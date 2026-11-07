"""Sea creatures of "Message Ship": every creature in content/he/creatures.json in two looks.

blender -b --python art/blender/sea_creatures.py -- <ABS rawdir> [id ...]
Writes <rawdir>/creatures/<id>_<noise|friend>_<0|1>.png + meta.json (pack: art/pack_atlas.py creatures).
Built facing -Y (towards the camera) then turned to face screen-LEFT and the camera (towards the ship, which
sails on the left). flipX in the engine to face right. Size: radius in creatures.json is in world px (56 px/unit);
the body is modelled at ~1 unit radius and scaled to radius/56, so the sprite matches the hit circle.
Origin (anchor) = point on the water surface under the creature.
noise: dark, glitchy, glowing red-orange eyes, letters (pack step adds RGB split + flaking letters).
friend: colourful and cute.
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Euler

from v2lib import *
from shiplib import Job, ring_tube, grid_mesh, fix_normals_out, brass, proj

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FACE_ROT = math.radians(-48)
NOISE_DARK = "#2a2236"
EYE_NOISE = "#ff6a2a"
FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"


def mixhex(a, b, t):
    A, B = hexlin(a), hexlin(b)
    return lin2hex(tuple(x * (1 - t) + y * t for x, y in zip(A, B)))


class St:
    def __init__(self, state, f):
        self.noise = state == 'noise'
        self.f = f
        self.ph = math.pi * f          # two frames: 0 and pi

    def c(self, hexc, amt=0.7):
        return mixhex(hexc, NOISE_DARK, amt) if self.noise else hexc

    def m(self, hexc, amt=0.7, **kw):
        kw.setdefault('kind', 'soft')
        return mat(self.c(hexc, amt), **kw)


# ------------------------------------------------------------------ faces
def eye_friend(parent, loc, r, iris="#3a2a1a", look=(0.0, 0.0)):
    e = pivot("eye", loc, parent)
    ellipsoid("sclera", r, mat("#fbf4ea", kind='soft', rim=0.2), e, scale=(1, 0.62, 1.1), seg=18, rings=12)
    lx, lz = look
    ellipsoid("iris", r * 0.68, mat(iris, kind='soft', rim=0, line=False), e, loc=(lx * r * 0.3, -r * 0.42, lz * r * 0.3),
              scale=(1, 0.38, 1.05), seg=16, rings=10)
    ellipsoid("pupil", r * 0.4, mat("#140c10", kind='flat', rim=0, line=False), e, loc=(lx * r * 0.32, -r * 0.55, lz * r * 0.32),
              scale=(1, 0.3, 1.05), seg=12, rings=8)
    ellipsoid("hl", r * 0.22, glow("#ffffff", 1.0), e, loc=(-r * 0.26 + lx * r * 0.3, -r * 0.68, r * 0.34), seg=8, rings=6)
    ellipsoid("hl2", r * 0.1, glow("#ffffff", 1.0), e, loc=(r * 0.25, -r * 0.66, -r * 0.25), seg=6, rings=4)
    return e


def eye_noise(parent, loc, r, side=1):
    e = pivot("eyen", loc, parent)
    ellipsoid("sock", r * 1.05, mat("#120c18", kind='flat', rim=0, ao=0), e, scale=(1, 0.5, 0.8), seg=16, rings=10)
    sl = ellipsoid("slit", r * 0.78, glow(EYE_NOISE, 2.6), e, loc=(0, -r * 0.4, 0), scale=(1, 0.3, 0.42), seg=14, rings=8,
                   line=False)
    sl.rotation_euler = (0, side * 0.35, 0)
    ellipsoid("pup", r * 0.22, glow("#ffe0a0", 3.0), e, loc=(0, -r * 0.55, 0), scale=(0.6, 0.3, 1.0), line=False)
    ellipsoid("halo", r * 1.5, glow(EYE_NOISE, 1.2, alpha=0.35, soft=True), e, loc=(0, -r * 0.4, 0), line=False)
    # angry brow
    tube("brow", [Vector((-side * r * 1.1, -r * 0.5, r * 0.55)), Vector((side * r * 0.9, -r * 0.55, r * 1.05))],
         [r * 0.16], mat("#120c18", kind='flat', rim=0), e, seg=6, sub=1, line=False)
    return e


def face(parent, loc, r, st, gap=1.25, iris="#2a4a7a", mouth=True, mouth_dz=-1.2, blush_c="#f08a8a", y_in=0.0):
    x, y, z = loc
    for s in (-1, 1):
        if st.noise:
            eye_noise(parent, (x + s * r * gap, y, z), r, side=s)
        else:
            eye_friend(parent, (x + s * r * gap, y, z), r, iris=iris, look=(0.15, -0.05))
    if not mouth:
        return
    mz = z + r * mouth_dz
    if st.noise:
        pts = [Vector((x - r * 0.8 + i * r * 0.4, y - r * 0.2, mz + (r * 0.18 if i % 2 else -r * 0.05))) for i in range(5)]
        tube("zig", pts, [r * 0.1], mat("#120c18", kind='flat', rim=0), parent, seg=5, sub=1, line=False)
    else:
        w = r * 0.55
        pts = [Vector((x - w, y - r * 0.15, mz + w * 0.45)), Vector((x, y - r * 0.3, mz)), Vector((x + w, y - r * 0.15, mz + w * 0.45))]
        tube("smile", pts, [w * 0.13, w * 0.17, w * 0.13], mat("#5a2a30", kind='flat', rim=0, ao=0, line=False), parent,
             seg=6, sub=4, line=False)
        for s in (-1, 1):
            ellipsoid("blush", r * 0.45, mat(blush_c, kind='soft', rim=0, line=False), parent,
                      loc=(x + s * r * (gap + 0.75), y + r * 0.05, mz + r * 0.35), scale=(1, 0.3, 0.6), line=False)


# ------------------------------------------------------------------ glyphs (3D letters)
_FONT = {}


def font():
    if 'f' not in _FONT:
        try:
            _FONT['f'] = bpy.data.fonts.load(FONT_PATH)
        except Exception:
            _FONT['f'] = None
    return _FONT['f']


def glyph(ch, material, parent, loc, size, rot=(math.pi / 2, 0, 0), extrude=0.03):
    cu = bpy.data.curves.new("g", 'FONT')
    cu.body = ch
    f = font()
    if f:
        cu.font = f
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    o = bpy.data.objects.new("glyph", cu)
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    cu.materials.append(material)
    return o


NOISE_CHARS = "AQ#?%&7Z@$xk"


def glyph_scatter(parent, n, center, rx, rz, size, st, seed, colors=("#c46a3a", "#6a5a7a", "#8a3a3a"), y=-0.0):
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(0, TAU)
        rr = rnd.uniform(0.3, 1.0)
        p = (center[0] + rx * rr * math.cos(a), center[1] + y, center[2] + rz * rr * math.sin(a))
        glyph(rnd.choice(NOISE_CHARS), mat(rnd.choice(colors), kind='soft', rim=0.3), parent, p, size * rnd.uniform(0.7, 1.2),
              rot=(math.pi / 2 + rnd.uniform(-0.4, 0.4), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.3, 0.3)))


def sparks(parent, n, center, R, seed, col="#fff1a0"):
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(0, TAU)
        c = Vector(center) + Vector((R * math.cos(a), -0.2, R * math.sin(a) * 0.8))
        pts = [c]
        d = Vector((math.cos(a), 0, math.sin(a)))
        for k in range(3):
            c = c + d * 0.13 + Vector((rnd.uniform(-0.08, 0.08), 0, rnd.uniform(-0.08, 0.08)))
            pts.append(c)
        tube("spark", pts, [0.025, 0.012], glow(col, 2.5), parent, seg=4, sub=1, line=False)


def zigzag(parent, a, b, col, w=0.03, n=6, amp=0.12, seed=0):
    rnd = random.Random(seed)
    a, b = Vector(a), Vector(b)
    pts = []
    for i in range(n + 1):
        t = i / n
        p = a.lerp(b, t)
        if 0 < i < n:
            p = p + Vector((rnd.uniform(-amp, amp), 0, rnd.uniform(-amp, amp)))
        pts.append(p)
    tube("zz", pts, [w], glow(col, 2.6), parent, seg=4, sub=1, line=False)


# ------------------------------------------------------------------ creatures (unit scale, facing -Y, water z=0)
def garble_squid(st, b):
    c1, c2 = "#ff8fb0", "#ffd36a"
    mt = st.m(c1, pat=None if st.noise else 'stripes', color2=st.c(c2), P=dict(fv=3.2, thr=0.62, weave=False), rim=0.6)
    loft("mantle", [(0.35, 0.5, 0.48), (0.6, 0.72, 0.68), (1.1, 0.74, 0.7), (1.65, 0.55, 0.52), (2.05, 0.28, 0.27),
                    (2.25, 0.05, 0.05)], mt, b, seg=32, cap_top=True,
         folds=(lambda a, t: 1 + 0.05 * math.sin(7 * a + t * 9)) if st.noise else None)
    for s in (-1, 1):
        ellipsoid("fin", 0.42, st.m(c2 if not st.noise else c1), b, loc=(s * 0.55, 0.05, 1.75), scale=(1, 0.25, 0.7),
                  rot=(0, s * 0.5, 0))
    rainbow = ["#ff6a6a", "#ffb84a", "#ffe066", "#7fd957", "#4ad6c8", "#5a9ae8", "#9a7bff", "#ff8fd0"]
    for k in range(8):
        a = TAU * k / 8 + 0.2
        r0 = 0.42
        pts = []
        for j in range(7):
            t = j / 6
            rr = r0 + 0.75 * t
            ang = a + 0.5 * t * math.sin(st.ph + k)
            zc = 0.38 - 0.42 * t + 0.25 * math.sin(t * 5 + st.ph + k) * t
            pts.append(Vector((rr * math.cos(ang), rr * math.sin(ang) * 0.75, zc)))
        col = st.c(rainbow[k]) if not st.noise else st.c(c1, 0.78)
        tube(f"ten{k}", pts, [0.13, 0.09, 0.04], mat(col, kind='soft', rim=0.5), b, seg=10, sub=3)
        if st.noise:   # tentacles end in jumbled letters
            glyph("AZ#?k%7Q"[k], mat("#c46a3a", kind='soft', rim=0.4), b, pts[-1] + Vector((0, -0.05, 0.08)), 0.28)
    face(b, (0, -0.66, 0.95), 0.17, st, gap=1.3, iris="#4a2a6a")
    if st.noise:
        glyph_scatter(b, 14, (0, -0.62, 1.45), 0.55, 0.55, 0.26, st, 11, y=0.02)


def static_jelly(st, b, cipher=False):
    c1, c2 = ("#8fe8ff", "#ff9ad8") if not cipher else ("#ff9a6a", "#7a8aff")
    bz = 0.7 + 0.06 * math.sin(st.ph)
    pat = None
    bell_m = st.m(c1, rim=0.8, pat=('stripes' if cipher and not st.noise else None), color2=st.c(c2),
                  P=dict(fv=4.5, thr=0.55, weave=False))
    if cipher and not st.noise:   # rainbow bell
        rb = ["#ff6a6a", "#ffb84a", "#ffe066", "#7fd957", "#4ad6c8", "#5a9ae8", "#9a7bff"]
        for i, col in enumerate(rb):
            z0 = bz + 0.12 * i
            r0 = 0.9 * math.cos(math.asin(min(0.99, (z0 - bz) / 0.95)))
            r1 = 0.9 * math.cos(math.asin(min(0.99, (z0 + 0.12 - bz) / 0.95)))
            loft(f"band{i}", [(z0, r0, r0 * 0.9), (z0 + 0.125, max(0.05, r1), max(0.05, r1 * 0.9))],
                 mat(col, kind='soft', rim=0.6), b, seg=32, cap_top=(i == 6))
    else:
        blob("bell", 0.9, bell_m, b, loc=(0, 0, bz), scale=(1, 0.9, 0.95),
             deform=lambda p: Vector((p.x, p.y, max(p.z, -0.15) if p.z > -0.15 else -0.15 + (p.z + 0.15) * 0.1)))
    loft("frill", [(bz - 0.02, 0.9, 0.82), (bz - 0.18, 0.98, 0.9), (bz - 0.28, 0.86, 0.78)], st.m(c2, rim=0.6), b, seg=40,
         folds=lambda a, t: 1 + 0.12 * math.sin(10 * a + st.ph) * t)
    if not st.noise:
        ellipsoid("core", 0.42, glow(c2 if not cipher else "#fff2a0", 1.6), b, loc=(0, 0.1, bz + 0.3), line=False)
    for k in range(6):
        a = TAU * k / 6
        pts = [Vector((0.55 * math.cos(a), 0.45 * math.sin(a), bz - 0.25 - 0.22 * j)) +
               Vector((0.1 * math.sin(j * 1.4 + st.ph + k), 0, 0)) for j in range(5)]
        tube(f"t{k}", pts, [0.07, 0.03], st.m(c2 if k % 2 else c1, rim=0.5), b, seg=8, sub=3)
    face(b, (0, -0.84, bz + 0.38), 0.17, st, gap=1.4, iris="#2a5a8a", mouth_dz=-1.1)
    if cipher:
        # padlock hanging under the bell
        lk = pivot("lock", (0, -0.5, bz - 0.5), b)
        box("lbody", (0.42, 0.18, 0.34), st.m("#e8b04a", amt=0.55, metal=True), lk, bevel=0.05)
        ring_tube("shackle", (0, 0, 0.2), 0.14, 0.04, st.m("#c8c4d0", amt=0.55), lk, axis='y', seg=20, tseg=6)
        ellipsoid("khole", 0.05, mat("#1a1220", kind='flat'), lk, loc=(0, -0.1, 0.0), scale=(1, 0.3, 1.3), line=False)
        if st.noise:
            for i in range(3):    # chains wrapping the bell
                ring_tube(f"chain{i}", (0, 0, bz + 0.15 + 0.22 * i), 0.92 - 0.12 * i, 0.035,
                          mat("#5a5866", kind='soft', rim=0.5), b, axis='z', seg=36, tseg=5)
            glyph_scatter(b, 9, (0, -0.8, bz + 0.5), 0.75, 0.45, 0.22, st, 21)
    elif st.noise:
        for i in range(5):
            a = TAU * i / 5 + st.ph * 0.3
            zigzag(b, (0.6 * math.cos(a), -0.3, bz + 0.4 + 0.5 * math.sin(a)),
                   (1.25 * math.cos(a), -0.4, bz + 0.4 + 0.9 * math.sin(a)), "#fff1a0", seed=i + st.f * 7)
        glyph_scatter(b, 6, (0, -0.8, bz + 0.5), 0.7, 0.4, 0.2, st, 31)


def tide_whale(st, b):
    c1, c2 = "#7ab8f0", "#f4f8ff"
    if st.noise:
        c1 = "#6a7488"
    bz = 0.25 + 0.05 * math.sin(st.ph)
    def deform(p):
        bulge = 1.0
        if st.noise:
            bulge = 1 + 0.12 * math.sin(p.x * 5) * math.sin(p.y * 4 + 1) + 0.08 * math.sin(p.z * 6)
        return Vector((p.x * bulge, p.y * (1 + 0.15 * max(0, p.y)), p.z * (1.0 if p.z > 0 else 0.7) * bulge))
    blob("body", 1.0, st.m(c1, rim=0.6, pat='noise' if st.noise else None, P=dict(scale=6), var=0.15), b,
         loc=(0, 0.3, bz + 0.6), scale=(1.15, 1.9, 0.95), deform=deform)
    blob("belly", 0.95, st.m(c2, amt=0.6, rim=0.3), b, loc=(0, 0.2, bz + 0.35), scale=(1.05, 1.75, 0.6))
    # tail + flukes raised behind
    tube("tail", [Vector((0, 1.9, bz + 0.6)), Vector((0, 2.6, bz + 0.9)), Vector((0, 3.0, bz + 1.4 + 0.15 * math.sin(st.ph)))],
         [0.45, 0.28, 0.16], st.m(c1, rim=0.6), b, seg=14, sub=4)
    for s in (-1, 1):
        ellipsoid("fluke", 0.5, st.m(c1, rim=0.6), b, loc=(s * 0.45, 3.05, bz + 1.55 + 0.15 * math.sin(st.ph)),
                  scale=(1, 0.4, 0.22), rot=(0.4, s * 0.35, 0))
        ellipsoid("flip", 0.45, st.m(c1, rim=0.6), b, loc=(s * 1.05, -0.2, bz + 0.25), scale=(0.9, 0.45, 0.22),
                  rot=(0, s * 0.7, s * 0.4))
    face(b, (0, -1.62, bz + 0.85), 0.2, st, gap=1.9, iris="#2a3a6a", mouth_dz=-1.4)
    if st.noise:
        # overstuffed: envelopes and crates bursting out of seams on the back
        rnd = random.Random(5)
        for i in range(7):
            p = Vector((rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 1.4), bz + 1.35 + rnd.uniform(-0.05, 0.15)))
            box("env", (0.38, 0.05, 0.26), mat("#a89a84", kind='soft', rim=0.3), b, loc=p,
                rot=(rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), rnd.uniform(-1, 1)), bevel=0.01)
        for i in range(4):   # stitched seams
            z = bz + 0.6 + 0.15 * i
            tube("seam", [Vector((-0.9 + 0.1 * i, -1.0 + 0.6 * i, z + 0.55)), Vector((-0.3, -0.6 + 0.6 * i, z + 0.75)),
                          Vector((0.4, -0.7 + 0.6 * i, z + 0.7))], [0.03], mat("#c46a3a", kind='soft'), b, seg=5, sub=3)
        glyph_scatter(b, 10, (0, -1.4, bz + 1.0), 1.1, 0.6, 0.32, st, 41)
    else:
        for i, (x, y, r) in enumerate(((-0.35, 0.2, 0.42), (0.2, 0.0, 0.5), (0.55, 0.5, 0.38), (-0.1, 0.8, 0.45), (0.3, 1.2, 0.34))):
            ellipsoid("cloud", r, mat("#ffffff", kind='soft', rim=0.5), b, loc=(x, y, bz + 1.38 + r * 0.3), scale=(1, 1, 0.75))
        # water spout of sparkles
        for i in range(5):
            ellipsoid("spout", 0.09 - 0.01 * i, mat("#bfe8ff", kind='soft', rim=0.6), b,
                      loc=(0.1 * math.sin(i * 2 + st.ph), -0.6, bz + 1.6 + 0.22 * i))


def gull_body(st, b, c1, c2, beak="#ffb84a", hz=1.15):
    z = hz + 0.08 * math.sin(st.ph)
    ellipsoid("gb", 0.48, st.m(c1, rim=0.6), b, loc=(0, 0.05, z), scale=(0.85, 1.2, 0.8))
    ellipsoid("ghead", 0.36, st.m(c1, rim=0.6), b, loc=(0, -0.48, z + 0.38))
    ellipsoid("gtail", 0.25, st.m(c2, rim=0.5), b, loc=(0, 0.62, z + 0.05), scale=(0.9, 1.3, 0.35))
    up = 0.9 if st.f == 0 else -0.35
    for s in (-1, 1):
        w = pivot("wing", (s * 0.35, 0.05, z + 0.15), b, rot=(0, s * up, 0))
        blob("w", 0.55, st.m(c2, rim=0.6), w, loc=(s * 0.55, 0.0, 0), scale=(1.3, 0.6, 0.18))
        ellipsoid("wtip", 0.25, st.m("#3a3a4a", amt=0.3), w, loc=(s * 1.15, 0.1, 0), scale=(1, 0.6, 0.2))
    if st.noise:   # wide-open echo beak
        tube("bk1", [Vector((0, -0.75, z + 0.38)), Vector((0, -1.05, z + 0.5))], [0.12, 0.02], st.m(beak, amt=0.5), b, seg=8, sub=1)
        tube("bk2", [Vector((0, -0.75, z + 0.28)), Vector((0, -1.0, z + 0.12))], [0.11, 0.02], st.m(beak, amt=0.5), b, seg=8, sub=1)
    else:
        tube("bk", [Vector((0, -0.75, z + 0.34)), Vector((0, -1.0, z + 0.3))], [0.11, 0.03], mat(beak, kind='soft'), b, seg=8, sub=1)
    face(b, (0, -0.7, z + 0.5), 0.1, st, gap=1.6, iris="#2a2a3a", mouth=False)
    for s in (-1, 1):
        tube("leg", [Vector((s * 0.15, 0.1, z - 0.35)), Vector((s * 0.15, 0.15, z - 0.6))], [0.035], mat("#ffb84a", kind='soft'),
             b, seg=6, sub=1)
    return z


def echo_gulls(st, b):
    z = gull_body(st, b, "#f4f4f8", "#c8d2e0")
    if st.noise:
        for i in range(3):     # echo arcs in front of the beak
            r = 0.3 + 0.25 * i + 0.1 * st.f
            pts = [Vector((r * math.sin(a), -1.05 - r * math.cos(a) * 0.4, z + 0.3 + r * math.cos(a) * 0.9))
                   for a in [(-1.0 + 2.0 * j / 10) for j in range(11)]]
            pts = [Vector((p.x, -1.1 - 0.25 * i, p.z)) for p in pts]
            tube(f"arc{i}", pts, [0.035], glow(EYE_NOISE, 2.2), b, seg=5, sub=1, line=False)
        glyph_scatter(b, 4, (0, -0.6, z + 0.4), 0.6, 0.4, 0.2, st, 51)
    else:   # postman cap + satchel
        cyl("cap", 0.26, 0.24, 0.14, mat("#2a4a8a", kind='soft', rim=0.5), b, loc=(0, -0.5, z + 0.62))
        ellipsoid("visor", 0.2, mat("#1a2a5a", kind='soft'), b, loc=(0, -0.72, z + 0.63), scale=(1, 0.7, 0.15))
        box("bag", (0.3, 0.12, 0.24), mat("#c08048", kind='soft', rim=0.4), b, loc=(0.32, -0.12, z - 0.2), bevel=0.03)
        box("letter", (0.22, 0.03, 0.14), mat("#ffffff", kind='soft'), b, loc=(0.32, -0.2, z - 0.04), bevel=0.01)


def web_gull(st, b):
    z = gull_body(st, b, "#ffb0c8" if not st.noise else "#d8d8e0", "#4ad6c8", beak="#ffcf5a")
    # chest browser window
    box("win", (0.42, 0.05, 0.3), st.m("#f4f8ff", amt=0.5), b, loc=(0, -0.48, z - 0.05), bevel=0.02)
    box("winbar", (0.42, 0.06, 0.07), st.m("#5a9ae8", amt=0.6), b, loc=(0, -0.5, z + 0.08), bevel=0.01)
    for i in range(3):
        ellipsoid("dot", 0.022, mat("#ff6a6a" if i == 0 else "#ffe066" if i == 1 else "#7fd957", kind='flat'), b,
                  loc=(-0.15 + 0.06 * i, -0.54, z + 0.08), line=False)
    if st.noise:    # endless loading spinner above the head
        for k in range(8):
            a = TAU * k / 8 + st.ph * 0.5
            ellipsoid("ld", 0.05, glow(EYE_NOISE, 1.2 + 1.6 * (k / 8)), b, loc=(0.3 * math.cos(a), -0.5, z + 1.15 + 0.3 * math.sin(a)),
                      line=False)
        glyph("?", mat("#c46a3a", kind='soft'), b, (0, -0.56, z - 0.05), 0.24)
    else:
        ellipsoid("globe", 0.12, mat("#4ad6c8", kind='soft', rim=0.5, pat='patches', color2="#7fd957", P=dict(scale=8)), b,
                  loc=(0, -0.56, z - 0.06))


def lost_bottle(st, b):
    glass = "#5fd0c8" if not st.noise else "#4a5a50"
    tilt = 0.45 + 0.06 * math.sin(st.ph)
    bt = pivot("bt", (0, 0, 0.25), b, rot=(0, tilt, 0))
    gm = mat(glass if not st.noise else mixhex(glass, NOISE_DARK, 0.4), kind='soft', rim=0.9)
    loft("glass", [(-0.55, 0.0, 0.0), (-0.52, 0.32, 0.32), (-0.3, 0.42, 0.42), (0.45, 0.42, 0.42), (0.7, 0.3, 0.3),
                   (0.85, 0.15, 0.15), (1.15, 0.13, 0.13), (1.2, 0.16, 0.16)], gm, bt, rot=(0, 0, 0), seg=28, cap_top=True)
    if st.noise:
        for i in range(4):
            ellipsoid("fog", 0.2, mat("#3a3346", kind='soft', rim=0.1), bt, loc=(0.1 * i - 0.15, -0.1, -0.2 + 0.25 * i))
        # torn blank label
        lb = loft("label", [(-0.15, 0.435, 0.435), (0.25, 0.435, 0.435)], mat("#8a8070", kind='soft'), bt, seg=28,
                  arc=(math.pi * 0.95, math.pi * 1.75))
        for i in range(3):
            tube("crack", [Vector((0.3 - 0.1 * i, -0.4, 0.5 - 0.2 * i)), Vector((0.2, -0.43, 0.35 - 0.2 * i)),
                           Vector((0.35, -0.42, 0.2 - 0.2 * i))], [0.012], glow("#ff8a5a", 1.5), bt, seg=4, sub=1, line=False)
        glyph_scatter(b, 7, (0, -0.4, 0.8), 0.6, 0.45, 0.24, st, 61)
    else:
        cyl("cork", 0.12, 0.14, 0.2, mat("#c08048", kind='soft', pat='noise', P=dict(scale=30), var=0.2), bt, loc=(0, 0, 1.18))
        tube("scroll", [Vector((0, 0, -0.35)), Vector((0, 0, 0.35))], [0.18], mat("#fff4d8", kind='soft', rim=0.4), bt, seg=14, sub=1)
        ring_tube("ribbon", (0, 0, 0.0), 0.19, 0.03, mat("#ff6a6a", kind='soft'), bt, axis='z', seg=20, tseg=5)
        # address tag on a string
        tube("string", [Vector((0.15, -0.1, 0.95)), Vector((0.35, -0.25, 0.75)), Vector((0.45, -0.3, 0.55))], [0.012],
             mat("#c9a870", kind='soft'), bt, seg=5, sub=3, line=False)
        box("tag", (0.22, 0.03, 0.14), mat("#ffd36a", kind='soft', rim=0.4), bt, loc=(0.48, -0.32, 0.47), rot=(0, 0.3, 0),
            bevel=0.01)
    face(bt, (0, -0.42, 0.05), 0.13, st, gap=1.4, iris="#2a4a3a", mouth_dz=-1.3)


def crab_base(st, b, c1, c2, body_scale=(1.0, 0.75, 0.55), claw_c=None, legs=True):
    bz = 0.45 + 0.04 * math.sin(st.ph)
    blob("cbody", 0.6, st.m(c1, rim=0.6), b, loc=(0, 0, bz), scale=body_scale)
    claw_c = claw_c or c1
    for s in (-1, 1):
        arm = [Vector((s * 0.45, -0.35, bz)), Vector((s * 0.75, -0.65, bz + 0.2)), Vector((s * 0.65, -0.95, bz + 0.45))]
        tube("arm", arm, [0.09, 0.07], st.m(claw_c, rim=0.5), b, seg=10, sub=3)
        op = 0.25 if st.f == 0 else 0.5
        cl = pivot("claw", arm[-1], b, rot=(0, 0, s * 0.2))
        ellipsoid("cl1", 0.2, st.m(claw_c, rim=0.6), cl, loc=(0, -0.12, 0.08), scale=(0.8, 1.3, 0.7), rot=(op, 0, 0))
        ellipsoid("cl2", 0.14, st.m(claw_c, rim=0.6), cl, loc=(0, -0.12, -0.08), scale=(0.7, 1.2, 0.5), rot=(-op, 0, 0))
        if legs:
            for k in range(3):
                y = -0.1 + 0.25 * k
                lift = 0.1 * math.sin(st.ph + k * 2 + (s > 0))
                tube("leg", [Vector((s * 0.5, y, bz - 0.05)), Vector((s * 0.85, y + 0.05, bz + 0.12 + lift)),
                             Vector((s * 1.0, y + 0.1, 0.02))], [0.06, 0.03], st.m(c2, rim=0.5), b, seg=8, sub=3)
    return bz


def paper_crab(st, b):
    if st.noise:
        bz = 0.5
        rnd = random.Random(3)
        def crumple(p):
            k = 1 + 0.16 * math.sin(p.x * 9 + 1) * math.sin(p.y * 7) + 0.1 * math.sin(p.z * 11 + p.x * 3)
            return Vector((p.x * k, p.y * k, p.z * k))
        blob("ball", 0.6, mat(mixhex("#e8e0c8", NOISE_DARK, 0.55), kind='soft', rim=0.5, pat='stripes', color2="#4a4258",
                              P=dict(fv=14, thr=0.9, weave=False)), b, loc=(0, 0, bz), scale=(1.1, 0.9, 0.85), deform=crumple,
             seg=24, rings=16)
        for s in (-1, 1):
            arm = [Vector((s * 0.5, -0.3, bz)), Vector((s * 0.8, -0.6, bz + 0.25)), Vector((s * 0.7, -0.9, bz + 0.45))]
            tube("arm", arm, [0.08, 0.06], mat("#6a6270", kind='soft'), b, seg=6, sub=1)
            blob("claw", 0.22, mat(mixhex("#e8e0c8", NOISE_DARK, 0.55), kind='soft', rim=0.5), b, loc=arm[-1] + Vector((0, -0.1, 0.05)),
                 scale=(0.9, 1.2, 0.8), deform=crumple, seg=12, rings=8)
            for k in range(3):
                y = -0.1 + 0.25 * k
                tube("leg", [Vector((s * 0.5, y, bz - 0.1)), Vector((s * 0.85, y, bz + 0.1 + 0.1 * math.sin(st.ph + k))),
                             Vector((s * 1.0, y + 0.1, 0.02))], [0.05, 0.025], mat("#6a6270", kind='soft'), b, seg=6, sub=1)
        for i in range(5):    # ink smudges
            ellipsoid("ink", 0.12, mat("#1e1830", kind='flat', rim=0), b,
                      loc=(rnd.uniform(-0.4, 0.4), -0.45, bz + rnd.uniform(-0.1, 0.4)), scale=(1, 0.2, 0.6), line=False)
        face(b, (0, -0.55, bz + 0.15), 0.13, st, gap=1.5, mouth_dz=-1.4)
        glyph_scatter(b, 8, (0, -0.5, bz + 0.5), 0.7, 0.4, 0.22, st, 71)
    else:
        bz = crab_base(st, b, "#ff9a5a", "#e8784a")
        # folder shell with tabs
        box("folder", (1.05, 0.75, 0.12), mat("#f2cf7a", kind='soft', rim=0.5), b, loc=(0, 0.05, bz + 0.35), rot=(-0.25, 0, 0), bevel=0.03)
        for i, col in enumerate(("#ff6a6a", "#4ad6c8", "#9a7bff")):
            box("tab", (0.2, 0.08, 0.12), mat(col, kind='soft'), b, loc=(-0.3 + 0.3 * i, 0.32, bz + 0.52), rot=(-0.25, 0, 0), bevel=0.02)
        box("page", (0.9, 0.05, 0.4), mat("#ffffff", kind='soft'), b, loc=(0, 0.25, bz + 0.6), rot=(-0.25, 0, 0), bevel=0.01)
        face(b, (0, -0.45, bz + 0.12), 0.13, st, gap=1.5, mouth_dz=-1.3)


def cable_eel(st, b, cz=0.0):
    c1, c2 = ("#ffd34a", "#3a8fd0") if not st.noise else ("#4a4a58", "#2a2a36")
    sw = 0.15 * math.sin(st.ph)
    pts = [Vector((0.3, 1.2, -0.15)), Vector((0.5, 0.6, 0.35)), Vector((0.2, 0.1, 0.9)), Vector((-0.15, -0.15, 1.45 + sw)),
           Vector((-0.1, -0.45, 1.85 + sw))]
    tube("cable", pts, [0.2, 0.24, 0.24, 0.22, 0.2], mat(c1, kind='soft', rim=0.6, pat='stripes', color2=c2,
                                                       P=dict(fv=6, thr=0.7, weave=False)), b, seg=16, sub=6)
    tube("cable2", [Vector((-0.4, 1.0, -0.1)), Vector((-0.6, 1.5, 0.25)), Vector((-0.75, 2.0, -0.1))], [0.18, 0.12],
         mat(c1, kind='soft', rim=0.6), b, seg=12, sub=4)
    hp = pivot("plug", pts[-1], b, rot=(0.25, 0, 0))
    box("head", (0.5, 0.42, 0.55), mat("#d8dce8" if not st.noise else "#5a5866", kind='soft', rim=0.7), hp, loc=(0, -0.1, 0.25), bevel=0.08)
    box("clip", (0.18, 0.12, 0.25), mat("#b8c0d0" if not st.noise else "#4a4856", kind='soft'), hp, loc=(0, 0.15, 0.35), bevel=0.03)
    if st.noise:
        # torn top: frayed copper wires + sparks
        rnd = random.Random(9 + st.f)
        cols = ["#d9823a", "#3a8a5a", "#3a5ad0", "#d0d0d0"]
        for i in range(8):
            a = TAU * i / 8
            base = Vector((0.12 * math.cos(a), -0.1 + 0.1 * math.sin(a), 0.5))
            tip = base + Vector((0.35 * math.cos(a) * rnd.uniform(0.7, 1.2), -0.1, 0.25 + rnd.uniform(0, 0.3)))
            tube("wire", [base, base.lerp(tip, 0.5) + Vector((0, 0, 0.08)), tip], [0.03, 0.02], mat(cols[i % 4], kind='soft'), hp,
                 seg=5, sub=2)
        sparks(hp, 6, (0, -0.1, 0.75), 0.4, 3 + st.f)
        face(hp, (0, -0.33, 0.25), 0.1, st, gap=1.3, mouth_dz=-1.4)
        glyph_scatter(b, 6, (0, -0.5, 1.3), 0.6, 0.5, 0.22, st, 81)
    else:
        for i in range(4):     # gold contacts on top
            box("pin", (0.06, 0.1, 0.05), mat("#e8b04a", metal=True), hp, loc=(-0.12 + 0.08 * i, -0.2, 0.52))
        face(hp, (0, -0.33, 0.25), 0.1, st, gap=1.3, mouth_dz=-1.4)
        zigzag(b, (0.4, -0.3, 1.5), (0.8, -0.3, 2.0), "#fff6a0", seed=2)


def frame_crab(st, b):
    bz = crab_base(st, b, "#ff7a6a" if not st.noise else "#8a6a6a", "#ff9a7a", claw_c="#ff6a5a")
    if st.noise:
        # crooked broken frame with a wrong address tag
        fr = pivot("frame", (0, 0.05, bz + 0.45), b, rot=(-0.3, 0.25, 0.1))
        fm = mat("#5a4a3a", kind='soft', rim=0.4)
        for (sx, sz, lx, lz) in ((1.0, 0.1, 0, 0.35), (0.8, 0.1, 0.05, -0.35), (0.1, 0.7, -0.5, 0), (0.1, 0.5, 0.5, -0.05)):
            box("fb", (sx, 0.1, sz), fm, fr, loc=(lx, 0, lz), bevel=0.02)
        glyph("??", mat("#c46a3a", kind='soft'), fr, (0, -0.06, 0), 0.3)
        glyph_scatter(b, 7, (0, -0.4, bz + 0.6), 0.7, 0.4, 0.22, st, 91)
    else:
        for i, (x, y, r, col) in enumerate(((-0.25, 0.1, 0.32, "#ffd0e0"), (0.25, 0.05, 0.3, "#fff0c8"), (0.0, 0.35, 0.28, "#c8f0ff"))):
            sh = pivot("shell", (x, y, bz + 0.28), b, rot=(-0.5, 0, 0))
            loft("sc", [(0, 0.0, 0.0), (0.02, r, r * 0.9)], mat(col, kind='soft', rim=0.5, pat='vstripes', color2=mixhex(col, "#ff8a6a", 0.4),
                                                              P=dict(nu=10, thr=0.6)), sh, seg=24, arc=(0, math.pi), cap_bot=False)
    face(b, (0, -0.45, bz + 0.12), 0.13, st, gap=1.5, mouth_dz=-1.3)


def ip_hermit(st, b):
    bz = 0.35
    # house shell on the back
    hs = pivot("house", (0, 0.25, bz + 0.15), b, rot=((0.0, 0.15, 0.12) if st.noise else (0, 0, 0)))
    wallc = "#f2cf7a" if not st.noise else "#5a5060"
    box("walls", (0.85, 0.75, 0.6), mat(wallc, kind='soft', rim=0.5, pat=None if st.noise else 'patches',
                                       color2="#7fd957", P=dict(scale=3, thr=0.55)), hs, loc=(0, 0, 0.3), bevel=0.05)
    roof = mat("#e85a4a" if not st.noise else "#3a2a36", kind='soft', rim=0.5)
    for s in (-1, 1):
        box("roof", (0.62, 0.9, 0.08), roof, hs, loc=(s * 0.24, 0, 0.75), rot=(0, s * 0.7, 0), bevel=0.02)
    box("door", (0.2, 0.04, 0.3), mat("#8a5a36", kind='soft'), hs, loc=(0.18, -0.39, 0.18), bevel=0.02)
    box("plate", (0.24, 0.03, 0.14), mat("#f4f8ff" if not st.noise else "#8a8090", kind='soft'), hs, loc=(-0.2, -0.39, 0.45), bevel=0.01)
    glyph("7" if not st.noise else "?", mat("#2a4a8a" if not st.noise else "#c46a3a", kind='soft'), hs, (-0.2, -0.42, 0.45), 0.13)
    if not st.noise:
        tube("pole", [Vector((0.3, 0.1, 0.8)), Vector((0.3, 0.1, 1.25))], [0.02], mat("#8a5a36"), hs, seg=6, sub=1)
        box("flag", (0.25, 0.02, 0.15), mat("#4ad6c8", kind='soft'), hs, loc=(0.43, 0.1, 1.17))
    else:
        box("hole", (0.25, 0.05, 0.2), mat("#120c18", kind='flat'), hs, loc=(0.2, 0.0, 0.85), rot=(0, 0.7, 0))
        glyph_scatter(b, 7, (0, -0.4, 0.8), 0.6, 0.5, 0.22, st, 101)
    # crab bits poking out
    blob("hbody", 0.35, st.m("#ff9a6a", rim=0.6), b, loc=(0, -0.3, bz + 0.1), scale=(1, 0.8, 0.8))
    for s in (-1, 1):
        ellipsoid("claw", 0.17, st.m("#ff7a5a", rim=0.6), b, loc=(s * 0.25, -0.62, bz - 0.05 + 0.05 * math.sin(st.ph + s)),
                  scale=(0.9, 1.2, 0.8))
        for k in range(2):
            tube("leg", [Vector((s * 0.25, -0.2 + 0.2 * k, bz)), Vector((s * 0.55, -0.15 + 0.2 * k, bz + 0.1)),
                         Vector((s * 0.65, -0.1 + 0.2 * k, 0.02))], [0.05, 0.025], st.m("#ff9a6a"), b, seg=6, sub=3)
        tube("stalk", [Vector((s * 0.12, -0.45, bz + 0.25)), Vector((s * 0.16, -0.5, bz + 0.5))], [0.035], st.m("#ff9a6a"), b,
             seg=6, sub=1)
    for s in (-1, 1):
        if st.noise:
            eye_noise(b, (s * 0.16, -0.55, bz + 0.58), 0.09, side=s)
        else:
            eye_friend(b, (s * 0.16, -0.55, bz + 0.58), 0.1, iris="#2a2a3a")


def port_urchin(st, b):
    c1, c2 = ("#b88aff", "#ffd36a") if not st.noise else ("#3e3050", "#5a4a5a")
    bz = 0.6 + 0.04 * math.sin(st.ph)
    ellipsoid("ub", 0.6, mat(c1, kind='soft', rim=0.6, pat='dots', color2=mixhex(c1, "#ffffff", 0.35), P=dict(nu=10, fv=6, rad=0.2)),
              b, loc=(0, 0, bz), scale=(1, 1, 0.92))
    rnd = random.Random(4)
    doors = [(0.6, 0.55), (2.2, 0.2), (3.5, 0.7), (4.8, 0.1), (1.4, -0.2)]
    door_cols = ["#ff6a6a", "#4ad6c8", "#ffe066", "#7fd957", "#5a9ae8"]
    nums = ["80", "53", "22", "21", "25"]
    k = 0
    for i in range(34):
        a = rnd.uniform(0, TAU)
        e = rnd.uniform(-0.5, 1.2)
        d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        base = Vector((0, 0, bz)) + d * 0.55
        L = (0.38 if not st.noise else 0.5) * rnd.uniform(0.8, 1.2)
        tip = base + d * L
        if st.noise:
            tip = tip + Vector((rnd.uniform(-0.1, 0.1), 0, rnd.uniform(-0.1, 0.1)))
        tube("sp", [base, tip], [0.05, 0.008 if st.noise else 0.035], mat(c2, kind='soft', rim=0.5), b, seg=6, sub=1)
        if not st.noise:
            ellipsoid("sptip", 0.045, mat("#fff6d0", kind='soft'), b, loc=tip)
    for j, (a, e) in enumerate(doors):
        d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        if d.y > 0.3:
            continue
        p = Vector((0, 0, bz)) + d * 0.6
        dr = pivot("door", p, b, rot=(0, 0, math.atan2(d.y, d.x) + math.pi / 2))
        if st.noise:
            dr.rotation_euler = (0.3, 0.4, dr.rotation_euler[2] + 0.6)
        box("d", (0.2, 0.05, 0.27), mat(door_cols[j] if not st.noise else "#5a4a4a", kind='soft', rim=0.5), dr, bevel=0.03)
        ellipsoid("knob", 0.025, mat("#e8b04a", metal=True), dr, loc=(0.06, -0.04, 0))
        if not st.noise:
            glyph(nums[j], mat("#2a2236", kind='flat'), dr, (0, -0.035, 0.07), 0.08, extrude=0.005)
    face(b, (0, -0.56, bz + 0.05), 0.13, st, gap=1.4, mouth_dz=-1.3)
    if st.noise:
        glyph_scatter(b, 7, (0, -0.6, bz + 0.3), 0.7, 0.5, 0.22, st, 111)
        glyph("?", mat("#c46a3a", kind='soft'), b, (0.55, -0.4, bz + 0.85), 0.3)


def session_snail(st, b):
    c1, c2 = ("#ffb07a", "#7a5ae0") if not st.noise else ("#5a5060", "#3a2a40")
    bz = 0.0
    sl = loft("foot", [(-0.0, 0.0, 0.0), (0.02, 0.32, 0.3), (0.18, 0.34, 0.32), (0.3, 0.2, 0.2)], st.m("#ffd0a8", rim=0.5), b,
              rot=(-math.pi / 2, 0, 0), loc=(0, 0.6, 0.15), seg=20, cap_top=True)
    sl.scale = (1.0, 1.0, 4.2)
    # head and eyestalks at the front
    ellipsoid("head", 0.3, st.m("#ffd0a8", rim=0.6), b, loc=(0, -0.65, 0.35), scale=(1, 1, 1.1))
    # shell: spiral coil
    shell_m = mat(c1 if not st.noise else c1, kind='soft', rim=0.6, pat='spiral', color2=c2, P=dict(nu=3, fv=6, thr=0.55))
    pts, rad = [], []
    for i in range(60):
        t = i / 59
        a = 2.4 * TAU * t
        r = 0.55 * (1 - t) ** 0.9
        pts.append(Vector((0.0, 0.25 + r * math.cos(a), 0.68 + r * math.sin(a))))
        rad.append(0.38 * (1 - t) ** 0.85 + 0.03)
    if st.noise:   # shell cracked in half: the two halves pulled apart, a cut cord dangling
        sh1 = pivot("h1", (0, 0, 0), b, rot=(0, 0.0, 0.0))
        sh2 = pivot("h2", (0.0, 0.0, 0.0), b)
        sh1.location = (-0.12, 0, 0)
        sh2.location = (0.12, 0, 0.05)
        sh2.rotation_euler = (0, 0.25, 0)
        for hp, s in ((sh1, -1), (sh2, 1)):
            o = tube("shell", pts, rad, shell_m, hp, seg=16, sub=1)
            # keep one half: squash x
            o.scale = (0.5, 1, 1)
            o.location = (s * 0.12, 0, 0)
        cord = [Vector((0.2, 0.25 + 0.1 * math.cos(t * 9), 0.6 - t * 0.5)) + Vector((0.08 * math.sin(t * 20), 0, 0)) for t in
                [i / 20 for i in range(21)]]
        tube("cord", cord, [0.03], mat("#2a2a36", kind='soft'), b, seg=6, sub=1)
        sparks(b, 3, (0.2, 0.0, 0.1), 0.15, 5 + st.f, col="#ff8a4a")
        glyph_scatter(b, 6, (0, -0.4, 0.9), 0.6, 0.4, 0.22, st, 121)
    else:
        tube("shell", pts, rad, shell_m, b, seg=16, sub=1)
        # a little book/page on the shell side
        box("page", (0.04, 0.32, 0.24), mat("#fff4d8", kind='soft'), b, loc=(-0.42, 0.25, 0.68), rot=(0, 0, 0.1), bevel=0.01)
    for s in (-1, 1):
        tube("stalk", [Vector((s * 0.1, -0.7, 0.55)), Vector((s * 0.18, -0.78, 0.85 + 0.04 * math.sin(st.ph + s)))], [0.035],
             st.m("#ffd0a8"), b, seg=6, sub=1)
        if st.noise:
            eye_noise(b, (s * 0.18, -0.82, 0.92), 0.09, side=s)
        else:
            eye_friend(b, (s * 0.18, -0.82, 0.92), 0.1, iris="#3a2a5a")
    if not st.noise:
        face(b, (0, -0.9, 0.35), 0.1, st, gap=0.0, mouth_dz=-0.4) if False else None
        w = 0.08
        tube("smile", [Vector((-w, -0.93, 0.33)), Vector((0, -0.96, 0.29)), Vector((w, -0.93, 0.33))], [0.015],
             mat("#5a2a30", kind='flat'), b, seg=5, sub=3, line=False)


def raw_pearl(st, b):
    bz = 0.25
    if st.noise:
        # bare dull pearl shivering on a broken empty shell
        for s in (-1, 1):
            sh = pivot("half", (s * 0.35, 0.1, bz - 0.1), b, rot=(0, s * 0.9, 0.2 * s))
            loft("valve", [(0, 0.0, 0.0), (0.05, 0.45, 0.35)], mat("#4a4252", kind='soft', rim=0.4, pat='vstripes', color2="#3a3242",
                                                                 P=dict(nu=12, thr=0.6)), sh, seg=20, arc=(0, math.pi))
        ellipsoid("pearl", 0.42, mat("#8a8496", kind='soft', rim=0.6), b, loc=(0.03 * (st.f * 2 - 1), -0.05, bz + 0.38))
        for i in range(3):
            tube("crack", [Vector((-0.1 + 0.1 * i, -0.4, bz + 0.6)), Vector((0.0 + 0.1 * i, -0.42, bz + 0.45))], [0.01],
                 mat("#2a2236", kind='flat'), b, seg=4, sub=1, line=False)
        face(b, (0, -0.38, bz + 0.42), 0.1, st, gap=1.4, mouth_dz=-1.4)
        glyph_scatter(b, 8, (0, -0.4, bz + 0.5), 0.6, 0.45, 0.22, st, 131)
    else:
        hinge = pivot("hinge", (0, 0.35, bz), b)
        loft("lower", [(0, 0.0, 0.0), (0.12, 0.6, 0.5)], mat("#ff9ad8", kind='soft', rim=0.5, pat='vstripes', color2="#ffd0ec",
                                                          P=dict(nu=14, thr=0.55)), b, loc=(0, 0, bz - 0.05), seg=28,
             rot=(math.pi, 0, 0))
        up = pivot("upper", (0, 0.3, bz), b, rot=(-0.95 - 0.1 * st.f, 0, 0))
        loft("top", [(0, 0.0, 0.0), (0.12, 0.6, 0.5)], mat("#ff9ad8", kind='soft', rim=0.5, pat='vstripes', color2="#ffd0ec",
                                                        P=dict(nu=14, thr=0.55)), up, loc=(0, -0.3, 0.0), seg=28)
        ellipsoid("pearl", 0.36, mat("#ffd36a", metal=True, rim=0.8), b, loc=(0, -0.05, bz + 0.3))
        ellipsoid("sheen", 0.1, glow("#ffffff", 1.2), b, loc=(-0.12, -0.3, bz + 0.48), line=False)
        face(b, (0, -0.33, bz + 0.33), 0.09, st, gap=1.4, mouth_dz=-1.4)


def segment_barnacle(st, b):
    c1, c2 = ("#4ad6c8", "#ffffff") if not st.noise else ("#4a4a5a", "#3a3442")
    bz = 0.3
    loft("cone", [(0, 0.5, 0.5), (0.45, 0.42, 0.42), (0.8, 0.25, 0.25), (0.85, 0.18, 0.18)], mat(c1, kind='soft', rim=0.6,
         pat='vstripes', color2=c2, P=dict(nu=8, thr=0.65)), b, loc=(0, 0, bz), seg=24, cap_top=True,
         folds=lambda a, t: 1 + 0.06 * math.sin(8 * a))
    if not st.noise:   # wave crest on top
        for i in range(5):
            a = -0.6 + 0.3 * i
            ellipsoid("crest", 0.12, mat("#ffffff", kind='soft'), b, loc=(0.18 * math.sin(a), 0.1, bz + 0.92 + 0.08 * math.cos(a * 2)))
    # two port tags on poles (source / destination)
    for s, num in ((-1, "80" if not st.noise else "?"), (1, "53" if not st.noise else "#")):
        tube("pole", [Vector((s * 0.15, 0.0, bz + 0.85)), Vector((s * 0.3, 0.0, bz + 1.3))], [0.02], mat("#8a5a36"), b, seg=5, sub=1)
        box("tag", (0.32, 0.04, 0.2), mat("#ffd36a" if not st.noise else "#6a5a4a", kind='soft', rim=0.4), b,
            loc=(s * 0.33, -0.02, bz + 1.38), bevel=0.02)
        glyph(num, mat("#2a2236", kind='flat'), b, (s * 0.33, -0.05, bz + 1.38), 0.13, extrude=0.008)
    for k in range(6):   # running legs
        a = TAU * k / 6
        lift = 0.12 * math.sin(st.ph + k * 2)
        tube("leg", [Vector((0.4 * math.cos(a), 0.4 * math.sin(a), bz + 0.1)), Vector((0.7 * math.cos(a), 0.7 * math.sin(a), bz + 0.15 + lift)),
                     Vector((0.85 * math.cos(a), 0.85 * math.sin(a), 0.02))], [0.05, 0.025], mat("#ffb07a" if not st.noise else "#5a4a50",
                     kind='soft'), b, seg=6, sub=3)
    face(b, (0, -0.47, bz + 0.4), 0.12, st, gap=1.4, mouth_dz=-1.3)
    if st.noise:
        glyph_scatter(b, 7, (0, -0.5, bz + 0.8), 0.6, 0.45, 0.22, st, 141)


def packet_ray(st, b):
    c1, c2 = ("#3a4ad0", "#ffe066") if not st.noise else ("#3a3448", "#5a4a5a")
    bz = 0.35
    flap = 0.35 if st.f == 0 else -0.25
    def wing(p):
        x = p.x
        return Vector((p.x, p.y, p.z + flap * abs(x) ** 1.6 * 0.6))
    blob("ray", 1.0, mat(c1, kind='soft', rim=0.6, pat=None if st.noise else 'dots', color2=c2, P=dict(nu=14, fv=8, rad=0.12)),
         b, loc=(0, 0, bz), scale=(1.4, 0.95, 0.18),
         deform=lambda p: wing(Vector((p.x * (1 - 0.35 * max(0, p.y)), p.y * (1 - 0.3 * abs(p.x)), p.z))))
    tube("tail", [Vector((0, 0.8, bz)), Vector((0, 1.5, bz + 0.1)), Vector((0.1, 2.0, bz + 0.25))], [0.08, 0.02], mat(c1, kind='soft'),
         b, seg=8, sub=4)
    for s in (-1, 1):
        ellipsoid("horn", 0.13, mat(c1, kind='soft'), b, loc=(s * 0.25, -0.9, bz + 0.05), scale=(0.6, 1.2, 0.5))
    # envelope with an IP stamp on its back
    env = pivot("env", (0, 0.05, bz + 0.2), b, rot=(-0.2, 0, 0.1))
    box("e", (0.7, 0.5, 0.06), mat("#fff4d8" if not st.noise else "#8a8070", kind='soft', rim=0.4), env, bevel=0.02)
    tube("flap", [Vector((-0.33, -0.24, 0.035)), Vector((0, 0.0, 0.04)), Vector((0.33, -0.24, 0.035))], [0.012],
         mat("#c8a070", kind='flat'), env, seg=4, sub=1, line=False)
    box("stamp", (0.18, 0.18, 0.02), mat("#ff6a6a" if not st.noise else "#5a3a3a", kind='soft'), env, loc=(0.2, 0.12, 0.04))
    glyph("IP" if not st.noise else "I?", mat("#2a4a8a" if not st.noise else "#c46a3a", kind='flat'), env, (-0.12, 0.08, 0.04),
          0.14, rot=(0, 0, 0), extrude=0.005)
    if st.noise:
        box("tear", (0.2, 0.3, 0.07), mat("#120c18", kind='flat'), env, loc=(-0.25, -0.1, 0.0), rot=(0, 0, 0.5))
        glyph_scatter(b, 8, (0, -0.7, bz + 0.4), 0.8, 0.3, 0.22, st, 151)
    else:
        for i in range(5):
            a = TAU * i / 5
            glyph("*", mat("#ffe066", kind='soft'), b, (0.9 * math.cos(a) * 0.9, -0.2, bz + 0.12 + 0.05 * math.sin(a)), 0.16)
    face(b, (0, -0.8, bz + 0.1), 0.11, st, gap=1.6, mouth_dz=-1.0)


def frame_turtle(st, b):
    c1, c2 = ("#6ad08a", "#ffd36a") if not st.noise else ("#4a5048", "#3a3a40")
    bz = 0.25 + 0.04 * math.sin(st.ph)
    shell = pivot("sh", (0, 0.1, bz + 0.2), b)
    blob("shell", 0.8, mat(c1, kind='soft', rim=0.6, pat='patches' if not st.noise else 'noise', color2=mixhex(c1, "#2a7a5a", 0.4),
                           P=dict(scale=3.5, thr=0.5)), shell, scale=(1.0, 1.2, 0.6),
         deform=lambda p: Vector((p.x, p.y, max(p.z, -0.2))))
    # header band (front) + trailer band (back): coloured frame bands
    ring_tube("header", (0, -0.55, 0.08), 0.7, 0.07, mat("#ff8a4a" if not st.noise else "#5a3a3a", kind='soft', rim=0.5), shell, axis='y',
              seg=28, tseg=6)
    ring_tube("trailer", (0, 0.75, 0.05), 0.55, 0.07, mat("#4ad6c8" if not st.noise else "#3a4a4a", kind='soft', rim=0.5), shell,
              axis='y', seg=28, tseg=6)
    ring_tube("rim", (0, 0, -0.08), 0.82, 0.06, mat(c2, kind='soft', rim=0.5), shell, axis='z', seg=36, tseg=6)
    if st.noise:
        for i in range(4):
            tube("crack", [Vector((-0.3 + 0.2 * i, -0.3, 0.45)), Vector((-0.2 + 0.2 * i, 0.0, 0.5)), Vector((-0.3 + 0.2 * i, 0.3, 0.45))],
                 [0.02], glow("#ff7a3a", 1.6), shell, seg=4, sub=1, line=False)
        glyph_scatter(b, 8, (0, -0.6, bz + 0.8), 0.7, 0.45, 0.24, st, 161)
    skin = "#a8e070" if not st.noise else "#5a6050"
    ellipsoid("head", 0.32, mat(skin, kind='soft', rim=0.6), b, loc=(0, -0.95, bz + 0.25 + 0.05 * math.sin(st.ph)), scale=(1, 1.1, 0.9))
    for s in (-1, 1):
        for fy in (-0.45, 0.6):
            ellipsoid("flip", 0.25, mat(skin, kind='soft', rim=0.5), b, loc=(s * 0.8, fy, bz - 0.05), scale=(1.3, 0.6, 0.3),
                      rot=(0, 0, s * (0.4 + 0.25 * math.sin(st.ph + fy))))
    face(b, (0, -1.22, bz + 0.33), 0.1, st, gap=1.4, mouth_dz=-1.3)


def bit_swarm(st, b):
    rnd = random.Random(12)
    cols = ["#fff06a", "#6ae8ff", "#ffffff"] if not st.noise else ["#8a3a3a", "#5a3a4a", "#6a4a3a"]
    for i in range(9):
        a = TAU * i / 9 + 0.3 * st.f
        r = 0.55 * (0.4 + 0.6 * ((i * 7) % 5) / 4)
        p = Vector((r * math.cos(a), r * math.sin(a) * 0.6, 0.55 + 0.3 * math.sin(a * 2 + st.ph) + 0.1 * (i % 3)))
        ch = "01"[i % 2]
        col = cols[i % 3]
        m = glow(col, 1.4) if not st.noise else mat(col, kind='soft', rim=0.5)
        fish = pivot("fish", p, b, rot=(0, 0, rnd.uniform(-0.3, 0.3)))
        glyph(ch, m, fish, (0, 0, 0), 0.42, extrude=0.06)
        # little tail fin + eye
        mesh_obj("tail", [Vector((0.12, 0.0, 0.0)), Vector((0.28, 0.0, 0.1)), Vector((0.28, 0.0, -0.1))], [(0, 1, 2)],
                 m, fish, smooth=False, recalc=False, line=False)
        if st.noise:
            ellipsoid("e", 0.035, glow(EYE_NOISE, 3.0), fish, loc=(-0.05, -0.06, 0.06), line=False)
        else:
            ellipsoid("e", 0.04, mat("#1a1220", kind='flat'), fish, loc=(-0.05, -0.07, 0.06), line=False)
            ellipsoid("eh", 0.014, glow("#ffffff", 1), fish, loc=(-0.06, -0.1, 0.075), line=False)
    if not st.noise:
        ellipsoid("swarmglow", 0.8, glow("#fff6a0", 0.8, alpha=0.25, soft=True), b, loc=(0, 0, 0.6), line=False)


BUILDERS = dict(garble_squid=garble_squid, static_jelly=static_jelly, tide_whale=tide_whale, echo_gulls=echo_gulls,
                lost_bottle=lost_bottle, paper_crab=paper_crab, cable_eel=cable_eel, frame_crab=frame_crab,
                ip_hermit=ip_hermit, port_urchin=port_urchin, session_snail=session_snail,
                cipher_jelly=lambda st, b: static_jelly(st, b, cipher=True), web_gull=web_gull, raw_pearl=raw_pearl,
                segment_barnacle=segment_barnacle, packet_ray=packet_ray, frame_turtle=frame_turtle, bit_swarm=bit_swarm)
# visual radius of each model in its own units (so radius/56 maps the hit circle)
MODEL_R = dict(garble_squid=1.15, static_jelly=1.0, tide_whale=1.9, echo_gulls=1.1, lost_bottle=0.95, paper_crab=1.0,
               cable_eel=1.1, frame_crab=1.0, ip_hermit=0.8, port_urchin=1.05, session_snail=0.9, cipher_jelly=1.0,
               web_gull=1.1, raw_pearl=0.7, segment_barnacle=0.9, packet_ray=1.3, frame_turtle=1.1, bit_swarm=0.75)


def render_creature(job, cid, radius):
    k = (radius / 56.0) / MODEL_R[cid]
    size = int(max(96, radius * 4.4) // 8 * 8)
    for state in ('noise', 'friend'):
        for f in (0, 1):
            job.scene('day', samples=20)
            STATE['line_t'] = 0.011
            st = St(state, f)
            root = pivot("root", rot=(0, 0, FACE_ROT))
            root.scale = (k, k, k)
            body = pivot("body", parent=root)
            BUILDERS[cid](st, body)
            nm = f"{cid}_{state}_{f}"
            extra = dict(radiusPx=radius, facing="left")
            if state == 'noise':
                extra['glitch'] = [hash(cid) % 1000, f]
            job.shoot(nm, (size, size), (size // 2, int(size * 0.74)), line_t=0.011 * k, extra=extra,
                      shadow=None)


def main():
    a = args()
    raw = a[0]
    which = a[1:]
    data = json.load(open(os.path.join(ROOT, "content", "he", "creatures.json"), encoding="utf-8"))
    job = Job(raw, "creatures")
    for c in data["creatures"]:
        if c["id"] == "garble_kraken":
            continue
        if which and c["id"] not in which:
            continue
        render_creature(job, c["id"], c["radius"])
    anims = job.meta.get("_anims", {})
    for c in data["creatures"]:
        if c["id"] == "garble_kraken":
            continue
        for state in ('noise', 'friend'):
            anims[f"{c['id']}_{state}"] = {"frames": [f"{c['id']}_{state}_0", f"{c['id']}_{state}_1"],
                                           "frameRate": 4 if state == 'friend' else 6, "repeat": -1}
    job.meta["_anims"] = anims
    job.save()


if __name__ == "__main__":
    main()
