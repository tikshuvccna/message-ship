"""The Garble Kraken (boss): head in 3 noise phases + friend, arms per phase. Separate atlas creatures/kraken.

blender -b --python art/blender/kraken.py -- <ABS rawdir>
Phase 1 "rules": 5 arms, each broken by another rule (band colour = ammo colour of that rule + a symbol).
Phase 2 "layers": seven glowing eyes stacked like the seven floors on the head; arms ringed with the 7 layer colours.
Phase 3 "encapsulation": crates in crates on the head, arms clutching containers.
Head and arms rise out of the water: anchor = water point under them (engine adds foam rings).
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

from v2lib import *
from shiplib import Job, ring_tube
import sea_creatures as SC

RULES = [("addr", "#ffb84a", "@"), ("code", "#4ad6c8", "Aa"), ("fmt", "#8f7bff", "#"), ("size", "#ff7f6e", "XL"),
         ("time", "#7fd957", "1:2")]
LAYERS = ["#d94f4f", "#e98a3d", "#e8cf3a", "#58c46a", "#3fb5c9", "#5a7ee0", "#a566d9"]


def skin(phase):
    if phase == 'friend':
        return "#c9a0ff", "#ffc8e0"
    return {1: ("#4a3a5e", "#6a4a6a"), 2: ("#3a3a5a", "#4a4a6e"), 3: ("#4a4048", "#6a5650")}[phase]


def head(phase, f):
    c1, c2 = skin(phase)
    st = SC.St('friend' if phase == 'friend' else 'noise', f)
    b = pivot("kb", rot=(0, 0, math.radians(-12)))
    bob = 0.08 * math.sin(math.pi * f)
    def deform(p):
        z = p.z
        wob = 1.0 if phase == 'friend' else 1 + 0.04 * math.sin(p.x * 6 + p.z * 4)
        return Vector((p.x * wob, p.y * wob, max(z, -0.35) if z > -0.35 else -0.35))
    blob("mantle", 2.0, mat(c1, kind='soft', rim=0.6, pat='patches', color2=c2, P=dict(scale=4.5, thr=0.6, sharp=3.0)), b,
         loc=(0, 0.3, 1.1 + bob), scale=(0.95, 0.85, 1.3), deform=deform)
    # brow ridge / cheeks
    for s in (-1, 1):
        ellipsoid("cheek", 0.6, mat(c2, kind='soft', rim=0.5), b, loc=(s * 0.95, -1.2, 0.85 + bob), scale=(1, 0.6, 0.7))
    if phase == 'friend':
        for s in (-1, 1):
            SC.eye_friend(b, (s * 0.66, -1.5, 1.85 + bob), 0.5, iris="#6a3aa0", look=(0.1, -0.1))
            ellipsoid("blush", 0.3, mat("#ff8ab0", kind='soft', rim=0), b, loc=(s * 1.15, -1.45, 1.3 + bob), scale=(1, 0.3, 0.6))
        tube("smile", [Vector((-0.4, -1.7, 1.15 + bob)), Vector((0, -1.8, 1.0 + bob)), Vector((0.4, -1.7, 1.15 + bob))],
             [0.05, 0.07, 0.05], mat("#5a2a40", kind='flat'), b, seg=6, sub=4)
        # messenger cap + satchel strap: Tamir's messenger, calm again
        cyl("cap", 0.75, 0.7, 0.35, mat("#2a4a8a", kind='soft', rim=0.5), b, loc=(0.15, 0.3, 3.35 + bob), rot=(-0.15, 0.1, 0))
        ellipsoid("visor", 0.55, mat("#1a2a5a", kind='soft'), b, loc=(0.1, -0.35, 3.35 + bob), scale=(1, 0.7, 0.15))
        ellipsoid("badge", 0.14, mat("#e8b04a", metal=True), b, loc=(0.12, -0.42, 3.55 + bob), scale=(1, 0.4, 1))
        return
    # noise eyes
    for s in (-1, 1):
        SC.eye_noise(b, (s * 0.66, -1.48, 1.85 + bob), 0.48, side=s)
    pts = [Vector((-0.6 + 0.3 * i, -1.72, 1.05 + bob + (0.12 if i % 2 else -0.04))) for i in range(5)]
    tube("zig", pts, [0.07], mat("#120c18", kind='flat'), b, seg=5, sub=1)
    if phase == 1:   # five rule runes glowing on the forehead
        for i, (_, col, sym) in enumerate(RULES):
            a = -0.8 + 0.4 * i
            p = Vector((1.15 * math.sin(a), -1.25 * math.cos(a) - 0.05, 2.75 + bob + 0.15 * math.cos(a)))
            SC.glyph(sym, glow(col, 2.0), b, p, 0.32, rot=(math.pi / 2 - 0.2, 0, a * 0.8))
    elif phase == 2:   # seven stacked eyes = seven floors
        for i, col in enumerate(LAYERS):
            z = 2.35 + 0.19 * i + bob
            ellipsoid("lsock", 0.17, mat("#120c18", kind='flat'), b, loc=(0, -1.42 + 0.12 * i, z), scale=(1.3, 0.4, 0.62))
            ellipsoid("leye", 0.13, glow(col, 2.4), b, loc=(0, -1.49 + 0.12 * i, z), scale=(1.3, 0.4, 0.48))
    elif phase == 3:   # nested crates on the head (data in segment in packet in frame)
        for i, (sz, col) in enumerate(((1.4, "#8a6a4a"), (1.05, "#b8864a"), (0.72, "#d9a764"), (0.42, "#f4e7c5"))):
            box("crate", (sz, sz * 0.9, sz * 0.75), mat(SC.mixhex(col, SC.NOISE_DARK, 0.35), kind='soft', rim=0.4,
                pat='planks', color2="#3a2a20", P=dict(axis='z', fv=6, fu=0.0, butt=0.0, seam=0.1)), b,
                loc=(0.1 * i, 0.3, 3.05 + sum((1.4, 1.05, 0.72, 0.42)[:i]) * 0.72 + bob), rot=(0, 0, 0.15 * i), bevel=0.04)
    SC.glyph_scatter(b, 14, (0, -1.6, 2.0), 1.6, 1.0, 0.4, st, 300 + phase)


def arm(kind, f, rule=0):
    """kind: p1 (rule colour band), p2 (layer rings), p3 (holding a container), friend."""
    phase = {'p1': 1, 'p2': 2, 'p3': 3, 'friend': 'friend'}[kind]
    c1, c2 = skin(phase)
    sway = 0.35 * math.sin(math.pi * f + rule)
    pts = [Vector((0, 0.2, -0.3)), Vector((0.15, 0.0, 0.8)), Vector((-0.05 + sway * 0.4, -0.05, 1.9)),
           Vector((0.35 + sway, -0.1, 2.9)), Vector((0.9 + sway, -0.15, 3.35)), Vector((1.15 + sway, -0.2, 3.0)),
           Vector((0.85 + sway, -0.25, 2.75))]
    rad = [0.42, 0.38, 0.32, 0.25, 0.17, 0.11, 0.07]
    tube("arm", pts, rad, mat(c1, kind='soft', rim=0.6), pivot("ab"), seg=16, sub=6)
    ab = bpy.data.objects["ab"]
    # suckers along the inner (camera) side
    from v2lib import _catmull
    C = _catmull(pts, 6)
    for i in range(3, len(C) - 4, 3):
        t = i / len(C)
        r = 0.42 * (1 - t) + 0.07
        p = C[i] + Vector((0.0, -r * 0.92, 0.0))
        ellipsoid("suck", r * 0.38, mat(c2, kind='soft', rim=0.4), ab, loc=p, scale=(1, 0.45, 1))
    if kind == 'p1':
        _, col, sym = RULES[rule]
        for k in (14, 18):
            ring_tube("band", C[k], 0.27 - 0.06 * (k - 14) / 4, 0.06, glow(col, 1.8), ab, axis='z', seg=20, tseg=6)
        SC.glyph(sym, glow(col, 2.4), ab, C[16] + Vector((0, -0.45, 0.0)), 0.36)
        SC.glyph_scatter(ab, 4, (0.3, -0.4, 1.6), 0.6, 0.8, 0.26, SC.St('noise', f), 400 + rule)
    elif kind == 'p2':
        for i, col in enumerate(LAYERS):
            k = 6 + i * 3
            r = 0.42 * (1 - k / len(C)) + 0.12
            ring_tube("lr", C[k], r, 0.05, glow(col, 1.6), ab, axis='z', seg=20, tseg=5)
    elif kind == 'p3':
        tip = C[-6]
        for i, (sz, col) in enumerate(((0.62, "#8a6a4a"), (0.4, "#d9a764"))):
            box("cr", (sz, sz, sz * 0.8), mat(SC.mixhex(col, SC.NOISE_DARK, 0.3), kind='soft', rim=0.4, pat='planks',
                color2="#3a2a20", P=dict(axis='z', fv=8, fu=0.0, butt=0.0, seam=0.1)), ab,
                loc=tip + Vector((0.1, -0.25, -0.35 + 0.5 * i)), rot=(0.2, 0.1, 0.3 * i), bevel=0.03)
    else:
        for i in range(4):
            ellipsoid("heart", 0.08, mat("#ff8ab0", kind='soft'), ab, loc=C[-3] + Vector((0.3 + 0.15 * i, -0.3, 0.4 + 0.25 * i)))


def main():
    raw = args()[0]
    job = Job(raw, "kraken")
    def shoot_head(nm, phase, f):
        job.scene('day', samples=24)
        STATE['line_t'] = 0.02
        head(phase, f)
        ex = dict(note="anchor = water point under the head")
        if phase != 'friend':
            ex['glitch'] = [500 + phase, f]
        job.shoot(nm, (420, 360), (210, 300), line_t=0.02, extra=ex)
    for ph in (1, 2, 3):
        for f in (0, 1):
            shoot_head(f"kraken_head_p{ph}_{f}", ph, f)
    for f in (0, 1):
        shoot_head(f"kraken_head_friend_{f}", 'friend', f)
    def shoot_arm(nm, kind, f, rule=0):
        job.scene('day', samples=24)
        arm(kind, f, rule)
        job.shoot(nm, (200, 260), (70, 240), line_t=0.02, extra=dict(note="anchor = water point at the arm base; flipX for the other side"))
    for k in range(5):
        for f in (0, 1):
            shoot_arm(f"kraken_arm_p1_{RULES[k][0]}_{f}", 'p1', f, k)
    for kind in ('p2', 'p3', 'friend'):
        for f in (0, 1):
            shoot_arm(f"kraken_arm_{kind}_{f}", kind, f)
    an = {}
    for ph in ("p1", "p2", "p3", "friend"):
        an[f"kraken_head_{ph}"] = {"frames": [f"kraken_head_{ph}_0", f"kraken_head_{ph}_1"], "frameRate": 3, "repeat": -1}
    for k in range(5):
        r = RULES[k][0]
        an[f"kraken_arm_p1_{r}"] = {"frames": [f"kraken_arm_p1_{r}_0", f"kraken_arm_p1_{r}_1"], "frameRate": 3, "repeat": -1}
    for kind in ('p2', 'p3', 'friend'):
        an[f"kraken_arm_{kind}"] = {"frames": [f"kraken_arm_{kind}_0", f"kraken_arm_{kind}_1"], "frameRate": 3, "repeat": -1}
    job.meta["_anims"] = an
    job.save()


main()
