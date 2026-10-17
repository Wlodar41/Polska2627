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

# ---- part 3: Daily player list shows the game's score and period/clock ----
GST_MARK = "function tnMatch("
GST_CSS_ANCHOR = "#tnlist .ln3 .gtm{color:var(--ink-2)}"
GST_CSS = """
#tnlist .ln3 .gst{font-family:var(--num);font-weight:600;letter-spacing:.04em;color:var(--ink-2);font-variant-numeric:tabular-nums;white-space:nowrap}
#tnlist .ln3 .gst.on{color:var(--live)}
#tnlist .ln3 .gst b.w{color:var(--live);font-weight:700}
#tnlist .ln3 .gst b.l{color:var(--bad);font-weight:700}"""
GST_JS = """/* Daily list: the game's state beside the opponent, off D.gsum: puck drop, the score and period/clock while it
   is on, or W/L, the score and Final once it is over.  His own club's goals first. */
function tnMatch(p,d){const g=gameOn(p,d);if(!g)return "";
  const CODE=x=>({LAK:"LA",NJD:"NJ",SJS:"SJ",TBL:"TB"})[x]||x;
  const G=((D.gsum&&D.gsum[d])||[]).find(x=>CODE(x.h)===p.sc||CODE(x.a)===p.sc);
  const vs=`<span class="vs">${g.home?"vs":"@"} ${esc(g.opp)}</span> `;
  if(!G||G.st==="FUT"||G.st==="PRE")return vs+`<span class="gtm">${clock(d,g.t)}</span>`;
  const home=CODE(G.h)===p.sc,mine=(home?G.hs:G.as)??0,them=(home?G.as:G.hs)??0,st=gameState(G,d,g.t);
  if(G.st==="OFF"||G.st==="FINAL")
    return vs+`<span class="gst fin"><b class="${mine>them?"w":"l"}">${mine>them?"W":"L"}</b> ${mine}–${them} · ${esc(st.txt)}</span>`;
  return vs+`<span class="gst on">${mine}–${them} · ${esc(st.txt)}</span>`;}
"""
LINE3_OLD = "line3:matchup(e.p,d),"
LINE3_NEW = "line3:tnMatch(e.p,d),"

# ---- part 4: across the site, no green "playing" dot or ring once a player's game is final ----
DONE_MARK = "function gameDone("
DONE_ANCHOR = "const playsTonight=p=>playsOn(p,A);"
DONE_JS = """
/* his club's game that day is over (D.gsum); the green dot and ring stop once it is (build/tonight_bar.py) */
function gameDone(p,d){if(!p)return false;const CODE=x=>({LAK:"LA",NJD:"NJ",SJS:"SJ",TBL:"TB"})[x]||x;
  return ((D.gsum&&D.gsum[d])||[]).some(g=>(g.st==="OFF"||g.st==="FINAL")&&(CODE(g.h)===p.sc||CODE(g.a)===p.sc));}
const liveTonight=p=>playsTonight(p)&&!gameDone(p,A);"""
DONE_SWAPS = [
    ('<div class="lc${playsTonight(p)?" tonite":""}', '<div class="lc${liveTonight(p)?" tonite":""}'),
    ('live:e.active&&playsTonight(e.p),tn:', 'live:e.active&&liveTonight(e.p),tn:'),
    ('live:playsTonight(p),', 'live:liveTonight(p),'),
    ('<div class="ln2">${p&&playsTonight(p)?liveTag(true)+" ":""}', '<div class="ln2">${p&&liveTonight(p)?liveTag(true)+" ":""}'),
    ('live:tonight?true:past?(d===TD-1?"YESTERDAY":fmtDay(d).toUpperCase()):lab(d).toUpperCase()',
     'live:tonight?!gameDone(e.p,d):past?false:lab(d).toUpperCase()'),
]

# ---- part 5: Daily player list, players whose game has started (live or final) above those still to start ----
ORD_MARK = "function tnOrder("
ORD_JS = """/* Daily list order: everyone whose game has started (live or final) first, then those still to start;
   points (then the usual tie-breaks, already applied) within each */
function tnOrder(rows,d){const gs=tnGameState(d),w=e=>gs(e.p.sc)==="u"?1:0;
  return rows.map((e,i)=>[e,i]).sort((x,y)=>w(x[0])-w(y[0])||x[1]-y[1]).map(x=>x[0]);}
"""
ORD_OLD = "+(rows.length?rows.map(e=>prow({p:e.p,"
ORD_NEW = "+(rows.length?tnOrder(rows,d).map(e=>prow({p:e.p,"


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
    if GST_MARK not in s:
        need_once(s, GST_CSS_ANCHOR, "game status css")
        need_once(s, JS_ANCHOR, "game status js")
        need_once(s, LINE3_OLD, "player line")
        s = s.replace(GST_CSS_ANCHOR, GST_CSS_ANCHOR + GST_CSS, 1)
        s = s.replace(JS_ANCHOR, GST_JS + JS_ANCHOR, 1)
        s = s.replace(LINE3_OLD, LINE3_NEW, 1)
        done.append("game score and clock on the Daily list")
    if DONE_MARK not in s:
        need_once(s, DONE_ANCHOR, "playing check")
        for old, _ in DONE_SWAPS:
            need_once(s, old, "green dot")
        s = s.replace(DONE_ANCHOR, DONE_ANCHOR + DONE_JS, 1)
        for old, new in DONE_SWAPS:
            s = s.replace(old, new, 1)
        done.append("no green dot once a game is final")
    if ORD_MARK not in s:
        need_once(s, JS_ANCHOR, "order js")
        need_once(s, ORD_OLD, "player loop")
        s = s.replace(JS_ANCHOR, ORD_JS + JS_ANCHOR, 1)
        s = s.replace(ORD_OLD, ORD_NEW, 1)
        done.append("started players above those still to start")
    if not done:
        print("already patched, nothing to do")
        return
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))
    print("patched: " + ", ".join(done))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "index.html")
