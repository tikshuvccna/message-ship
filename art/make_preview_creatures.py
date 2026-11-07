"""Contact sheet of the creatures atlas (noise_0, noise_1, friend_0, friend_1 per row) on sea blue + codex PNGs.
python art/make_preview_creatures.py  -> art/preview_creatures.png, public/assets/creatures/<id>.png (friend_0, codex)"""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "public", "assets", "creatures")
js = json.load(open(os.path.join(A, "creatures.json"), encoding="utf-8"))
im = Image.open(os.path.join(A, "creatures.png")).convert("RGBA")
data = json.load(open(os.path.join(ROOT, "content", "he", "creatures.json"), encoding="utf-8"))
ids = [c["id"] for c in data["creatures"] if c["id"] != "garble_kraken"]


def fr(n):
    r = js["frames"][n]["frame"]
    return im.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"])), js["frames"][n]["anchorPx"]


COLW, ROWH = 190, 0
rows = []
for cid in ids:
    cells = [fr(f"{cid}_{s}_{i}") for s in ("noise", "friend") for i in (0, 1)]
    rows.append(cells)
heights = [max(c[0].height for c in r) + 16 for r in rows]
W = 4 * COLW + 20
H = sum(heights) + 20
cols = ((40, 46, 70), (40, 46, 70), (58, 132, 160), (58, 132, 160))
sheet = Image.new("RGBA", (W, H), (58, 132, 160, 255))
d = ImageDraw.Draw(sheet)
y = 10
for r, h in zip(rows, heights):
    for k, (img, a) in enumerate(r):
        x0 = 10 + k * COLW
        d.rectangle((x0, y, x0 + COLW - 4, y + h - 4), fill=cols[k] + (255,))
        sheet.alpha_composite(img, (int(x0 + COLW / 2 - a["x"]), int(y + h - 10 - img.height)))
    y += h
sheet.save(os.path.join(ROOT, "art", "preview_creatures.png"))
# codex singles: friend frame 0 (plus noise for reference)
for cid in ids:
    for st in ("friend", "noise"):
        img, a = fr(f"{cid}_{st}_0")
        img.save(os.path.join(A, f"{cid}.png" if st == "friend" else f"{cid}_noise.png"), optimize=True)
print("ok", len(ids))
