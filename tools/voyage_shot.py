"""Voyage engine visual check in the real Chrome (GPU, headless=new).
usage: python -I tools/voyage_shot.py <query> <out_prefix> [shots] [script]
  query   : dev.html query string, e.g. "kind=battle&leg=1&seed=7"
  shots   : comma list of seconds at which to screenshot (default "3,8")
  script  : optional JS run once after load (has access to window.__dev)
Prints fps (average over the run), console errors, and the debug panel text.
Server: npx vite --port 5181 (started separately).
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = os.environ.get("VOY_URL", "http://localhost:5181/dev.html")

def main():
    query, prefix = sys.argv[1], sys.argv[2]
    shots = [float(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "3,8").split(",")]
    script = sys.argv[4] if len(sys.argv) > 4 else ""
    W, H = int(os.environ.get("VOY_W", 1600)), int(os.environ.get("VOY_H", 900))
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, headless=True,
                              args=["--headless=new", "--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist",
                                    "--disable-background-timer-throttling", "--disable-renderer-backgrounding"])
        ctx = b.new_context(viewport={"width": W, "height": H})
        pg = ctx.new_page()
        logs = []
        pg.on("console", lambda m: logs.append(m.type + ": " + m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: logs.append("PAGEERROR: " + str(e)))
        pg.goto(BASE + "?" + query, wait_until="domcontentloaded")
        try:
            pg.wait_for_function("() => window.__dev && window.__dev.sim()", timeout=20000)
        except Exception as e:
            pg.screenshot(path=prefix + "_fail.png")
            print("NOT STARTED", e)
            for l in logs[:25]:
                print("  ", l)
            b.close()
            return
        if script:
            try:
                r = pg.evaluate(script)
                if r is not None:
                    print("script:", r)
            except Exception as e:
                print("script error", e)
        pg.evaluate("() => window.__dev.resetFps()")
        t = 0.0
        for s in shots:
            pg.wait_for_timeout(int((s - t) * 1000))
            t = s
            out = f"{prefix}_{s:g}s.png"
            pg.screenshot(path=out)
            print("shot", out)
        print("fps", pg.evaluate("() => window.__dev.fps()"))
        print("panel", pg.evaluate("() => document.getElementById('dbg').textContent"))
        print("gpu", pg.evaluate("() => { const g = window.__dev.game; return g.renderer.type === 2 ? 'webgl' : 'canvas'; }"))
        for l in logs[:15]:
            print("  ", l)
        b.close()

main()
