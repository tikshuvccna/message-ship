"""Shared Blender helpers for the "Too Quiet" art pipeline.

Run via:  blender.exe -b --python <script>.py -- <args>
Everything here is deterministic and headless (EEVEE, transparent film).

Conventions
- Z is up. A character faces -Y at rotation 0 (towards the camera = direction "S").
- The camera is fixed (orthographic, 35 deg elevation). To get the 8 directions the
  SUBJECT is rotated about Z (equivalent to orbiting the camera, but the lighting
  then stays identical on screen for every direction, which keeps sprites cohesive).
- World unit -> pixels: PPU (pixels per unit) is constant for characters and props.
"""
import math
import sys

import bpy
import bmesh
from mathutils import Vector, Euler

ELEVATION_DEG = 35.0          # camera looks down 35 degrees below the horizon
PPU = 56.0                    # output pixels per world unit (before supersampling)
SSAA = 4                      # render at 4x, downscale in pack step (anti-aliasing)

# direction name -> subject rotation about Z (degrees). 0 = facing camera.
DIRECTIONS = [("S", 0), ("SW", 315), ("W", 270), ("NW", 225),
              ("N", 180), ("NE", 135), ("E", 90), ("SE", 45)]

# ---------------------------------------------------------------- colours
def srgb(hexstr):
    """'#rrggbb' -> linear float tuple."""
    h = hexstr.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


PAL = dict(
    skin_a="#f1c4a0", skin_b="#c98c64", skin_c="#e6b896",
    cream="#f3e4c4", gold="#e8b04a", amber="#f2a64a", teal="#35d3b0",
    leather="#8a5a36", leather_d="#5e3a22", wood="#a06a3e", wood_d="#6b4326",
    plum="#6a3f73", wine="#a94a62", indigo="#3e4486", forest="#2f7d6f",
    ochre="#d68f3a", straw="#e1b865", stone="#a29a92", stone_d="#756e72",
    thatch="#c99a4a", tile="#b4553a", teal_roof="#3f8f93", leaf1="#4f9a4f",
    leaf2="#6cb257", leaf3="#2f6b48", bark="#6d4a33", plaster="#efd9b0",
    plaster2="#e8c6a0", blue_plaster="#c9d2e6", shadow_violet="#2a1d4a",
    window="#ffc66a", gray_hair="#d8d4d8", brown_hair="#5a3626",
    dark_hair="#2e2020", red="#c44b3f", white="#f6f0e6",
)


_MAT_CACHE = {}


def reset_scene():
    _MAT_CACHE.clear()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights):
        for b in list(coll):
            coll.remove(b)


# ---------------------------------------------------------------- materials


