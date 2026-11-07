"""Message Ship character render driver.

blender -b --python art/blender/ms_render.py -- portrait <name[,name]|all> <ABS rawdir>
blender -b --python art/blender/ms_render.py -- sprite   <name[,name]|all> <ABS rawdir> [quick]
names: hero_girl hero_boy naama uri talia barak bit
Raw: <rawdir>/portraits/<name>_<expr>.png (1024, SSAA 2), <rawdir>/characters/<name>/<anim>_<DIR>_<i>.png (SSAA 4).
Pack: python art/pack_cast.py <rawdir>
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

from v2lib import *
from v2_cast import pose
import ms_cast

EXPRS = ['neutral', 'happy', 'worried', 'surprised']
PORTRAIT_RES = 512
SSAA_P = 2


def scene(line_t=0.012):
    reset()
    STATE['truth'] = False
    STATE['line_t'] = line_t
    STATE['lines'] = True
    render_setup(samples=32)
    world_and_lights('day')


def build(name, line_t=0.012):
    scene(line_t)
    h = ms_cast.CAST[name]()
    h.name = name
    return h


def do_portrait(name, rawdir):
    od = os.path.join(rawdir, "portraits")
    os.makedirs(od, exist_ok=True)
    if name == 'bit':
        for e in EXPRS:
            scene(0.004)
            r = ms_cast.bit(e, 0)
            r.rotation_euler = (0, 0, math.radians(-18))
            add_lines(t=0.004)
            portrait_camera((0, 0, 0.04), dist=8, res=PORTRAIT_RES * SSAA_P, elev=8, yaw=0, ortho_scale=1.05)
            bpy.context.scene.eevee.taa_render_samples = 48
            render_to(os.path.join(od, f"bit_{e}.png"))
        return
    h = build(name)
    info = getattr(h, 'portrait', {})
    pose(h, 'idle', 0, 4)
    h.P['root'].rotation_euler = (0, 0, math.radians(info.get('yaw', -24)))
    bpy.context.view_layer.update()
    hw = h.P['head'].matrix_world.translation.copy()
    add_lines(t=info.get('line', 0.0042))
    portrait_camera(hw + Vector((0, 0, info.get('dz', -0.08))), dist=8, res=PORTRAIT_RES * SSAA_P, elev=info.get('elev', 7),
                    yaw=0, ortho_scale=info.get('scale', 1.18))
    bpy.context.scene.eevee.taa_render_samples = 48
    for e in EXPRS:
        h.face.clear()
        h.face.build(e)
        render_to(os.path.join(od, f"{name}_{e}.png"))
        print("PORTRAIT", name, e)


def do_sprite(name, rawdir, quick=False):
    od = os.path.join(rawdir, "characters", name)
    os.makedirs(od, exist_ok=True)
    if name == 'bit':
        for i in range(4):
            scene(0.009)
            r = ms_cast.bit('neutral' if i != 2 else 'happy', i)
            r.location = (0, 0, 1.25)
            r.rotation_euler = (0, 0, math.radians(-15))
            add_lines(t=0.009)
            sprite_camera(128, 128, (64, 110), ssaa=4)
            render_to(os.path.join(od, f"float_{i}.png"))
        return
    h = build(name, line_t=0.011)
    hat = h.P['hat'] if ('hat' in h.P and h.P['hat'].type == 'EMPTY') else None
    hat_x0 = hat.rotation_euler.x if hat else 0.0
    tilt = getattr(h, 'sprite_hat_tilt', -0.22)
    h.flags.setdefault('head_pitch', -0.16)
    add_lines()
    sprite_camera(128, 128, (64, 110), ssaa=4)
    bpy.context.scene.eevee.taa_render_samples = 24
    h.face.build('neutral')
    open_objs = list(h.face.fp.objs)
    h.face.fp.objs = []
    h.face.build('neutral', closed=True)
    closed_objs = list(h.face.fp.objs)
    t0 = time.time()
    for anim, n in (('idle', 4), ('walk', 8)):
        for dname, deg in DIRECTIONS:
            if quick and dname not in ('S', 'E', 'NW', 'SE'):
                continue
            for i in range(n):
                if quick and i not in (0, 3):
                    continue
                pose(h, anim, i, n)
                blink = anim == 'idle' and i == 3
                for o in open_objs:
                    o.hide_render = blink
                for o in closed_objs:
                    o.hide_render = not blink
                h.P['root'].rotation_euler = (0, 0, math.radians(deg))
                if hat:
                    hat.rotation_euler.x = hat_x0 + tilt * math.cos(math.radians(deg))
                bpy.context.view_layer.update()
                render_to(os.path.join(od, f"{anim}_{dname}_{i}.png"))
    print(f"SPRITE {name} {time.time() - t0:.1f}s")


def main():
    a = args()
    mode, which, raw = a[0], a[1], a[2]
    quick = len(a) > 3 and a[3] == 'quick'
    names = (list(ms_cast.CAST) + ['bit']) if which == 'all' else which.split(',')
    for nm in names:
        if mode == 'portrait':
            do_portrait(nm, raw)
        else:
            do_sprite(nm, raw, quick)
        print("DONE", mode, nm)


main()
