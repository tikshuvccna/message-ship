"""Smoke test: the MAIN page (index.html) with the voyage engine: emit voyage:start on its bus, screenshot.
usage: python -I tools/voyage_main_smoke.py <out.png>"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright
CFG = """{seed: 3, leg: 1, nodeId: 'smoke_1', nodeKind: 'battle', look: 'boy', playerName: 'x', twoPlayers: false,
 stats: {hullMax: 100, reloadSec: 1.6, shotPower: 1, sailSpeed: 1, repairSpeed: 1, lanternRadius: 260, doubleShot: false, shield: false},
 ammo: ['addr','code','fmt','size','time'], duration: 80, checkpointHull: 1, quality: 'medium'}"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True, args=["--headless=new", "--use-angle=d3d11"])
    pg = b.new_context(viewport={"width": 1280, "height": 720}).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto("http://localhost:5181/?fresh", wait_until="domcontentloaded")
    pg.wait_for_function("() => window.__ms && window.__ms.bus", timeout=20000)
    pg.wait_for_timeout(1500)
    hud = []
    pg.evaluate("() => { window.__hud = 0; window.__ms.bus.on('voyage:hud', () => window.__hud++); window.__ms.bus.emit('voyage:start', " + CFG + "); }")
    pg.wait_for_timeout(6000)
    print("hud events", pg.evaluate("() => window.__hud"), "fps", pg.evaluate("() => window.__ms.game.loop.actualFps"))
    pg.screenshot(path=sys.argv[1])
    for e in errs[:10]: print("ERR", e)
    b.close()
