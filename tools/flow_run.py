"""Plays the real main page from the title into the first voyage and screenshots each stage.
usage: python -I tools/flow_run.py <out_prefix> [WxH] [base_url]"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from playwright.sync_api import sync_playwright

prefix = sys.argv[1]
w, h = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else "1280x720").split("x")]
base = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:5201/"
touch = w < 800

def click_text(pg, text, timeout=4000):
    pg.get_by_role("button", name=text).first.click(timeout=timeout)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True, args=["--headless=new", "--use-angle=d3d11"])
    pg = b.new_context(viewport={"width": w, "height": h}, has_touch=touch, is_mobile=touch).new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append("PAGEERROR " + str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "404" not in m.text else None)
    pg.goto(base + "?fresh", wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.screenshot(path=f"{prefix}_1title.png")
    click_text(pg, "התחלה")
    pg.wait_for_timeout(500)
    pg.screenshot(path=f"{prefix}_2hero.png")
    click_text(pg, "הפלגה")
    for i in range(14):   # dialogue lines: tap twice per line (finish typing, advance)
        pg.mouse.click(w // 2, h // 2); pg.wait_for_timeout(150)
        pg.mouse.click(w // 2, h // 2); pg.wait_for_timeout(250)
        if i == 2: pg.screenshot(path=f"{prefix}_3dialogue.png")
        if pg.locator(".help-screen").count(): break
    pg.screenshot(path=f"{prefix}_4help.png")
    click_text(pg, "הבנתי")
    pg.wait_for_timeout(500)
    pg.screenshot(path=f"{prefix}_5chart.png")
    pg.locator(".node.open").first.click()
    pg.wait_for_timeout(3500)
    pg.screenshot(path=f"{prefix}_6voyage_a.png")
    pg.keyboard.down("d"); pg.wait_for_timeout(900); pg.keyboard.up("d")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=f"{prefix}_7voyage_b.png")
    print("fps", pg.evaluate("() => window.__ms.game.loop.actualFps"))
    for e in errs[:10]: print("ERR", e)
    b.close()
