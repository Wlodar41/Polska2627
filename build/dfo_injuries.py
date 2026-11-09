"""Latest injury news for hurt players, from Daily Faceoff's team line-combination pages.

CBS says who is hurt and gives a date; Daily Faceoff adds the sentence or two about it ("Andersen (undisclosed) is
expected to be out until December").  Picked 2026-09-30 from three research passes: it is the only free,
server-rendered source with a per-player text update for every injured player, and robots.txt allows the pages.
No terms-of-use page could be found, so this stays polite: one request a second, at most 32 pages, refetched no
more than every 90 minutes, credited and linked on the card, and quiet on any failure.

  python dfo_injuries.py            # -> data/dfo-injuries.json (skipped if it is less than 90 minutes old)
  python dfo_injuries.py --force    # fetch now
  python dfo_injuries.py --print    # show what it found, write nothing

The file: {"fetched","source","players":{"<folded name>":{"n","t","st","det","long","at","link"}}}
"""
import datetime as dt
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "dfo-injuries.json"
BASE = "https://www.dailyfaceoff.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0 Safari/537.36 polska-pool-site (hobby fantasy page)",
      "Accept-Language": "en-CA,en;q=0.9"}
SHORT = {"LAK": "LA", "NJD": "NJ", "SJS": "SJ", "TBL": "TB"}     # the page's own club codes
CODE = {"out": "O", "ir": "IR", "dtd": "DTD"}
MAX_AGE_MIN = 90


def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z ]", " ", s.lower()).split())


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def page(slug):
    req = urllib.request.Request(f"{BASE}/teams/{slug}/line-combinations", headers=UA)
    h = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
    if not m:
        raise ValueError("no page data")
    return json.loads(m.group(1))["props"]["pageProps"]


def scrape(pause=1.0):
    first = page("anaheim-ducks")
    slugs = [t.get("slug") or re.sub(r"[^a-z]+", "-", t.get("name", "").lower()).strip("-")
             for t in first.get("sortedTeams") or []]
    out, seen = {}, 0
    for i, slug in enumerate(slugs):
        pp = first if slug == "anaheim-ducks" else None
        if pp is None:
            time.sleep(pause)
            try:
                pp = page(slug)
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
                continue                                    # one bad page must not lose the rest
        comb = pp.get("combinations") or {}
        abbr = SHORT.get(comb.get("teamAbbreviation", ""), comb.get("teamAbbreviation", ""))
        seen += 1
        today = dt.date.today()
        for p in comb.get("players") or []:
            k = fold(p.get("name", ""))
            if not k:
                continue
            st = (p.get("injuryStatus") or "").lower()
            news = p.get("latestNews") or {}
            role = p.get("groupIdentifier") or ""
            if role in ("g", "") and (p.get("positionIdentifier") or "").startswith("g"):
                role = p["positionIdentifier"]                  # g1 starter, g2 backup
            row = out.setdefault(k, {"n": p.get("name", ""), "t": abbr, "st": "", "det": "", "long": "", "at": "",
                                     "link": f"{BASE}/teams/{slug}/line-combinations", "ro": []})
            if role and role not in ("ir",) and role not in row["ro"]:
                row["ro"].append(role)
            if st:
                row["st"] = CODE.get(st, "O")
            at = (news.get("createdAt") or "")[:10]
            if news.get("details") and at >= row["at"]:
                row["det"], row["at"] = clean(news.get("details")), at
                row["long"] = clean(news.get("fantasyDetails"))
        for row in out.values():                                 # a healthy player keeps only a recent one-liner
            if not row["st"]:
                row["long"] = ""
                try:
                    if (today - dt.date.fromisoformat(row["at"])).days > 30:
                        row["det"] = ""
                except ValueError:
                    row["det"] = ""
    return out, seen


def age_minutes():
    try:
        f = json.loads(OUT.read_text(encoding="utf-8")).get("fetched", "")
        return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(f)).total_seconds() / 60
    except (OSError, ValueError, json.JSONDecodeError):
        return 1e9


def load(path=None):
    f = Path(path) if path else OUT
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def run(force=False, show=False):
    """Fetch and write, never raising: a scrape must not fail the nightly job."""
    if not force and not show and age_minutes() < MAX_AGE_MIN:
        print(f"Daily Faceoff: file is {age_minutes():.0f} min old, not refetching")
        return
    try:
        players, pages = scrape()
    except Exception as e:                                   # noqa: BLE001 - best effort by design
        print(f"Daily Faceoff is not answering ({type(e).__name__}); leaving {OUT.name} as it is")
        return
    if pages < 20 or sum(1 for r in players.values() if r["st"]) < 10:                       # a layout change reads as "nobody is hurt"
        print(f"only {pages} pages / {len(players)} players parsed - the site has probably changed; nothing written")
        return
    if show:
        for k, p in list(sorted(players.items()))[:10]:
            print(f"  {p['n']:22s} {p['t']:4s} {p['st']:4s} {','.join(p['ro']):10s} {p['at']}  {p['det'][:50]}")
        print(f"{len(players)} players, {sum(1 for r in players.values() if r['st'])} hurt, on {pages} pages")
        return
    OUT.write_text(json.dumps({"fetched": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                               "source": "Daily Faceoff", "players": players}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"{len(players)} players ({sum(1 for r in players.values() if r['st'])} hurt) from {pages} Daily Faceoff pages written to {OUT}")


if __name__ == "__main__":
    run(force="--force" in sys.argv, show="--print" in sys.argv)
