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



def hockey_today():
    """Today in Edmonton, not the server's date: GitHub runs on UTC, where 6 PM Mountain is already
    tomorrow (30 Sep 2026: the site said Oct 1 during the Sep 30 games).  Edmonton time, at Christopher's word."""
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Edmonton")).date()
    except Exception:                                    # no tz database: Mountain standard time is close enough
        return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=7)).date()

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


HS = "https://hockeystats.com/api-n"                 # their robots.txt allows /api-n/ and disallows /api/
HS_SNAP = HERE / "cache" / "hs-2627.json"
HS_EVERY_H = 2                                      # 33 small reads at most this often


def club_records():
    """club -> ["W-L-OTL", conference, division, points, games, and its place in the league, conference, division
    and wild card race] off the NHL standings, for the Games tab and its playoff odds table (5 Oct 2026).
    Never breaks a build."""
    try:
        return {FIX.get(r["teamAbbrev"]["default"], r["teamAbbrev"]["default"]):
                [f'{r["wins"]}-{r["losses"]}-{r["otLosses"]}', r.get("conferenceName", ""), r.get("divisionName", ""),
                 r.get("points", 0), r.get("gamesPlayed", 0), r.get("leagueSequence", 0), r.get("conferenceSequence", 0),
                 r.get("divisionSequence", 0), r.get("wildcardSequence", 0)] for r in get(f"{API}/standings/now")["standings"]}
    except Exception as e:
        print(f"  club records skipped ({type(e).__name__})")
        return {}


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    r = urllib.request.urlopen(req, timeout=30)
    b = r.read()
    if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
        import gzip
        b = gzip.decompress(b)
    return b.decode("utf-8-sig")


def hs_text(path):
    return fetch_text(f"{HS}/{path}")


MP = "https://moneypuck.com/moneypuck"              # their robots.txt disallows nothing
WP_SNAP = HERE / "cache" / "wp-2627.json"


