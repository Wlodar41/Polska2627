"""Assemble the REAL 2026-27 season from the boxscore cache and write it into the page.

Three inputs, no simulation anywhere:
  data/league-2627.json    the pool itself - teams, the draft, add/drops, who is hurt.  Hand kept,
                           because Yahoo is the system of record for it and there are at most 36
                           moves in a season.  Nothing here runs until it says "live": true.
  cache/box2627/*.json     every night's real lines (nhl_boxscores.py)
  data/nhl-sched-2627.json the season's fixtures, for who plays tonight and at what time

Out goes the same blob mock_2627.py writes, between the MOCK-DATA markers of the page, so the site
renders identically - it is only where the numbers come from that changes.

  python live_2627.py                          # site/polska2627.html, in place
  python live_2627.py --page index.html --stamp   # what GitHub Actions runs in the published repo
  python live_2627.py --dry                    # say what it would write, write nothing
"""
import json, re, sys, time, unicodedata, urllib.request, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LEAGUE = HERE / "data" / "league-2627.json"
BOX = HERE / "cache" / "box2627"
SCHED = HERE / "data" / "nhl-sched-2627.json"
ROSTERS = HERE / "cache" / "rosters-2627.json"
API = "https://api-web.nhle.com/v1"
TEAM_CODES = ("ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD NSH NYI NYR OTT "
              "PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH").split()
# the page uses the short codes the schedule and boxscores carry
FIX = {"LAK": "LA", "NJD": "NJ", "SJS": "SJ", "TBL": "TB"}
SLOT = {"C": "C", "L": "LW", "R": "RW", "D": "D", "G": "G"}
POS = {"C": "F", "L": "F", "R": "F", "D": "D", "G": "G"}


def norm(s):
    """Names are typed by hand and come back from two APIs: fold accents and punctuation away."""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", " ", s.lower()).split() and " ".join(
        re.sub(r"[^a-z ]", " ", s.lower()).split()) or ""


