"""Tonight board: show who is done, live and still to play.

1. Replaces the single "13 PLAYING" pill on the Tonight board with one small block per rostered player
   (filled blue = his game is final, pulsing green = his game is on, outline = not started yet) and a
   count line under it ("4 DONE · 2 LIVE · 7 TO PLAY").  Every block is the same size; a long roster
   wraps onto a second row rather than squeezing the blocks.
2. Puts games played beside each name ("4/13": players whose game is final, out of everyone he has
   playing tonight), so you can see at a glance who has the most games left.
Past and future days keep the old pill and no count.

The game state comes from D.gsum, which the refresh already writes, so nothing new is fetched.

Run on the copy of the site the refresh job builds from:
    python build/tonight_bar.py index.html
Safe to run again: each part is applied once, and a page that already has part 1 just gets part 2.
It keeps the file's own line endings.
"""
import sys

# ---- part 1: the block bar ----
BAR_MARK = "function tnBar("
CSS_ANCHOR = ".off{font-size:12.5px;color:var(--muted)}"
CSS_ADD = """
/* Tonight board: a block per player, done / live / to play (build/tonight_bar.py) */
.tnbar{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}
.tnbar i{flex:0 0 12px;width:12px;height:8px;border-radius:2px;box-sizing:border-box;border:1.5px solid color-mix(in oklab,var(--muted) 75%,transparent)}
.tnbar i.d{background:var(--hi);border-color:var(--hi)}
.tnbar i.l{background:var(--live);border-color:var(--live);animation:tnpz 1.4s ease-in-out infinite}
@keyframes tnpz{50%{opacity:.35}}
@media(prefers-reduced-motion:reduce){.tnbar i.l{animation:none}}
.tnsum{margin-top:4px;font-family:var(--num);font-size:12px;font-weight:600;letter-spacing:.06em;color:var(--muted);white-space:nowrap}
.tnsum b{color:var(--live);font-weight:600}"""
JS_ANCHOR = "function renderTonight(){"
JS_ADD = """/* Tonight board: each player's game as done (d), live (l) or still to come (u), off D.gsum's state by club */
function tnGameState(d){const CODE=x=>({LAK:"LA",NJD:"NJ",SJS:"SJ",TBL:"TB"})[x]||x,S={};
  ((D.gsum&&D.gsum[d])||[]).forEach(g=>{S[CODE(g.h)]=g.st;S[CODE(g.a)]=g.st;});
  return ab=>{const s=S[ab];return s==="OFF"||s==="FINAL"?"d":s==="LIVE"||s==="CRIT"?"l":"u";};}
function tnBar(rows,d){const gs=tnGameState(d),n={d:0,l:0,u:0};rows.forEach(e=>n[gs(e.p.sc)]++);
  const blk=k=>`<i class="${k}"></i>`.repeat(n[k]);
  return `<div class="tnbar" role="img" aria-label="${n.d} done, ${n.l} live, ${n.u} to play">${blk("d")}${blk("l")}${blk("u")}</div>`
    +`<div class="tnsum">${n.d} DONE${n.l?` · <b>${n.l} LIVE</b>`:""} · ${n.u} TO PLAY</div>`;}
"""
ROW_OLD = '${x.rows.length?liveTag(x.rows.length,past?" PLAYED":" PLAYING"):'
ROW_NEW = '${x.rows.length?(tonight?tnBar(x.rows,d):liveTag(x.rows.length,past?" PLAYED":" PLAYING")):'

# ---- part 2: games played beside the name ----
CNT_MARK = "function tnCount("
CNT_CSS = """
.tncnt{flex:0 0 auto;font-family:var(--num);font-size:13px;font-weight:700;letter-spacing:.04em;color:var(--muted);padding:1px 6px;border-radius:5px;border:1px solid color-mix(in oklab,var(--muted) 40%,transparent)}
.tncnt b{color:var(--ink);font-weight:700}"""
CNT_JS_ANCHOR = "function tnBar(rows,d){"
CNT_JS = """/* games played beside the name: final games out of everyone playing tonight */
function tnCount(rows,d){const gs=tnGameState(d),n=rows.filter(e=>gs(e.p.sc)==="d").length;
  return `<span class="tncnt" aria-label="${n} of ${rows.length} games played"><b>${n}</b>/${rows.length}</span>`;}
"""
NAME_OLD = '<div class="tn tnl">${logo(x.t.name)}<span>${esc(person(x.t.name))}</span></div>'
NAME_NEW = '<div class="tn tnl">${logo(x.t.name)}<span>${esc(person(x.t.name))}</span>${tonight&&x.rows.length?tnCount(x.rows,d):""}</div>'


def need_once(s, old, name):
    if s.count(old) != 1:
        sys.exit(f"stopped: the {name} spot was found {s.count(old)} times (expected 1); the page has changed, nothing written")


def main(path):
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    done = []
    if BAR_MARK not in s:
        for name, old in (("css", CSS_ANCHOR), ("js", JS_ANCHOR), ("row", ROW_OLD)):
            need_once(s, old, name)
        s = s.replace(CSS_ANCHOR, CSS_ANCHOR + CSS_ADD, 1)
        s = s.replace(JS_ANCHOR, JS_ADD + JS_ANCHOR, 1)
        s = s.replace(ROW_OLD, ROW_NEW, 1)
        done.append("done / live / to play blocks")
    if CNT_MARK not in s:
        need_once(s, CSS_ANCHOR + CSS_ADD, "count css")
        need_once(s, CNT_JS_ANCHOR, "count js")
        need_once(s, NAME_OLD, "name")
        s = s.replace(CSS_ANCHOR + CSS_ADD, CSS_ANCHOR + CSS_ADD + CNT_CSS, 1)
        s = s.replace(CNT_JS_ANCHOR, CNT_JS + CNT_JS_ANCHOR, 1)
        s = s.replace(NAME_OLD, NAME_NEW, 1)
        done.append("games played beside the name")
    if not done:
        print("already patched, nothing to do")
        return
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))
    print("patched: " + ", ".join(done))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "index.html")