def game_odds(gsum, write=True):
    """Head-to-head game odds for the Games tab: the home side's chance of winning, by game id (5 Oct 2026).

    From MoneyPuck until HockeyStats.com answers the request to read their live games feed (Christopher, 5 Oct
    2026; notes/hockeystats permission email.md).  Before and after a game it is their pre-game figure
    (predictions/<id>.csv, read once and kept in cache/wp-2627.json).  While a game is live it is the last
    homeWinProbability in their play-by-play file (gameData/<season>/<id>.csv), read each run.
    Only the nights in gsum (tonight and yesterday) carry game ids, so only those games get odds.
    Returns {"src", "g": {game id: home %}, "live": [game ids showing a live figure]}.  Never breaks a build."""
    import csv, io
    try:
        pre = json.loads(WP_SNAP.read_text(encoding="utf-8")) if WP_SNAP.exists() else {}
        g, live, dirty = {}, [], False
        for night in gsum.values():
            for gm in (night.get("games", []) if isinstance(night, dict) else night):
                gid = str(gm.get("id") or "")
                if not gid:
                    continue
                if gid not in pre:
                    try:
                        row = next(csv.DictReader(io.StringIO(fetch_text(f"{MP}/predictions/{gid}.csv"))))
                        pre[gid] = round(float(row["preGameMoneyPuckHomeWinPrediction"]) * 100, 1)
                        dirty = True
                    except Exception:
                        pass                             # not posted yet: try again next run
                if gid in pre:
                    g[gid] = pre[gid]
                if gm.get("st") in ("LIVE", "CRIT"):
                    try:
                        rows = list(csv.DictReader(io.StringIO(fetch_text(f"{MP}/gameData/{gid[:4]}{int(gid[:4]) + 1}/{gid}.csv"))))
                        g[gid] = round(float(rows[-1]["homeWinProbability"]) * 100, 1)
                        live.append(gid)
                    except Exception:
                        pass                             # no live file yet: the pre-game figure stands
        if dirty and write:
            keep = sorted(pre, key=int)[-260:]
            WP_SNAP.write_text(json.dumps({k: pre[k] for k in keep}, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        return {"src": "MoneyPuck", "g": g, "live": live}
    except Exception as e:
        print(f"  game odds skipped ({type(e).__name__}: {e})")
        return {}


def playoff_odds(gsum, write=True):
    """HockeyStats.com's chance of making the playoffs, for the Games tab (Christopher, 5 Oct 2026: HockeyStats,
    not MoneyPuck).  Only their allowed feeds are read: playoff-odds-daily (every club, one row a day) and
    team-games-to-watch (a club's chance as it stands, and if the home side wins or loses each coming game).

    Each coming game's figures are kept by game id in cache/hs-2627.json until it starts.  Once it is final the
    page shows the chance that result gave and the change from before it, without waiting for their next run.
    A game nobody read before puck drop shows no change.  The feeds are read at most every HS_EVERY_H hours;
    the stamp rides in the output so a read always reaches the repo.  Their live win % sits behind /api/, which
    their robots.txt disallows, so it is not read (permission asked 5 Oct 2026).
    Returns {"src", "at", "now": {club: pct}, "cup": {club: pct}, "g": {game id: {club: [before, after or None]}}}.  Never breaks a build."""
    import csv, io
    short = lambda ab: FIX.get(ab.replace(".", ""), ab.replace(".", ""))
    pct = lambda x: round(float(x) * 100, 1)
    nights = [(n.get("games", []) if isinstance(n, dict) else n) for n in gsum.values()]
    try:
        c = json.loads(HS_SNAP.read_text(encoding="utf-8")) if HS_SNAP.exists() else {}
        c.setdefault("now", {}); c.setdefault("snap", {})
        stamp = dt.datetime.now(dt.timezone.utc)
        try:
            age_h = (stamp - dt.datetime.fromisoformat(c["at"])).total_seconds() / 3600
        except Exception:
            age_h = 1e9
        if age_h >= HS_EVERY_H:
            rows = list(csv.DictReader(io.StringIO(hs_text("playoff-odds-daily"))))
            last = max(r["timestamp"] for r in rows)
            codes = sorted(r["team"] for r in rows if r["timestamp"] == last)
            c["now"] = {short(r["team"]): round(float(r["playoff_odds"]), 1) for r in rows if r["timestamp"] == last}
            c["cup"] = {short(r["team"]): round(float(r["cup_odds"]), 1) for r in rows if r["timestamp"] == last}
            started = {str(gm.get("id")) for night in nights for gm in night if gm.get("st") not in ("FUT", "PRE")}
            for code in codes:
                try:
                    d = json.loads(hs_text(f"stats/nhl/team-games-to-watch?team={code}&limit=5"))
                except Exception:
                    continue                             # one club's read failing leaves its last figures
                me = short(code)
                if d.get("baselinePlayoffProb") is not None:
                    c["now"][me] = pct(d["baselinePlayoffProb"])
                for gw in d.get("gamesToWatch") or []:
                    gid, home = str(gw["gameId"]), short(gw["homeTeam"]) == me
                    if gid in started or me not in (short(gw["homeTeam"]), short(gw["awayTeam"])):
                        continue                         # a game under way keeps the figures from before it
                    win, lose = (gw["playoffIfHomeWins"], gw["playoffIfHomeLoses"])[::1 if home else -1]
                    c["snap"].setdefault(gid, {})[me] = [pct(d["baselinePlayoffProb"]), pct(win), pct(lose)]
                time.sleep(0.15)
            c["snap"] = {k: c["snap"][k] for k in sorted(c["snap"], key=int)[-260:]}
            c["at"] = stamp.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            if write:
                HS_SNAP.write_text(json.dumps(c, separators=(",", ":"), sort_keys=True), encoding="utf-8")
        g = {}
        for night in nights:
            for gm in night:
                s = c["snap"].get(str(gm.get("id")))
                if not s:
                    continue
                final = gm.get("st") in ("OFF", "FINAL")
                for side, mine, theirs in (("h", "hs", "as"), ("a", "as", "hs")):
                    ab = FIX.get(gm[side], gm[side])
                    if ab not in s:
                        continue
                    after = None
                    if final and gm.get(mine) != gm.get(theirs):
                        after = s[ab][1 if (gm.get(mine) or 0) > (gm.get(theirs) or 0) else 2]
                    g.setdefault(str(gm["id"]), {})[ab] = [s[ab][0], after]
        return {"src": "HockeyStats.com", "at": c.get("at", ""), "now": c["now"], "cup": c.get("cup", {}), "g": g}
    except Exception as e:
        print(f"  HockeyStats playoff odds skipped ({type(e).__name__}: {e})")
        return {}


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


def last_season_pool():
    """id -> name, position, team for everyone who played an NHL regular season game last year: two calls.
    Catches the players the club rosters leave out, such as anyone on injured reserve."""
    out = {}
    q = "?limit=-1&cayenneExp=seasonId=20252026%20and%20gameTypeId=2"
    for kind, name in (("skater", "skaterFullName"), ("goalie", "goalieFullName")):
        try:
            rows = get(f"https://api.nhle.com/stats/rest/en/{kind}/summary{q}")["data"]
        except Exception as e:
            print(f"  last season's {kind}s skipped ({type(e).__name__})")
            continue
        for r in rows:
            ab = (r.get("teamAbbrevs") or "").split(",")[-1].strip()
            out[int(r["playerId"])] = {"n": r.get(name, ""), "pos": "G" if kind == "goalie" else r.get("positionCode", "C"),
                                       "t": FIX.get(ab, ab), "hs": ""}
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
    today = min(hockey_today(), end)
    day_of = lambda d: (d - start).days
    weeks = weeks_of(start, end)
    week_start = [day_of(a) for a, _ in weeks]
    A = max(0, day_of(today))
    week = max(1, sum(1 for d in week_start if d <= A))

    # ---- the fixtures: who plays, when, in minutes after 00:00 UTC on the date ----
    sched, games = {}, {}
    for date, home, away, utc in jload(SCHED, "the NHL schedule")["games"]:
        d = day_of(dt.date.fromisoformat(date))
        if d < 0 or d > A + 7:          # a week ahead too: the injury report says when they play next
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
    auto_gg = {}                              # goalie id -> days he scored
    auto_ga = {}                              # goalie id -> a day for each assist he had
    gsum = {}                                 # day -> the score card's games and goals (Tonight > Games)
    for f in nights:
        n = json.loads(f.read_text(encoding="utf-8"))
        d = day_of(dt.date.fromisoformat(n["date"]))
        if d < 0 or d > A:
            continue
        seen += 1
        if d >= A - 1 and n.get("sum"):       # only tonight and yesterday: the page has no older Games view
            gsum[d] = n["sum"]
        for pid, s in n.get("skaters", {}).items():
            p = slot_for(int(pid), s.get("pos") or "C")
            p["n"] = p["n"] or s["n"]; p["t"] = s["t"]
            if s["g"] or s["a"]:
                p["ev"].append([d, s["g"], s["a"]])
            p["gd"].append(d); p["gs"].append(s["sog"]); p["gt"].append(s["toi"])
        # a goalie's goal is read off the score card's goal list, never a hand list (Christopher, 1 Oct 2026:
        # Shesterkin scored and was missed); shootout goals do not count
        gids = set(n.get("goalies", {}))
        for gm in (n.get("sum") or {}).get("games", []) if isinstance(n.get("sum"), dict) else (n.get("sum") or []):
            for x in gm.get("g", []):
                if x[0] != "SO" and str(x[3]) in gids:
                    auto_gg.setdefault(int(x[3]), set()).add(d)
                # a goalie's assist scores 1 like anyone's (Christopher, 4 Oct 2026); the boxscore gives goalies
                # no assist count, so it comes off the same goal list, one entry per assist
                for aid, _nm in (x[5] if x[0] != "SO" and len(x) > 5 else []):
                    if str(aid) in gids:
                        auto_ga.setdefault(int(aid), []).append(d)
        for pid, s in n.get("goalies", {}).items():
            p = slot_for(int(pid), "G")
            p["n"] = p["n"] or s["n"]; p["t"] = s["t"]
            if s["w"] or s["so"] or s.get("otl"):
                p["ev"].append([d, s["w"], s["so"], s.get("otl", 0)])
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

    def index(names):
        full, short, last = {}, {}, {}
        for pid, n in names:
            full.setdefault(norm(n), []).append(pid)
            bits = n.split()
            if len(bits) > 1:
                short.setdefault(norm(bits[0][0] + " " + " ".join(bits[1:])), []).append(pid)
                last.setdefault(norm(" ".join(bits[1:])), []).append(pid)
        return full, short, last
    played = index((pid, p["n"]) for pid, p in P.items())
    # a drafted player who has not played yet is still on the team page: fall back to the club rosters
    unplayed = index((pid, r["n"]) for pid, r in R.items() if pid not in P and r["n"])
    missing = []
    def card(pid):
        """An empty card for a drafted player who has no games yet, so he still shows on his team."""
        if pid not in P:
            r = R.get(pid)
            if r is None:                                # on no club's active roster (injured list, say)
                try:
                    d = get(f"{API}/player/{pid}/landing")
                    r = {"n": f"{d['firstName']['default']} {d['lastName']['default']}",
                         "pos": d.get("position", "C"), "t": FIX.get(d.get("currentTeamAbbrev", ""),
                         d.get("currentTeamAbbrev", "")), "hs": d.get("headshot", "")}
                except Exception:
                    missing.append(f"NHL id {pid} (not on a roster and the player lookup failed)")
                    return None
            P[pid] = {"ev": [], "gd": [], "gs": [], "gt": [], "gga": [], "n": r["n"], "t": r["t"],
                      "pos": POS.get(r["pos"], "F"), "slot": SLOT.get(r["pos"], "C")}
            if r["hs"]:
                P[pid]["hs"] = r["hs"]
        return pid
    def find(name):
        for group in (played, unplayed):
            for idx in group:                            # full name, then "C. McDavid", then the surname
                hits = idx.get(norm(name), [])
                if len(hits) == 1:
                    return card(hits[0])
                if len(hits) > 1:
                    missing.append(f"{name} (fits {len(hits)} players - give the NHL id instead)")
                    return None
        missing.append(name)
        return None
    ident = lambda v: card(v) if isinstance(v, int) else find(v)

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
            auto_gg.setdefault(pid, set()).update(day_of(dt.date.fromisoformat(x)) for x in days)
    for pid, days in auto_gg.items():
        if pid in P:
            P[pid]["gg"] = sorted(days)

    # every player on a club's active roster, and everyone who played last season, gets a card too, played or not,
    # so search finds anyone the league could pick up (Christopher, 1 Oct 2026: Bedard was missing - he is on no
    # active roster before his first game)
    for pid in R:
        card(pid)
    for pid, r in last_season_pool().items():
        if pid not in P and r["n"]:
            R[pid] = r
            card(pid)

    # ---- the blob the page reads ----
    # every player on a club's line chart gets a card (played yet or not), so the injury report and the news reach
    # him, and so the likely pickups have somewhere to live.  Daily Faceoff names are matched to NHL ids by full
    # name, and only when exactly one player has it.
    dfo_rows = {}
    try:
        import dfo_injuries
        dfo_rows = (dfo_injuries.load() or {}).get("players") or {}
    except Exception:                                      # the extra source is optional
        pass
    dfo_by_pid = {}
    for row in dfo_rows.values():
        hits = played[0].get(norm(row["n"]), []) or unplayed[0].get(norm(row["n"]), [])
        if len(hits) == 1 and card(hits[0]) is not None:
            dfo_by_pid[hits[0]] = row
    if dfo_rows:
        print(f"  {len(dfo_by_pid)} of {len(dfo_rows)} Daily Faceoff players matched to NHL ids")
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
        if p["pos"] == "G" and pid in auto_ga:
            o["gas"] = sorted(auto_ga[pid])
        if p["gd"]:
            o["toi"] = round(sum(p["gt"]) / len(p["gd"]))
        drow = dfo_by_pid.get(pid)
        if drow:
            if drow.get("ro"):
                o["ro"] = drow["ro"]                     # line roles: f1 f2 d1 pp1 g1 ...
            if drow.get("det") and not drow.get("st"):   # a healthy player's recent one-liner
                o["nw"] = {"x": drow["det"], "d": drow["at"], "u": drow["link"]}
        if pid in hurt:
            o["inj"] = hurt[pid]
            if pid in hurtd:
                o["injd"] = hurtd[pid]      # what it is, since when, the latest word
        players[str(pid)] = o

    # CBS fills in what the league file does not say: status, what it is, since when, the latest word
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cbs_injuries
        n = len(cbs_injuries.merge(players, keep=set(str(k) for k in hurt)))
        if n:
            print(f"  {n} injuries from CBS on top of the {len(hurt)} in the league file")
    except Exception as e:                      # a scrape is never allowed to break a build
        print(f"  CBS injuries skipped ({type(e).__name__})")

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
        "gsum": {str(d): g for d, g in sorted(gsum.items())},
        "clubs": club_records(),
        "mp": playoff_odds(gsum, write=not dry),
        "wp": game_odds(gsum, write=not dry),
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
                    lambda m: "/*MOCK-DATA*/" + js + "/*END-MOCK-DATA*/", s, flags=re.S)
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
