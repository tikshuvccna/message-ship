"""Quick look: python art/view.py out.png [zoom] raw1.png [raw2.png ...]
Finishes each raw frame (outline + 4x downscale) and lays them out on a sea-blue background."""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack_atlas import finish

out = sys.argv[1]
zoom = float(sys.argv[2])
ims = [finish(p) for p in sys.argv[3:]]
W = sum(i.width for i in ims) + 20 * (len(ims) + 1)
H = max(i.height for i in ims) + 40
bg = Image.new("RGBA", (W, H), (58, 132, 160, 255))
x = 20
for im in ims:
    bg.alpha_composite(im, (x, 20))
    x += im.width + 20
if zoom != 1:
    bg = bg.resize((int(W * zoom), int(H * zoom)), Image.LANCZOS if zoom < 1 else Image.NEAREST)
bg.save(out)
print(out, bg.size)
