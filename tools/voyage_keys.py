"""Drive the dev harness with the REAL keyboard (Playwright key events into Chrome) and screenshot.
usage: python -I tools/voyage_keys.py <query> <out_prefix>
Walks P1 to the rack (WASD), takes a ball (E), carries it to the near cannon, loads (E), aims (A/D), fires (Space).
"""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE = "http://localhost:5181/dev.html"
q, prefix = sys.argv[1], sys.argv[2]
STATE = "() => { const s = window.__dev.sim(); const p = s.w.players[0]; return { x: +p.x.toFixed(2), y: +p.y.toFixed(2), at: p.at, held: p.held, shots: s.w.acc.shots, loaded: s.w.cannons.cannon_near.loaded, prompt: document.getElementById('prompt').textContent }; }"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True, args=["--headless=new", "--use-angle=d3d11", "--enable-gpu"])
    pg = b.new_context(viewport={"width": 1600, "height": 900}).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(BASE + "?" + q, wait_until="domcontentloaded")
    pg.wait_for_function("() => window.__dev && window.__dev.sim()", timeout=20000)
    pg.wait_for_timeout(800)
    pg.click("canvas")
    def hold(k, ms):
        pg.keyboard.down(k); pg.wait_for_timeout(ms); pg.keyboard.up(k)
    def walk_to(x, y, tol=0.25):
        for _ in range(60):
            s = pg.evaluate(STATE)
            dx, dy = x - s["x"], y - s["y"]
            if abs(dx) < tol and abs(dy) < tol: return s
            keys = []
            if dx > tol: keys.append("d")
            if dx < -tol: keys.append("a")
            if dy > tol: keys.append("w")
            if dy < -tol: keys.append("s")
            for k in keys: pg.keyboard.down(k)
            pg.wait_for_timeout(int(min(250, 1000 * max(abs(dx), abs(dy)) / 3.3)))
            for k in keys: pg.keyboard.up(k)
        return pg.evaluate(STATE)
    print("start", pg.evaluate(STATE))
    print("at rack", walk_to(-3.2, 2.2))
    pg.screenshot(path=prefix + "_rack.png")
    pg.keyboard.press("e"); pg.wait_for_timeout(200)
    print("took", pg.evaluate(STATE))
    print("detour", walk_to(-1.0, 0.0))
    print("at cannon", walk_to(1.0, -1.75))
    pg.keyboard.press("e"); pg.wait_for_timeout(300)
    print("loaded", pg.evaluate(STATE))
    pg.screenshot(path=prefix + "_loading.png")
    pg.wait_for_timeout(1500)
    hold("d", 400)
    pg.screenshot(path=prefix + "_aim.png")
    pg.keyboard.press("Space"); pg.wait_for_timeout(120)
    pg.screenshot(path=prefix + "_fire.png")
    pg.wait_for_timeout(500)
    print("fired", pg.evaluate(STATE))
    pg.keyboard.press("e"); pg.wait_for_timeout(200)
    print("left", pg.evaluate(STATE))
    for e in errs: print("ERR", e)
    b.close()
