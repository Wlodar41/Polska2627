"""gamedaytweets.com: the line-combination feed, and a viewable copy of the site itself.

The site cannot be put straight into an iframe - every real page there answers with
`x-frame-options: SAMEORIGIN`, which is the site telling browsers not to embed it, and that is
theirs to decide.  So this reads the four pages that matter and writes each one out beside our own
page as a plain HTML file:

  /            -> gdt-all.html       everything the beat writers have posted
  /lines       -> gdt-lines.html     the line combinations
  /news        -> gdt-news.html      who is hurt, who is in, who was traded
  /goalies     -> gdt-goalies.html   the starting-goalie card for the next game day

Those files are their pages, not a retelling of them: their stylesheet, their logos and their
layout, loaded from their own server, with the browser end of the site taken out - every <script>
removed, so nothing of theirs runs on our origin, and the frame is sandboxed on top of that.  Their
own nav (ALL / LINES / GOALIES / NEWS) is pointed at the sibling files so it still works inside the
frame; every other link is sent out to the real site in a new tab, which is also where the tab's
"Open the full page" goes.  The top of each file says where and when it came from.

It still writes site/line-tweets.json as well, which is what the Lines tab reads.

  python gdt_lines.py                 # -> site/
  python gdt_lines.py --out .         # what the nightly job runs, beside index.html
  python gdt_lines.py --print

Like the injury scrape, it fails quietly: a bad response or a page that no longer parses leaves the
last good files alone, and the tabs fall back to saying so with a link out.
"""
import json, re, sys, urllib.error, urllib.request, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SITE = "https://www.gamedaytweets.com"
URL = SITE + "/lines"
# their path -> the file we write it to.  The order is the order the tab offers them.
PAGES = (("/", "gdt-all.html"), ("/lines", "gdt-lines.html"),
         ("/news", "gdt-news.html"), ("/goalies", "gdt-goalies.html"))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
      "Accept-Language": "en-CA,en;q=0.9"}
KEEP = 40                                   # a couple of days' worth; the page shows the lot


def text_of(html):
    """Tweet body with its line breaks kept - the lines ARE the content."""
    s = re.sub(r"<br\s*/?>", "\n", html)
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&mdash;", "—"),
                 ("&nbsp;", " "), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    s = re.sub(r"[ \t]+", " ", s)
    return "\n".join(l.strip() for l in s.split("\n")).strip("\n ")


def scrape(html):
    out = []
    for bq in re.findall(r'<blockquote class="tweet[^"]*">(.*?)</blockquote>', html, re.S):
        who = re.search(r'class="handle"[^>]*>@?([^<]+)</a>', bq)
        body = re.search(r"<p[^>]*>(.*?)</p>", bq, re.S)
        link = re.search(r'href="(https://x\.com/[^"]+/status/\d+)"[^>]*>([^<]+)</a>', bq)
        if not body:
            continue
        txt = text_of(body.group(1))
        if who:                              # the handle is the first line of the body; drop the repeat
            txt = re.sub(r"^@?" + re.escape(who.group(1).strip()) + r"\s*", "", txt).strip()
        out.append({"who": "@" + who.group(1).strip() if who else "",
                    "txt": txt,
                    "url": link.group(1) if link else "",
                    "when": link.group(2).strip() if link else "",
                    "pp": bool(re.search(r"\bPP\d?\b|power play", txt, re.I))})
    return out[:KEEP]


# their own nav, in whichever spelling the markup uses, pointed at the file beside this one
NAV = {"/": "gdt-all.html", "/lines": "gdt-lines.html",
       "/news": "gdt-news.html", "/goalies": "gdt-goalies.html"}
NAV.update({SITE + p: f for p, f in list(NAV.items()) if p != "/"})
NAV[SITE + "/"] = "gdt-all.html"
ASSET = re.compile(r'\s(src|href)="(/[^/][^"]*)"')
A_TAG = re.compile(r"<a\s([^>]*?)>", re.S)
HREF = re.compile(r'href="([^"]*)"')
# their inline analytics handlers.  Spelt out rather than \son[a-z]+= , which also eats "once="
ON_ATTR = re.compile(r'\son(?:click|load|error|submit|change|input|focus|blur|'
                     r'key[a-z]+|mouse[a-z]+|touch[a-z]+)="[^"]*"', re.I)
