"""Who is hot and who is cold, from Frozen Pool's Hot / Not report (Dobber Sports) - the flames and snowflakes.

  https://frozenpool.dobbersports.com/frozenpool_hotnot.php

Four public pages, no login: Hot and Cold, skaters and goalies.  Each is a plain table, ranked by points a game
(skaters) and by record and save percentage (goalies).  Asked for by Christopher, 16 Oct 2026: the marks on the
site come from this list, and how hard the mark animates scales with how hot or cold the player is.

Written to fail quietly, like cbs_injuries.py: if the page moves or the layout changes, it keeps the last good file
and says so, and the site simply shows no marks.  The list changes once a day, so a build reads the file and only
fetches again when it is over an hour old.

  python frozenpool_hotnot.py            # -> data/frozenpool-hotnot.json
  python frozenpool_hotnot.py --print    # show what it found and the level each gets, write nothing

The file it writes:
  {"fetched","source","rows":[{"k":"hot"|"cold","n","t","pos","gp","rp"(Yahoo % rostered), skaters "pts","ppg",
                                goalies "w","sv","gaa"}]}
level(row) turns a row into 1, 2 or 3 (0 = not worth a mark); the thresholds are in its comment.
"""
import html, json, re, sys, unicodedata, datetime as dt, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "frozenpool-hotnot.json"
URL = "https://frozenpool.dobbersports.com/frozenpool_hotnot.php?type={k}&pos={p}&team=ALL&MinGP=0&ranks=0"
SOURCE = "https://frozenpool.dobbersports.com/frozenpool_hotnot.php"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "en-CA,en;q=0.9"}
strip = lambda s: html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip())


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def club(t):
    """Frozen Pool writes L.A, N.J, S.J, T.B; the pool's feed writes LA, NJ, SJ, TB (and TBL now and then)."""
    t = (t or "").replace(".", "").upper()
    return "TB" if t == "TBL" else t


def num(x, f=float):
    try:
        return f(x)
    except (TypeError, ValueError):
        return 0