def jload(p, what):
    if not p.exists():
        sys.exit(f"missing {what}: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def nhl_rosters(max_age_h=20):
    """id -> full name, position, team, headshot.  One call a club, cached for the day."""
    if ROSTERS.exists():
        try:
            c = json.loads(ROSTERS.read_text(encoding="utf-8"))
            age = (dt.datetime.now(dt.timezone.utc)
                   - dt.datetime.fromisoformat(c["fetched"])).total_seconds() / 3600
            if age < max_age_h:
                return {int(k): v for k, v in c["players"].items()}
        except Exception:
            pass
    out = {}
    for ab in TEAM_CODES:
        try:
            d = get(f"{API}/roster/{ab}/current")
        except Exception as e:
            print(f"  roster {ab} failed ({e}); carrying on")
            continue
        for grp in ("forwards", "defensemen", "goalies"):
            for p in d.get(grp, []):
                out[int(p["id"])] = {
                    "n": f"{p['firstName']['default']} {p['lastName']['default']}",
                    "pos": p.get("positionCode", ""), "t": FIX.get(ab, ab),
                    "hs": p.get("headshot", "")}
        time.sleep(0.15)
    ROSTERS.parent.mkdir(parents=True, exist_ok=True)
    ROSTERS.write_text(json.dumps({"fetched": dt.datetime.now(dt.timezone.utc).isoformat(),
                                   "players": {str(k): v for k, v in out.items()}},
                                  ensure_ascii=False), encoding="utf-8")
    return out


def weeks_of(start, end):
    """Yahoo's weeks: the first runs from opening night to that Sunday, the rest are Mon-Sun."""
    out, a = [], start
    while a <= end:
        b = a + dt.timedelta(days=(6 - a.weekday()) % 7)      # that week's Sunday
        out.append((a, min(b, end)))
        a = b + dt.timedelta(days=1)
    return out


def build(dry=False, page=None, stamp=False):
    L = jload(LEAGUE, "the league file")
    if not L.get("live"):
        print('data/league-2627.json says "live": false - the real season has not been switched on, '
              "so the page keeps the data it has.")
        return False
    start = dt.date.fromisoformat(L["league"]["start"])
    end = dt.date.fromisoformat(L["league"]["end"])
    today = min(dt.date.today(), end)
    day_of = lambda d: (d - start).days
    weeks = weeks_of(start, end)
    week_start = [day_of(a) for a, _ in weeks]
    A = max(0, day_of(today))
    week = max(1, sum(1 for d in week_start if d <= A))

    # ---- the fixtures: who plays, when, in minutes after 00:00 UTC on the date ----
    sched, games = {}, {}
    for date, home, away, utc in jload(SCHED, "the NHL schedule")["games"]:
        d = day_of(dt.date.fromisoformat(date))
        if d < 0 or d > A:
            continue
        t = dt.datetime.fromisoformat(utc.replace("Z", "+00:00"))
        mins = t.hour * 60 + t.minute + 1440 * (t.date() - dt.date.fromisoformat(date)).days
        games.setdefault(d, []).append([home, away, mins])
        for ab in (home, away):
            sched.setdefault(ab, set()).add(d)

    # ---- the nights themselves ----
    P = {}                                    # id -> the arrays the page reads
    def slot_for(pid, code):
        p = P.setdefault(pid, {"ev": [], "gd": [], "gs": [], "gt": [], "gga": [], "pos": POS.get(code, "F"),
                               "slot": SLOT.get(code, "C"), "n": "", "t": ""})
        return p
    nights = sorted(BOX.glob("*.json"))
    seen = 0
    for f in nights:
        n = json.loads(f.read_text(encoding="utf-8"))
        d = day_of(dt.date.fromisoformat(n["date"]))
        if d < 0 or d > A:
            continue
        seen += 1
        for pid, s in n.get("skaters", {}).items():
            p = slot_for(int(pid), s.get("pos") or "C")
            p["n"] = p["n"] or s["n"]; p["t"] = s["t"]
            if s["g"] or s["a"]:
                p["ev"].append([d, s["g"], s["a"]])
            p["gd"].append(d); p["gs"].append(s["sog"]); p["gt"].append(s["toi"])
        for pid, s in n.get("goalies", {}).items():
            p = slot_for(int(pid), "G")
            p["n"] = p["n"] or s["n"]; p["t"] = s["t"]
            if s["w"] or s["so"]:
                p["ev"].append([d, s["w"], s["so"]])
            p["gd"].append(d); p["gs"].append(s["sa"]); p["gt"].append(s["toi"]); p["gga"].append(s["ga"])

    # ---- names, positions and faces off the club rosters ----
    R = nhl_rosters()
    for pid, r in R.items():
        p = P.get(pid)
        if p is None:
            continue                          # on a roster but has not played: nothing to rank him on
        p["n"] = r["n"] or p["n"]
        p["t"] = r["t"] or p["t"]
        if r["pos"]:
            p["pos"], p["slot"] = POS.get(r["pos"], p["pos"]), SLOT.get(r["pos"], p["slot"])
        if r["hs"]:
            p["hs"] = r["hs"]

    full, short, last = {}, {}, {}
    for pid, p in P.items():
        n = p["n"]
        full.setdefault(norm(n), []).append(pid)
        bits = n.split()
        if len(bits) > 1:
            short.setdefault(norm(bits[0][0] + " " + " ".join(bits[1:])), []).append(pid)
            last.setdefault(norm(" ".join(bits[1:])), []).append(pid)
    missing = []
    def find(name):
        for idx in (full, short, last):                 # full name, then "C. McDavid", then the surname
            hits = idx.get(norm(name), [])
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                missing.append(f"{name} (fits {len(hits)} players - give the NHL id instead)")
                return None
        missing.append(name)
        return None
    ident = lambda v: v if isinstance(v, int) else find(v)

    # ---- the pool: draft, stints, moves ----
    teams = L["teams"]
    tid = {t["id"] for t in teams}
    nteams = len(teams)
    draft, stints, txns = [], {}, []
    for pick in sorted(L.get("draft", []), key=lambda x: (x["round"], x["pick"])):
        pid = ident(pick["player"])
        if pid is None or pick["team"] not in tid:
            continue
        rd, pk = pick["round"], pick["pick"]
        ov = (rd - 1) * nteams + (pk if rd % 2 else nteams - pk + 1)     # snake
        draft.append({"p": pid, "t": pick["team"], "rd": rd, "pk": pk, "ov": ov})
        stints.setdefault(pid, []).append([pick["team"], 0, None])
    for mv in sorted(L.get("moves", []), key=lambda x: x["week"]):
        w, t = mv["week"], mv["team"]
        add, drop = ident(mv["add"]), ident(mv["drop"])
        if add is None or drop is None or t not in tid:
            continue
        for s in stints.get(drop, []):
            if s[0] == t and s[2] is None:
                s[2] = w - 1                   # he is gone as that week starts
        stints.setdefault(add, []).append([t, w - 1, None])
        txns.append({"t": t, "w": w, "date": mv.get("date", ""), "add": add, "drop": drop,
                     "why": mv.get("why", "")})
    # "out" takes a bare name or {"player": ..., "status": "IR"} - the page shows the code by his name
    hurt, hurtd = {}, {}
    for _o in L.get("out", []):
        if isinstance(_o, str):
            _n, _s, _d = _o, "O", {}
        else:
            _n, _s = _o.get("player"), _o.get("status", "O")
            _d = {k: v for k, v in (("w", _o.get("what")), ("s", _o.get("since")),
                                    ("n", _o.get("note")), ("a", _o.get("asOf")),
                                    ("src", _o.get("source", "The league file"))) if v}
        _id = ident(_n) if _n else None
        if _id:
            hurt[_id] = str(_s).upper()
            if len(_d) > 1:
                hurtd[_id] = _d
    for pid, days in ((ident(g["player"]), g["dates"]) for g in L.get("goalieGoals", [])):
        if pid and pid in P:
            P[pid]["gg"] = sorted({day_of(dt.date.fromisoformat(x)) for x in days})

    # ---- the blob the page reads ----
    players = {}
    for pid, p in P.items():
        o = {"n": p["n"], "pos": p["pos"], "slot": p["slot"], "nhl": p["t"], "sc": p["t"],
             "ev": p["ev"], "gd": p["gd"], "gs": p["gs"], "gt": p["gt"]}
        if p.get("hs"):
            o["hs"] = p["hs"]
        if p["pos"] == "G":
            o["gga"] = p["gga"]
        if p.get("gg"):
            o["gg"] = p["gg"]
        if p["gd"]:
            o["toi"] = round(sum(p["gt"]) / len(p["gd"]))
        if pid in hurt:
            o["inj"] = hurt[pid]
            if pid in hurtd:
                o["injd"] = hurtd[pid]      # what it is, since when, the latest word
        players[str(pid)] = o

    out = {
        "live": True, "mock": False,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "league": L["league"],
        "asOf": {"week": week, "of": len(weeks), "day": A,
                 "date": today.strftime("%b ") + f"{today.day}, {today.year}"},
        "weeks": [[a.strftime("%b ") + str(a.day), b.strftime("%b ") + str(b.day)] for a, b in weeks],
        "weekStart": week_start,
        "sched": {k: sorted(v) for k, v in sorted(sched.items())},
        "games": {str(d): g for d, g in sorted(games.items())},
        "teams": teams,
        "players": players,
        "draft": draft,
        "stints": {str(k): v for k, v in stints.items()},
        "txns": sorted(txns, key=lambda t: -t["w"]),
        "poolSize": {P_: sum(1 for p in players.values() if p["pos"] == P_) for P_ in "FDG"},
    }
    if missing:
        print("  could not place these names from the league file (they have not played yet, or the "
              "name is ambiguous):\n   - " + "\n   - ".join(sorted(set(missing))))
    if not seen:
        print("  no nights in the cache yet, so the page keeps what it has "
              "(run nhl_boxscores.py first, or wait for opening night)")
        return False
    print(f"  day {A} of {day_of(end)}, week {week} of {len(weeks)} · {seen} nights · "
          f"{len(players)} players · {len(draft)} picks · {len(txns)} moves")
    if dry:
        print("  --dry: nothing written")
        return True

    js = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    (HERE / "data" / "live-2627.json").write_text(js, encoding="utf-8")
    target = Path(page) if page else HERE / "site" / "polska2627.html"
    s = target.read_text(encoding="utf-8")
    s2, n = re.subn(r"/\*MOCK-DATA\*/.*?/\*END-MOCK-DATA\*/",
                    lambda m: "/*MOCK-DATA*/" + js.replace("\\", "\\\\") + "/*END-MOCK-DATA*/", s, flags=re.S)
    if not n:
        sys.exit(f"no MOCK-DATA markers in {target}")
    if stamp:                                  # the published copy carries its own build id
        build_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        s2 = re.sub(r'(<meta name="build" content=")[^"]*(">)', r"\g<1>" + build_id + r"\g<2>", s2)
        (target.parent / "version.txt").write_text(build_id + "\n", encoding="utf-8", newline="\n")
        print(f"  stamped build {build_id}")
    if s2 == s:
        print("  the page already holds these numbers")
        return False
    target.write_text(s2, encoding="utf-8", newline="")
    print(f"  wrote {len(js):,} chars of real data into {target}")
    return True


if __name__ == "__main__":
    pg = sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else None
    build(dry="--dry" in sys.argv, page=pg, stamp="--stamp" in sys.argv)
