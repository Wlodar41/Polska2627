"""Standings: today's rank change beside each rank.

Christopher, 17 Oct 2026: show the day's movement only.  A team that climbs from 3rd to 1st today gets a green
up arrow and 2; a team that slips one place gets a small red down arrow and 1.  Nothing shows for no change.

How: the rank now against the rank before today's points (now minus today's points), both as competition ranks
(1 + the number of teams with more points), so ties never make phantom arrows.  It resets each day by itself:
before tonight's first goal nobody has moved.  Shown in the table (rank column) and the to-scale view (rank chip).

    python build/standings_move.py index.html
Safe to run again; keeps the file's own line endings.
"""
import sys

MARK = "function dayMoves("

CSS_ANCHOR = ".stt tr.first .c-rk{color:var(--accent)}"
CSS_ADD = """
/* today's rank change (build/standings_move.py) */
.rkmv{display:block;font-family:var(--num);font-size:10.5px;font-weight:700;line-height:1;margin-top:2px;letter-spacing:0;white-space:nowrap}
.rkmv.up{color:var(--live)}.rkmv.dn{color:var(--bad)}
.sp-chip .rkmv{display:inline-block;margin:0 0 0 -3px;font-size:10.5px}"""

JS_ANCHOR = "function renderStandings(){"
JS_ADD = """/* today's rank change by team id: rank before today's points minus rank now (build/standings_move.py).
   now and today are {team id: points}; competition ranks, so a tie never shows a move */
function dayMoves(now,today){const ids=Object.keys(now),before={},M={};
  ids.forEach(id=>before[id]=now[id]-(today[id]||0));
  const rk=(V,id)=>1+ids.filter(x=>V[x]>V[id]).length;
  ids.forEach(id=>M[id]=rk(before,id)-rk(now,id));return M;}
const rkMove=m=>m>0?`<span class="rkmv up" title="Up ${m} today">▲${m}</span>`:m<0?`<span class="rkmv dn" title="Down ${-m} today">▼${-m}</span>`:"";
"""

# the table: season points now and today's points are already on each row
TBL_OLD = "  const cols=stCols();\n  if(!cols.some(c=>c[0]===stsort.k))"
TBL_NEW = ("  const MV=dayMoves(Object.fromEntries(rows.map(r=>[r.t.id,r.total])),Object.fromEntries(rows.map(r=>[r.t.id,r.tdy])));\n"
           "  const cols=stCols();\n  if(!cols.some(c=>c[0]===stsort.k))")
CELL_OLD = '<td class="c-rk">${r.rk}</td>'
CELL_NEW = '<td class="c-rk">${r.rk}${rkMove(MV[r.t.id])}</td>'

# the to-scale view: its own range; today only counts when the range runs through today
SP_OLD = "const ord2=[...T].sort((a,b)=>P[b.id]-P[a.id]),lead=P[ord2[0].id],low=P[ord2[ord2.length-1].id];"
SP_NEW = (SP_OLD + "\n  const MV=dayMoves(P,d0<=A&&d1>=A?Object.fromEntries(T.map(t=>[t.id,teamSum(t.id,A,A).pts])):{});")
CHIP_OLD = '<span class="rk2">${x.i+1}</span>'
CHIP_NEW = '<span class="rk2">${x.i+1}</span>${rkMove(MV[x.t.id])}'


def main(path):
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    if MARK in s:
        print("already patched, nothing to do")
        return
    pairs = [(CSS_ANCHOR, CSS_ANCHOR + CSS_ADD), (JS_ANCHOR, JS_ADD + JS_ANCHOR), (TBL_OLD, TBL_NEW),
             (CELL_OLD, CELL_NEW), (SP_OLD, SP_NEW), (CHIP_OLD, CHIP_NEW)]
    for old, _ in pairs:
        if s.count(old) != 1:
            sys.exit(f"stopped: a spot was found {s.count(old)} times (expected 1): {old[:60]!r}; nothing written")
    for old, new in pairs:
        s = s.replace(old, new, 1)
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))
    print("patched: today's rank change on Standings")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "index.html")
