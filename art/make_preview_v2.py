"""Contact sheet for the v2 characters -> art/preview_characters_v2.png
Sections: heroes (8 dirs, true scale + 2x), NPCs (5 dirs, true scale + 2x), portraits (all expressions),
creatures (4 dirs idle + walk frame, true scale), legendaries, codex cards."""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "public", "assets")
BG = (96, 120, 84, 255)
BG2 = (110, 112, 128, 255)
W = 2048


def load(path):
    return Image.open(path).convert("RGBA"), json.load(open(path[:-4] + ".json", encoding="utf8"))


def crop(sh, js, fn):
    f = js["frames"][fn]["frame"]
    return sh.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))


def label(img, text, y):
    ImageDraw.Draw(img).text((8, y + 4), text, fill=(255, 250, 230, 255))


blocks = []
# ---- heroes
DIRS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
for n in ("apprentice_girl", "apprentice_girl_scarf", "apprentice_boy", "apprentice_boy_hat", "dvora"):
    sh, js = load(os.path.join(A, "characters_v2", n + ".png"))
    row = Image.new("RGBA", (128 * 11, 128), BG)
    for i, d in enumerate(DIRS):
        row.alpha_composite(crop(sh, js, f"walk_{d}_2"), (i * 128, 0))
    row.alpha_composite(crop(sh, js, "idle_S_0"), (8 * 128, 0))
    row.alpha_composite(crop(sh, js, "idle_S_3"), (9 * 128, 0))
    row.alpha_composite(crop(sh, js, "walk_E_5"), (10 * 128, 0))
    big = row.crop((0, 0, 128 * 8, 128)).resize((128 * 16, 256), Image.LANCZOS)
    blocks.append((f"{n}: walk frame 2 in S SW W NW N NE E SE, idle S, blink, walk E5 (true scale) / 2x", BG, [row, big]))
# ---- NPCs
nd = os.path.join(A, "characters_v2", "npcs")
names = sorted(json.load(open(os.path.join(nd, "index.json"))))
per = 12
bands = (len(names) + per - 1) // per
row1 = Image.new("RGBA", (W, 128 * 5 * bands), BG)
for k, n in enumerate(names):
    sh, js = load(os.path.join(nd, n + ".png"))
    for r, d in enumerate(["S", "SE", "E", "SW", "W"]):
        row1.alpha_composite(crop(sh, js, f"idle_{d}_0"), ((k % per) * 168, (k // per) * 640 + r * 128))
big = Image.new("RGBA", (W, 256 * ((len(names) + 8) // 9)), BG)
for k, n in enumerate(names):
    sh, js = load(os.path.join(nd, n + ".png"))
    im = crop(sh, js, "idle_SE_0").resize((256, 256), Image.LANCZOS)
    big.alpha_composite(im, ((k % 9) * 224 - 20, (k // 9) * 256))
blocks.append(("NPCs (" + ", ".join(names) + "): rows S SE E SW W, true scale; below SE at 2x", BG, [row1, big]))
# ---- portraits
pd = os.path.join(A, "portraits")
pidx = json.load(open(os.path.join(pd, "index.json")))
c = 200
prow = []
for n, exs in pidx.items():
    sh, js = load(os.path.join(pd, n + ".png"))
    r = Image.new("RGBA", (W, c), BG2)
    for k, ex in enumerate(exs):
        r.alpha_composite(crop(sh, js, f"{n}_{ex}").resize((c, c), Image.LANCZOS), (k * (c + 8), 0))
    prow.append(r)
blocks.append(("Portraits: " + " | ".join(f"{n}: {' '.join(e)}" for n, e in pidx.items()), BG2, prow))
# ---- creatures
cd = os.path.join(A, "creatures")
cidx = json.load(open(os.path.join(cd, "index.json"), encoding="utf8"))
small = [n for n, v in cidx.items() if not v["legendary"]]
legend = [n for n, v in cidx.items() if v["legendary"]]
crow = Image.new("RGBA", (W, 128 * 2 * ((len(small) + 2) // 3)), BG)
for k, n in enumerate(small):
    sh, js = load(os.path.join(cd, n + ".png"))
    x0, y0 = (k % 3) * 680, (k // 3) * 256
    for j, d in enumerate(["S", "SE", "E", "N"]):
        crow.alpha_composite(crop(sh, js, f"idle_{d}_0"), (x0 + j * 128, y0))
    crow.alpha_composite(crop(sh, js, "walk_E_2"), (x0 + 4 * 128, y0))
    crow.alpha_composite(crop(sh, js, "idle_SE_0").resize((128, 128), Image.LANCZOS), (x0, y0 + 128))
    crow.alpha_composite(crop(sh, js, "idle_S_0").resize((85, 85), Image.LANCZOS), (x0 + 150, y0 + 150))
blocks.append(("Creatures: S SE E N idle, walk E; below: SE, and S at exact world scale (0.667)", BG, [crow]))
lrow = Image.new("RGBA", (W, 384), BG2)
x = 0
for n in legend:
    sh, js = load(os.path.join(cd, n + ".png"))
    for i in range(2):
        im = crop(sh, js, f"idle_{i * 2}")
        lrow.alpha_composite(im, (x, 384 - im.height))
        x += im.width
blocks.append(("Legendaries (idle 0 and 2): " + ", ".join(legend), BG2, [lrow]))
cx = Image.open(os.path.join(cd, "codex.png")).convert("RGBA")
crow2 = Image.new("RGBA", (W, cx.height // 2), BG2)
half = cx.resize((cx.width // 2, cx.height // 2), Image.LANCZOS)
crow2.alpha_composite(half, (0, 0))
blocks.append(("Codex cards (256 px each, shown at half size)", BG2, [crow2]))
hs = Image.open(os.path.join(cd, "the_head.png")).convert("RGBA")
hrow = Image.new("RGBA", (W, 512), (70, 80, 110, 255))
hrow.alpha_composite(hs.crop((0, 0, 1024, 512)), (0, 0))
hrow.alpha_composite(hs.crop((0, 512, 1024, 1024)), (1024, 0))
blocks.append(("THE HEAD (1024x512): benevolent facade | truth", (70, 80, 110, 255), [hrow]))

H = sum(22 + sum(im.height for im in ims) for _, _, ims in blocks)
out = Image.new("RGBA", (W, H), (60, 60, 70, 255))
y = 0
for title, bg, ims in blocks:
    label(out, title[:330], y)
    y += 22
    for im in ims:
        bgim = Image.new("RGBA", (W, im.height), bg)
        bgim.alpha_composite(im.crop((0, 0, min(W, im.width), im.height)), (0, 0))
        out.alpha_composite(bgim, (0, y))
        y += im.height
out.convert("RGB").save(os.path.join(ROOT, "art", "preview_characters_v2.png"), optimize=True)
print("preview", out.size)
