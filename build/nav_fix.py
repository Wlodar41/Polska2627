"""Keep the floating tab bar on the bottom of the screen on iPhones (15 Oct 2026).

Christopher: "in team page it gets stuck mid screen when scrolling".
iOS 26 Safari has a known bug: after a dropdown picker (the team picker is a <select>) or the
keyboard closes, the bottom of the "fixed" layout and the bottom of the visible screen disagree,
so anything position:fixed to the bottom is left part way up the screen.  The page now measures
the visible screen (visualViewport) and pulls the bar back down by the gap.  Everywhere else the
gap is 0 and nothing changes.

Run once against the page (it is safe to run again; it skips anything already applied):
  python build/nav_fix.py index.html
"""
import sys

MARK = "--vvdy"

CSS_OLD_NAV = "html:root[data-scheme][lang] nav{position:fixed;top:auto;bottom:calc(36px + env(safe-area-inset-bottom,0px));"
CSS_NEW_NAV = "html:root[data-scheme][lang] nav{position:fixed;top:auto;bottom:calc(36px + env(safe-area-inset-bottom,0px) - var(--vvdy,0px));"
CSS_OLD_BAR = "html:root[data-scheme][lang] .nbar{bottom:calc(106px + env(safe-area-inset-bottom,0px))}"
CSS_NEW_BAR = ("html:root[data-scheme][lang] .nbar{bottom:calc(106px + env(safe-area-inset-bottom,0px) - var(--vvdy,0px))}\n"
               "/* --vvdy: how far the visible bottom of an iPhone screen sits below the layout's bottom (0 almost\n"
               "   always).  Set by the visualViewport watcher in the script; see build/nav_fix.py. */")

JS_ANCHOR = "/* how tall the sticky tab bar is, so the Daily day strip pins just below it */"
JS_NEW = r"""/* iPhone Safari (iOS 26+): after a dropdown picker or the keyboard closes, the bottom of the "fixed"
   layout and the bottom of the visible screen can disagree, which left the floating tab bar stuck
   part way up the screen (the team picker is the usual trigger).  Measure the visible screen and
   pull the bar back down by the gap.  Everywhere else the gap is 0 and this does nothing. (15 Oct 2026) */
(function(){
  var vv=window.visualViewport,r=document.documentElement,raf=0,last=0;if(!vv)return;
  function typing(){var a=document.activeElement;if(!a)return false;
    return a.tagName==="TEXTAREA"||a.isContentEditable||(a.tagName==="INPUT"&&!/^(button|checkbox|radio|range|submit|reset|color|file|image)$/i.test(a.type||""));}
  function fit(){raf=0;
    var d=Math.round(vv.offsetTop+vv.height-window.innerHeight);
    /* only the stuck-too-high case (the visible bottom is below the layout's): a gap the other way is a
       picker or keyboard covering the bar, which is fine.  Nothing while typing, pinch-zoomed, or for a
       gap that is noise or absurd */
    if(typing()||vv.scale>1.01||d<2||d>window.innerHeight*0.6)d=0;
    if(d!==last){last=d;if(d)r.style.setProperty("--vvdy",d+"px");else r.style.removeProperty("--vvdy");}
  }
  function ask(){if(!raf)raf=requestAnimationFrame(fit);}
  vv.addEventListener("resize",ask);vv.addEventListener("scroll",ask);
  window.addEventListener("scroll",ask,{passive:true});window.addEventListener("resize",ask);
  /* a closed picker is what knocks it loose: nudge Safari to settle its viewport, then measure again */
  document.addEventListener("focusout",function(e){
    var t=e.target;if(!t||!t.matches||!t.matches("select,input,textarea"))return;
    setTimeout(function(){window.scrollTo(window.scrollX,window.scrollY);ask();},60);
    setTimeout(ask,400);
  });
  document.addEventListener("change",function(e){var t=e.target;if(t&&t.matches&&t.matches("select"))setTimeout(ask,300);});
  ask();
})();
"""


def main(path):
    s = open(path, encoding="utf-8", newline="").read()   # keep the file's own line endings (Windows PC)
    if MARK in s:
        print("already applied, nothing to do")
        return 0
    for old in (CSS_OLD_NAV, CSS_OLD_BAR, JS_ANCHOR):
        if s.count(old) != 1:
            print("could not find exactly one of:\n  " + old[:90] + "\nthe page has changed; not touching it")
            return 1
    s = s.replace(CSS_OLD_NAV, CSS_NEW_NAV).replace(CSS_OLD_BAR, CSS_NEW_BAR)
    s = s.replace(JS_ANCHOR, JS_NEW + JS_ANCHOR)
    open(path, "w", encoding="utf-8", newline="").write(s)
    print("applied")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "index.html"))