def table(page):
    i = page.find("Click for more info")
    m = re.search(r"<thead>(.*?)</thead>(.*?)</tbody>", page[i if i >= 0 else 0:], re.S)
    if not m:
        return []
    hd = [strip(x) for x in re.findall(r"<th[^>]*>(.*?)</th>", m.group(1), re.S)]
    out = []
    for r in re.findall(r"<tr>(.*?)</tr>", m.group(2), re.S):
        c = [strip(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(c) == len(hd):
            out.append(dict(zip(hd, c)))
    return out


def fetch():
    rows = []
    for k in ("Hot", "Cold"):
        for p in ("ALL", "G"):
            req = urllib.request.Request(URL.format(k=k, p=p), headers=UA)
            page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            got = table(page)
            if p == "ALL" and len(got) < 10:
                raise ValueError(f"{k} skaters: only {len(got)} rows, the layout may have changed")
            for r in got:
                o = {"k": k.lower(), "n": r["Player"].title(), "t": club(r["Team"]), "pos": r["POS"],
                     "gp": num(r["GP"], int), "rp": num(r.get("Yahoo Rostered %"), int)}
                if p == "G":
                    o.update(w=num(r["W"], int), sv=num(r["SV%"]), gaa=num(r["GAA"]))
                elif r["POS"] == "G":
                    continue
                else:
                    o.update(pts=num(r["PTS"], int), ppg=num(r["PTS/G"]))
                rows.append(o)
    return {"fetched": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "source": SOURCE,
            "rows": rows}


def level(r):
    """1 warm / cool, 2 hot / cold, 3 on fire / frozen solid; 0 leaves the player unmarked.
    Hot skaters (3+ games in the list's window): 1.3 NHL points a game, 1.5, 2.0 (2.0 over 4+ games; over 3, level 2).
    Tuned on the 16 Oct 2026 list: 48 hot skaters marked, 5 of them on fire; 14 cold.
    Cold skaters only count when the pool would care: 4+ games and 40%+ rostered on Yahoo.
    Then 0.50 a game or less, 0.25 or less, nothing at all; a regular (80%+ rostered) goes up one level.
    Goalies, 3+ starts: hot on save percentage .915 / .930 / .945; cold, 40%+ rostered, .890 / .870 / .850 or worse."""
    gp, k = r.get("gp", 0), r["k"]
    if r.get("pos") == "G":
        sv = r.get("sv", 0)
        if gp < 3:
            return 0
        if k == "hot":
            return 3 if sv >= .945 else 2 if sv >= .930 else 1 if sv >= .915 else 0
        if r.get("rp", 0) < 40:
            return 0
        return 3 if sv <= .850 else 2 if sv <= .870 else 1 if sv <= .890 else 0
    ppg = r.get("ppg", 0)
    if k == "hot":
        if gp < 3:
            return 0
        return 3 if ppg >= 2.0 and gp >= 4 else 2 if ppg >= 1.5 else 1 if ppg >= 1.3 else 0
    if gp < 4 or r.get("rp", 0) < 40:
        return 0
    lv = 3 if ppg == 0 else 2 if ppg <= .25 else 1 if ppg <= .5 else 0
    return min(3, lv + 1) if lv and r.get("rp", 0) >= 80 else lv


def load(max_age_min=60):
    """The last good list, fetched again when it is over max_age_min old.  None if there has never been one."""
    old = None
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
        at = dt.datetime.strptime(old["fetched"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=dt.timezone.utc)
        if dt.datetime.now(dt.timezone.utc) - at < dt.timedelta(minutes=max_age_min):
            return old
    except Exception:
        pass
    try:
        new = fetch()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(new, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        return new
    except Exception as e:
        print(f"  Frozen Pool hot / not skipped ({type(e).__name__}: {str(e)[:120]}); keeping the last list")
        return old


def merge(players, data):
    """Put {k, l, ...} on each matched player as players[pid]["fp"].  Matched on folded name and club, then on name
    alone when only one player has it.  Returns how many were marked."""
    if not data:
        return 0
    by_nt, by_n = {}, {}
    for pid, p in players.items():
        f = fold(p["n"])
        by_nt.setdefault((f, club(p.get("nhl"))), []).append(pid)
        by_n.setdefault(f, []).append(pid)
    n = 0
    for r in data.get("rows", []):
        lv = level(r)
        if not lv:
            continue
        f = fold(r["n"])
        hit = by_nt.get((f, r["t"])) or (by_n.get(f) if len(by_n.get(f, [])) == 1 else None)
        if not hit or len(hit) != 1 or "fp" in players[hit[0]]:
            continue
        o = {"k": r["k"], "l": lv, "gp": r["gp"]}
        for key in ("pts", "ppg", "w", "sv", "gaa"):
            if key in r:
                o[key] = r[key]
        players[hit[0]]["fp"] = o
        n += 1
    return n


if __name__ == "__main__":
    if "--print" in sys.argv:
        d = fetch()
        for k in ("hot", "cold"):
            rs = [(level(r), r) for r in d["rows"] if r["k"] == k]
            print(f"{k}: {len(rs)} on the list; level 3 {sum(l == 3 for l, _ in rs)}, 2 {sum(l == 2 for l, _ in rs)}, "
                  f"1 {sum(l == 1 for l, _ in rs)}, unmarked {sum(l == 0 for l, _ in rs)}")
            for l, r in rs:
                if l:
                    print(f"   {l}  {r['n']:<24} {r['t']:<4} {r['pos']:<2} gp {r['gp']:<2} rost {r['rp']:>3}%  "
                          + (f"sv {r['sv']:.3f}" if r['pos'] == 'G' else f"{r['ppg']:.2f} a game"))
    else:
        d = load(0)
        print(f"  {len(d['rows']) if d else 0} rows -> {OUT}")