def toon(color, rim=0.35, shade=(0.40, 0.36, 0.66), name=None):
    """Soft three-step toon material. color is '#hex' or key of PAL.
    shade = multiplier giving the blue-violet shadow tone. rim adds an amber rim on lit side."""
    hexv = PAL.get(color, color)
    key = (hexv, rim, shade)
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    base = Vector(srgb(hexv))
    shadow = (base[0] * shade[0], base[1] * shade[1], base[2] * shade[2])
    light = (min(1, base[0] * 1.18 + 0.05), min(1, base[1] * 1.10 + 0.03), min(1, base[2] * 0.98 + 0.0))
    m = bpy.data.materials.new(name or ("toon_" + hexv))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    diff = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position = 0.18
    e[0].color = (*shadow, 1)
    e[1].position = 0.55
    e[1].color = (*base, 1)
    e2 = e.new(0.90)
    e2.color = (*light, 1)
    nt.links.new(diff.outputs["BSDF"], s2r.inputs["Shader"])
    # luminance of the diffuse result drives the ramp
    sep = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(s2r.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Val"], ramp.inputs["Fac"])
    last = ramp.outputs["Color"]
    if rim > 0:
        lw = nt.nodes.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.35
        rmp = nt.nodes.new("ShaderNodeMath")
        rmp.operation = "MULTIPLY"
        rmp.inputs[1].default_value = rim
        # use fresnel (edge) rather than facing
        nt.links.new(lw.outputs["Fresnel"], rmp.inputs[0])
        smooth = nt.nodes.new("ShaderNodeMath")
        smooth.operation = "MULTIPLY"
        nt.links.new(rmp.outputs["Value"], smooth.inputs[0])
        nt.links.new(sep.outputs["Val"], smooth.inputs[1])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "ADD"
        nt.links.new(smooth.outputs["Value"], mix.inputs["Factor"])
        nt.links.new(last, mix.inputs["A"])
        mix.inputs["B"].default_value = (*srgb("#ffb860"), 1)
        last = mix.outputs["Result"]
    nt.links.new(last, emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    _MAT_CACHE[key] = m
    return m


def glow(color, strength=4.0, alpha=1.0, name=None, soft=False):
    """Emissive material (windows, magic). alpha<1 gives a soft halo."""
    hexv = PAL.get(color, color)
    key = ("glow", hexv, strength, alpha, soft)
    if key in _MAT_CACHE:
        return _MAT_CACHE[key]
    m = bpy.data.materials.new(name or "glow_" + hexv)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*srgb(hexv), 1)
    em.inputs["Strength"].default_value = strength
    if alpha >= 0.999:
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    else:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        mx.inputs["Fac"].default_value = alpha
        if soft:   # radial falloff: opaque at the centre, transparent at the silhouette edge
            lw = nt.nodes.new("ShaderNodeLayerWeight")
            lw.inputs["Blend"].default_value = 0.6
            pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.0
            ml = nt.nodes.new("ShaderNodeMath"); ml.operation = "MULTIPLY"; ml.inputs[1].default_value = alpha
            inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
            nt.links.new(lw.outputs["Facing"], inv.inputs[1])
            nt.links.new(inv.outputs["Value"], pw.inputs[0])
            nt.links.new(pw.outputs["Value"], ml.inputs[0])
            nt.links.new(ml.outputs["Value"], mx.inputs["Fac"])
        nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
        nt.links.new(em.outputs["Emission"], mx.inputs[2])
        nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    _MAT_CACHE[key] = m
    return m


# ---------------------------------------------------------------- geometry
def _link(obj, parent):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def mesh_obj(name, verts, faces, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = rot
    return _link(obj, parent)


def pivot(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.location = loc
    o.rotation_euler = rot
    return _link(o, parent)


def frustum(name, r1, r2, h, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), seg=16,
            caps=(True, True), scale=(1, 1, 1), smooth=True):
    """Cylinder/cone frustum with its BASE at local z=0 and top at z=h."""
    verts, faces = [], []
    for z, r in ((0.0, r1), (h, r2)):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a) * scale[0], r * math.sin(a) * scale[1], z * scale[2]))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
    if caps[0]:
        c = len(verts)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r1 * math.cos(a) * scale[0], r1 * math.sin(a) * scale[1], 0))
        faces.append(tuple(reversed(range(c, c + seg))))
    if caps[1]:
        c = len(verts)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r2 * math.cos(a) * scale[0], r2 * math.sin(a) * scale[1], h * scale[2]))
        faces.append(tuple(range(c, c + seg)))
    return mesh_obj(name, verts, faces, mat, parent, loc, rot, smooth)


