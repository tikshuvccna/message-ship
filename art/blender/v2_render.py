"""v2 render driver.

blender -b --python v2_render.py -- portrait <name|all> <rawdir> [expr,expr...]
blender -b --python v2_render.py -- sprite   <name|all> <rawdir> [quick]
blender -b --python v2_render.py -- npc      <name|all> <rawdir>
Raw frames are supersampled and un-outlined; art/pack_v2.py finishes them.
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

import v2lib
from v2lib import *
import v2_cast
from v2_cast import pose

PORTRAIT_RES = 512
TRUTH_CHARS = ('dvora', 'shoshana', 'miriam', 'hillel', 'miller', 'asaf', 'hed')
PORTRAIT_CHARS = ('apprentice_girl', 'apprentice_girl_scarf', 'apprentice_boy', 'apprentice_boy_hat', 'dvora', 'shoshana',
                  'miriam', 'hillel', 'miller', 'asaf', 'hed', 'noam')
PORTRAIT_SSAA = 2


def all_cast():
    d = dict(v2_cast.CAST)
    try:
        import v2_cast_npc
        d.update(v2_cast_npc.CAST)
        import v2_cast_t3
        d.update(v2_cast_t3.CAST)
        import v2_skins
        d.update(v2_skins.CAST)
    except ImportError as e:
        print("cast import failed", e)
    return d


def build(name, truth=False, line_t=0.012):
    reset()
    STATE['truth'] = truth
    STATE['line_t'] = line_t
    render_setup(samples=32)
    world_and_lights('truth' if truth else 'day')
    h = all_cast()[name]()
    h.name = name
    return h


def head_world(h):
    bpy.context.view_layer.update()
    return h.P['head'].matrix_world.translation.copy()


def do_portrait(name, rawdir, exprs=None):
    meta = all_cast()[name]
    probe = build(name)
    info = getattr(probe, 'portrait', {})
    base = ['neutral', 'happy', 'worried', 'surprised', 'sad', 'blink']
    if name.startswith('apprentice'):
        base = ['neutral', 'happy', 'worried', 'surprised', 'blink']
    if name in TRUTH_CHARS:
        base = base + ['truth']
    exprs = exprs or info.get('exprs', base)
    want_truth = 'truth' in exprs
    exprs = [e for e in exprs if e != 'truth']
    od = os.path.join(rawdir, "portraits")
    os.makedirs(od, exist_ok=True)

    def setup_and_shoot(h, elist, truth):
        h.flags['hold'] = info.get('hold')
        pose(h, 'idle', 0, 4)
        yaw = info.get('yaw', -26)
        h.P['root'].rotation_euler = (0, 0, math.radians(yaw))
        bpy.context.view_layer.update()
        hw = head_world(h)
        scale = info.get('scale', 1.18)
        target = hw + Vector((0, 0, info.get('dz', -0.08)))
        add_lines(t=info.get('line', 0.0042))
        portrait_camera(target, dist=8, res=PORTRAIT_RES * PORTRAIT_SSAA, elev=info.get('elev', 7), yaw=0,
                        ortho_scale=scale)
        bpy.context.scene.eevee.taa_render_samples = 48
        for e in elist:
            h.face.clear()
            if e == 'blink':
                h.face.build('neutral', closed=True)
            else:
                h.face.build(e)
            if 'face_fn' in info:
                info['face_fn'](h, e)
            render_to(os.path.join(od, f"{name}_{e}.png"))
            print("PORTRAIT", name, e)
    setup_and_shoot(probe, exprs, False)
    if want_truth:
        h = build(name, truth=True)
        setup_and_shoot(h, ['truth'], True)


def do_sprite(name, rawdir, quick=False, anims=(('idle', 4), ('walk', 8)), dirs=None, ssaa=4, expr='neutral',
              sub='characters_v2'):
    h = build(name, line_t=0.011)
    # game camera looks down 35 deg: tip hats back and lift the face so it stays readable
    hat = h.P['hat'] if ('hat' in h.P and h.P['hat'].type == 'EMPTY') else None
    hat_x0 = hat.rotation_euler.x if hat else 0.0
    tilt = getattr(h, 'sprite_hat_tilt', -0.22)
    h.flags.setdefault('head_pitch', -0.16)
    add_lines()
    od = os.path.join(rawdir, sub, name)
    os.makedirs(od, exist_ok=True)
    sprite_camera(128, 128, (64, 110), ssaa=ssaa)
    bpy.context.scene.eevee.taa_render_samples = 24
    h.face.build(getattr(h, 'sprite_expr', expr))
    open_objs = list(h.face.fp.objs)
    h.face.fp.objs = []
    h.face.build(getattr(h, 'sprite_expr', expr), closed=True)
    closed_objs = list(h.face.fp.objs)
    t0 = time.time()
    count = 0
    for anim, n in anims:
        for dname, deg in (dirs or DIRECTIONS):
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
                if hat:   # tip the brim away from the camera in every facing
                    hat.rotation_euler.x = hat_x0 + tilt * math.cos(math.radians(deg))
                bpy.context.view_layer.update()
                render_to(os.path.join(od, f"{anim}_{dname}_{i}.png"))
                count += 1
    print(f"SPRITE {name}: {count} frames {time.time() - t0:.1f}s")


NPC_DIRS = [("S", 0), ("SE", 45), ("E", 90), ("SW", 315), ("W", 270)]


def main():
    a = args()
    mode, which, rawdir = a[0], a[1], a[2]
    extra = a[3] if len(a) > 3 else None
    cast = all_cast()
    names = (list(PORTRAIT_CHARS) if mode == 'portrait' else list(cast)) if which == 'all' else which.split(',')
    for nm in names:
        t0 = time.time()
        if mode == 'portrait':
            do_portrait(nm, rawdir, extra.split(',') if extra else None)
        elif mode == 'sprite':
            do_sprite(nm, rawdir, quick=(extra == 'quick'))
        elif mode == 'npc':
            do_sprite(nm, rawdir, anims=(('idle', 4),), dirs=NPC_DIRS, sub='npcs')
        print(f"DONE {mode} {nm} {time.time() - t0:.1f}s")


main()