# their webfont answers without Access-Control-Allow-Origin, so a framed page can only log the
# failure and fall back to the system font.  Skip the stylesheet and go straight to the fallback.
FONT_CSS = re.compile(r"<link[^>]*inter-font[^>]*>", re.I)


def viewable(html, path, when):
    """Their page, ready to be framed from our own origin.

    Nothing of theirs is allowed to run - every script goes, and the frame around it withholds
    allow-scripts as well, which is two locks on the same door.  What stays is their markup and
    their stylesheet, so it reads as their page rather than as our retelling of it.
    """
    s = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    s = re.sub(r"<noscript.*?</noscript>", "", s, flags=re.S)
    s = ON_ATTR.sub("", s)
    s = FONT_CSS.sub("", s)

    # their nav first, so the four pages walk to each other inside the frame
    for href, f in NAV.items():
        s = s.replace(f'href="{href}"', f'href="{f}"')
    # everything else they serve - stylesheet, club logos, sponsor art - off their own server
    s = ASSET.sub(lambda m: f' {m.group(1)}="{SITE}{m.group(2)}"', s)

    # a link that is not one of our four files leaves for the real site, in its own tab
    def out(m):
        attrs = m.group(1)
        h = HREF.search(attrs)
        if not h or h.group(1) in NAV.values() or "target=" in attrs:
            return m.group(0)
        return f'<a {attrs} target="_blank" rel="noopener">'
    s = A_TAG.sub(out, s)

    head = (f"<!-- gamedaytweets.com{path}, read {when}.  Their page, kept for the Game Day tab; "
            f"scripts removed, links sent back to them.  Rebuilt by build/gdt_lines.py. -->\n")
    if "charset" not in s[:600].lower():
        s = s.replace("<head>", '<head><meta charset="utf-8">', 1)
    return head + s


def fetch(path="/lines"):
    with urllib.request.urlopen(urllib.request.Request(SITE + path, headers=UA), timeout=40) as f:
        raw = f.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:               # should not happen; cp1252 rescues the accents if it does
        return raw.decode("cp1252", "replace")


if __name__ == "__main__":
    out_dir = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "site"
    when = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    got, lines = {}, None
    for path, name in PAGES:
        try:
            got[name] = fetch(path)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"gamedaytweets{path} is not answering ({e}); leaving {name} as it is")
    lines = scrape(got.get("gdt-lines.html", ""))

    if "--print" in sys.argv:
        for path, name in PAGES:
            page = got.get(name)
            print(f"{path:10s} {'-' if page is None else str(len(page) // 1024) + ' KB':>7s}"
                  f"  -> {name}{'' if page is None else ' (' + str(len(viewable(page, path, when)) // 1024) + ' KB viewable)'}")
        for t in lines[:5]:
            print("    {:20s} {:14s} {}".format(t["who"], t["when"], t["txt"].splitlines()[0][:60]))
        print(f"{len(lines)} line tweets, {sum(1 for t in lines if t['pp'])} of them power play")
        sys.exit(0)

    out_dir.mkdir(parents=True, exist_ok=True)
    for path, name in PAGES:
        if name in got:
            (out_dir / name).write_text(viewable(got[name], path, when), encoding="utf-8")
            print(f"  {name}  {(out_dir / name).stat().st_size // 1024} KB")
    if len(lines) < 3:
        print(f"only {len(lines)} tweets parsed - the feed page has probably changed shape; "
              f"line-tweets.json left as it is")
        sys.exit(0)
    (out_dir / "line-tweets.json").write_text(json.dumps(
        {"fetched": when, "source": "gamedaytweets.com/lines", "tweets": lines},
        ensure_ascii=False), encoding="utf-8")
    print(f"{len(lines)} tweets written to {out_dir / 'line-tweets.json'}")
