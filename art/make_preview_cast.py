"""python art/make_preview_cast.py -> art/preview_cast.png: each sheet (S, SE, E, NE, N, walk_SW_2, idle blink) at 2x."""
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "public", "assets", "characters")
names = ["hero_girl", "hero_boy", "naama", "uri", "talia", "barak", "skin_girl_sea", "skin_boy_navy", "bit"]
frames = ["idle_S_0", "idle_SE_0", "idle_E_0", "idle_NE_0", "idle_N_0", "walk_SW_2", "walk_E_5", "idle_S_3"]
sheet = Image.new("RGBA", (8 * 256, len(names) * 230), (214, 167, 100, 255))
for r, n in enumerate(names):
    js = json.load(open(os.path.join(C, n + ".json")))
    im = Image.open(os.path.join(C, n + ".png")).convert("RGBA")
    fl = frames if n != "bit" else ["float_0", "float_1", "float_2", "float_3"]
    for c, f in enumerate(fl):
        q = js["frames"][f]["frame"]
        cell = im.crop((q["x"], q["y"], q["x"] + q["w"], q["y"] + q["h"])).resize((256, 256), Image.NEAREST)
        sheet.alpha_composite(cell, (c * 256, r * 230 - 20))
sheet.save(os.path.join(ROOT, "art", "preview_cast.png"))
print("ok")
