"""Every NHL game, night by night, from api-web.nhle.com - the real numbers behind the live site.

The page scores its own points (G=2, A=1, W=3, SO=3, goalie goal=10) off per-game lines, so this
pulls the lines and nothing else: one call for the night's card, one per game for the boxscore.
A night is written to cache/box2627/<date>.json and, once every game on it is final, never fetched
again.  Tonight's file is rewritten on every run, which is what makes the site live while games are on.

  python nhl_boxscores.py                 # season start -> today, skipping nights already final
  python nhl_boxscores.py 2026-11-01 2026-11-03
  python nhl_boxscores.py --out <dir>     # somewhere other than cache/box2627 (used by the tests)

Each file holds, for one date:
  {"date","day","final","games":[[home,away,utcMinutes]],
   "skaters":{playerId:{"n","pos","t","g","a","sog","toi"}},
   "goalies":{playerId:{"n","t","w","so","sa","sv","ga","toi","st"}}}
day counts from the first day of pool scoring, the same numbering the page uses.
"""
import json, re, sys, time, urllib.error, urllib.request, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SEASON_START = dt.date(2026, 9, 29)          # day 0 of pool scoring; matches league.start in the page
SEASON_END = dt.date(2027, 4, 10)
OUT = HERE / "cache" / "box2627"
API = "https://api-web.nhle.com/v1"
LIVE = {"LIVE", "CRIT", "PRE"}               # not final yet: fetch it again next run


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=30))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


def mmss(s):
    """"15:33" -> 933 seconds.  The page stores ice time in seconds."""
    m = re.match(r"^(\d+):(\d\d)$", (s or "").strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else 0


def day_of(d):
    return (d - SEASON_START).days


def night(date):
    """One date: the card, then a boxscore per game.  Returns None when nobody played."""
    iso = date.isoformat()
    card = get(f"{API}/score/{iso}")
    games = [g for g in card.get("games", []) if g.get("gameType") in (2, 3)]   # regular season + playoffs
    if not games:
        return None
    out = {"date": iso, "day": day_of(date), "final": True, "games": [],
           "skaters": {}, "goalies": {}}
    for g in games:
        home, away = g["homeTeam"]["abbrev"], g["awayTeam"]["abbrev"]
        start = g.get("startTimeUTC") or ""
        mins = 0
        if start:
            t = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
            mins = t.hour * 60 + t.minute + 1440 * (t.date() - date).days   # minutes after 00:00 UTC on THIS date
        out["games"].append([home, away, mins])
        state = g.get("gameState", "")
        if state in LIVE or state == "FUT":
            out["final"] = False
        if state == "FUT":                      # not started: the card is all there is
            continue
        box = get(f"{API}/gamecenter/{g['id']}/boxscore")
        pbg = box.get("playerByGameStats") or {}
        for side, team in (("homeTeam", home), ("awayTeam", away)):
            grp = pbg.get(side) or {}
            for who in ("forwards", "defense"):
                for p in grp.get(who) or []:
                    out["skaters"][str(p["playerId"])] = {
                        "n": p["name"]["default"], "pos": p.get("position", ""), "t": team,
                        "g": p.get("goals", 0) or 0, "a": p.get("assists", 0) or 0,
                        "sog": p.get("sog", 0) or 0, "toi": mmss(p.get("toi"))}
            for p in grp.get("goalies") or []:
                toi = mmss(p.get("toi"))
                if not toi and not p.get("starter"):
                    continue                    # dressed as the backup and never used
                dec = p.get("decision", "")
                ga = p.get("goalsAgainst", 0) or 0
                sa = p.get("shotsAgainst", 0) or 0
                out["goalies"][str(p["playerId"])] = {
                    "n": p["name"]["default"], "t": team,
                    "w": 1 if dec == "W" else 0,
                    # a shutout is the win with nothing let in, which needs the whole game
                    "so": 1 if (dec == "W" and ga == 0 and sa > 0) else 0,
                    "sa": sa, "sv": p.get("saves", 0) or 0, "ga": ga,
                    "toi": toi, "st": 1 if p.get("starter") else 0}
        time.sleep(0.2)                         # the API is free; do not hammer it
    return out


def run(start, end, outdir=OUT, force=False):
    outdir.mkdir(parents=True, exist_ok=True)
    wrote = skipped = empty = 0
    d = start
    while d <= end:
        f = outdir / f"{d.isoformat()}.json"
        if f.exists() and not force:
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("final"):
                    skipped += 1; d += dt.timedelta(days=1); continue   # settled; never fetch it again
            except json.JSONDecodeError:
                pass
        n = night(d)
        if n is None:
            empty += 1
        else:
            f.write_text(json.dumps(n, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            wrote += 1
            print(f"  {d} {len(n['games']):2d} games, {len(n['skaters'])+len(n['goalies']):3d} players"
                  f"{'' if n['final'] else '  (still on)'}")
        d += dt.timedelta(days=1)
    print(f"{wrote} night{'' if wrote == 1 else 's'} written, {skipped} already final, {empty} with no hockey")
    return wrote


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = OUT
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    iso = lambda s: dt.date.fromisoformat(s)
    a = iso(args[0]) if args else SEASON_START
    b = iso(args[1]) if len(args) > 1 else min(dt.date.today(), SEASON_END)
    if b < a:
        print(f"the season starts {a}; nothing to fetch yet")   # opening night has not come round
        sys.exit(0)
    print(f"NHL boxscores {a} -> {b}")
    run(a, b, out, force="--force" in sys.argv)
