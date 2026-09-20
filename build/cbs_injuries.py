"""Who is hurt, from cbssports.com/nhl/injuries - the enrichment behind the card's injury report.

Nobody publishes NHL injuries in an API worth relying on: the NHL's own has none at all, and ESPN's
returns 403 to anything that is not a browser.  CBS publishes a plain table a team at a time -
player, position, updated, injury, status - so this reads that, and is written to fail quietly:
if the page moves or the layout changes, it leaves the last good file alone and says so, and the
site falls back to whatever the league file says by hand.

  python cbs_injuries.py            # -> data/injuries.json
  python cbs_injuries.py --print    # show what it found, write nothing

The file it writes:
  {"fetched","source","players":{"<folded name>":{"n","t","pos","status","what","since","note"}}}
status is the pool's own code - O, IR, IR-LT, DTD - so the page can show it beside a name.
"""
import json, re, sys, unicodedata, urllib.error, urllib.request, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "injuries.json"
URL = "https://www.cbssports.com/nhl/injuries/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
      "Accept-Language": "en-CA,en;q=0.9"}
# CBS spells five clubs its own way; everything else already matches the NHL feed
FIX = {"CLB": "CBJ", "LV": "VGK", "MON": "MTL", "WAS": "WSH", "LAK": "LA", "NJD": "NJ",
       "SJS": "SJ", "TBL": "TB"}
strip = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def code(status, injury):
    """CBS writes prose; the pool wants Yahoo's code."""
    s = (status or "").lower()
    if "long" in s or "ir-lt" in s:
        return "IR-LT"
    if "injured reserve" in s or re.search(r"\bir\b", s):
        return "IR"
    if "day to day" in s or "day-to-day" in s or "questionable" in s or "probable" in s or "game-time" in s:
        return "DTD"
    if "out" in s or "expected to miss" in s:
        return "O"
    return "O"                       # listed at all means he is not available


def when(txt, today=None):
    """"Sun, Sep 20" -> 2026-09-20.  No year on the page, so take the nearest one."""
    today = today or dt.date.today()
    m = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})", txt or "")
    if not m:
        return ""
    try:
        d = dt.datetime.strptime(f"{m.group(1)} {m.group(2)} {today.year}", "%b %d %Y").date()
    except ValueError:
        return ""
    if (d - today).days > 30:        # a date well ahead of today belongs to last year
        d = d.replace(year=d.year - 1)
    return d.isoformat()


def scrape(html, today=None):
    out = {}
    for block in re.split(r'<div class="TableBaseWrapper', html)[1:]:
        tm = re.search(r"/nhl/teams/([A-Z]{2,3})/", block)
        team = FIX.get(tm.group(1), tm.group(1)) if tm else ""
        for row in re.findall(r"<tr[^>]*TableBase-bodyTr[^>]*>(.*?)</tr>", block, re.S):
            cells = re.findall(r"<td.*?</td>", row, re.S)
            if len(cells) < 5:
                continue
            long = re.search(r'CellPlayerName--long[^>]*>(.*?)</span>\s*</span>', cells[0], re.S)
            name = strip(long.group(1)) if long else strip(cells[0]).split("  ")[-1]
            if not name:
                continue
            pos, upd, inj, st = (strip(c) for c in cells[1:5])
            out[fold(name)] = {"n": name, "t": team, "pos": pos, "status": code(st, inj),
                               "what": inj, "since": when(upd, today), "note": st}
    return out

def load(path=None):
    """The last good file, or {} when there is not one yet."""
    f = Path(path) if path else OUT
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def merge(players, keep=(), report=None):
    """Write CBS's status and detail onto a {id: player} map, matching on the folded name.

    `keep` is the ids the league file already speaks for by hand - those are left alone, because a
    person who typed it knows more than a scrape.  Returns the ids it touched.
    """
    data = report if report is not None else load()
    rows = (data or {}).get("players") or {}
    src = (data or {}).get("source", "CBS Sports")
    asof = (data or {}).get("fetched", "")
    hit = []
    for pid, p in players.items():
        if pid in keep:
            continue
        r = rows.get(fold(p.get("n", "")))
        if not r:
            continue
        if r.get("t") and p.get("nhl") and r["t"] != p["nhl"]:
            continue                      # same name, different club: not our man
        p["inj"] = r["status"]
        d = {k: v for k, v in (("w", r.get("what")), ("s", r.get("since")),
                               ("n", r.get("note")), ("a", asof), ("src", src)) if v}
        p["injd"] = d
        hit.append(pid)
    return hit


def fetch():
    req = urllib.request.Request(URL, headers=UA)
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")


if __name__ == "__main__":
    try:
        players = scrape(fetch())
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"CBS is not answering ({e}); leaving {OUT.name} as it is")
        sys.exit(0)                  # never fail the nightly job over this
    if len(players) < 5:             # a layout change reads as "nobody is hurt", which is never true
        print(f"only {len(players)} rows parsed - the page has probably changed shape; nothing written")
        sys.exit(0)
    if "--print" in sys.argv:
        for k, p in sorted(players.items())[:12]:
            print(f"  {p['n']:24s} {p['t']:4s} {p['status']:5s} {p['what']:16s} {p['since']}  {p['note'][:40]}")
        print(f"{len(players)} players listed")
        sys.exit(0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"fetched": dt.date.today().isoformat(), "source": "CBS Sports",
                               "players": players}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(players)} injured players written to {OUT}")