def ellipsoid(name, r, mat, parent=None, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), seg=18, rings=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * r * scale[0], v.co.y * r * scale[1], v.co.z * r * scale[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if mat:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    obj.location = loc
    obj.rotation_euler = rot
    return _link(obj, parent)


def box(name, size, mat, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, base=False):
    """Axis box centered at loc (or with base at loc z when base=True). Optional chamfer."""
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
    zc = sz if base else 0
    v = [(-sx, -sy, -sz + zc), (sx, -sy, -sz + zc), (sx, sy, -sz + zc), (-sx, sy, -sz + zc),
         (-sx, -sy, sz + zc), (sx, -sy, sz + zc), (sx, sy, sz + zc), (-sx, sy, sz + zc)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj(name, v, f, mat, parent, loc, rot, smooth=False)
    if bevel > 0:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect='EDGES')
        bm.to_mesh(o.data)
        bm.free()
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    return o


def link_cyl(name, p1, p2, r, mat, parent=None, seg=8, r2=None):
    """Cylinder between two local points."""
    a, b = Vector(p1), Vector(p2)
    d = b - a
    o = frustum(name, r, r if r2 is None else r2, d.length, mat, parent, loc=a, seg=seg)
    o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = d.to_track_quat('Z', 'Y')
    return o


def gable_roof(name, w, d, h, overhang, mat, parent=None, loc=(0, 0, 0), ridge_along='x', sag=0.0):
    """Triangular-prism roof with eaves at z=0 and ridge at z=h; ridge runs along ridge_along."""
    W, D = w / 2 + overhang, d / 2 + overhang
    if ridge_along == 'x':
        v = [(-W, -D, 0), (W, -D, 0), (W, D, 0), (-W, D, 0), (-W, 0, h), (W, 0, h)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
        f = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5)]
    else:
        v = [(-W, -D, 0), (W, -D, 0), (W, D, 0), (-W, D, 0), (0, -D, h), (0, D, h)]
        f = [(0, 4, 5, 3), (1, 2, 5, 4), (0, 1, 4), (3, 5, 2)]
    return mesh_obj(name, v, f, mat, parent, loc, smooth=False)


# ---------------------------------------------------------------- scene rig
def setup_world_and_lights():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*srgb("#7a6fb0"), 1)
    bg.inputs["Strength"].default_value = 0.55
    sc.world = w

    def sun(name, frm, color, energy, angle=0.3):
        ld = bpy.data.lights.new(name, 'SUN')
        ld.energy = energy
        ld.color = color
        ld.angle = angle
        o = bpy.data.objects.new(name, ld)
        bpy.context.scene.collection.objects.link(o)
        d = -Vector(frm)
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = d.to_track_quat('-Z', 'Y')
        return o
    # warm amber key from upper-left-front, cool violet-teal rim from back-right
    sun("key", (-0.9, -0.8, 1.2), srgb("#ffc98a"), 3.2)
    sun("rim", (0.8, 1.0, 0.7), srgb("#8fa8ff"), 1.0)


def setup_camera(cell_w, cell_h, anchor=None, ppu=PPU, ssaa=SSAA):
    """Orthographic oblique camera. The world origin (ground contact) is projected to pixel
    `anchor` (default: horizontally centred, 12 px above the bottom edge)."""
    sc = bpy.context.scene
    if anchor is None:
        anchor = (cell_w / 2, cell_h - 12)
    e = math.radians(ELEVATION_DEG)
    cd = bpy.data.cameras.new("cam")
    cd.type = 'ORTHO'
    cd.ortho_scale = max(cell_w, cell_h) / ppu
    cd.clip_start, cd.clip_end = 0.1, 100
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    # target point on the vertical axis so origin lands on anchor.y
    off_up = (cell_h / 2 - anchor[1]) / ppu        # negative = origin below centre
    tz = -off_up / math.cos(e)
    tx = (cell_w / 2 - anchor[0]) / ppu
    target = Vector((tx, 0, tz))
    dist = 30
    cam.location = target + Vector((0, -dist * math.cos(e), dist * math.sin(e)))
    cam.rotation_euler = Euler((math.radians(90 - ELEVATION_DEG), 0, 0))
    sc.camera = cam
    r = sc.render
    r.resolution_x, r.resolution_y = cell_w * ssaa, cell_h * ssaa
    r.resolution_percentage = 100
    return cam


def setup_render(samples=24):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.compression = 15
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def script_args():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return []
