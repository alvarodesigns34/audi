"""Studio lighting, cameras and Cycles rendering for verification images."""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

from . import scene as sc


def studio(floor=True, world_strength=0.35, floor_color=(0.55, 0.55, 0.56)):
    scn = bpy.context.scene
    world = bpy.data.worlds.new("Studio") if not scn.world else scn.world
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    mapping = nt.nodes.new("ShaderNodeMapping")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    # vertical gradient: dark floor horizon -> bright soft top (studio softbox feel)
    mapping.inputs["Rotation"].default_value = (0, -math.pi / 2, 0)
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.05, 0.05, 0.055, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.95, 0.95, 1.0, 1)
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = world_strength
    nt.links.new(bg.outputs[0], out.inputs[0])

    col = sc.collection("_Studio")
    # Large overhead softbox + side strips (classic car studio)
    def area(name, loc, rot, size, energy, sx=None):
        L = bpy.data.lights.new(name, "AREA")
        L.shape = "RECTANGLE"
        L.size = size
        L.size_y = sx or size
        L.energy = energy
        ob = bpy.data.objects.new(name, L)
        ob.location = loc
        ob.rotation_euler = rot
        ob.visible_camera = False      # seen through the windscreen otherwise
        ob.visible_transmission = False
        col.objects.link(ob)
        return ob

    area("Softbox_Top", (-1.3, 0, 6.0), (0, 0, 0), 7.0, 1400, 3.0)
    area("Strip_L", (-1.3, 5.0, 2.2), (math.radians(70), 0, 0), 8.0, 450, 0.8)
    area("Strip_R", (-1.3, -5.0, 2.2), (math.radians(-70), 0, 0), 8.0, 450, 0.8)
    area("Fill_Front", (6.0, 0, 1.8), (0, math.radians(75), 0), 3.0, 220, 2.0)
    area("Fill_Rear", (-8.5, 0, 1.8), (0, math.radians(-75), 0), 3.0, 200, 2.0)

    if floor:
        me = bpy.data.meshes.new("Floor")
        s = 40
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        fl = bpy.data.objects.new("Floor", me)
        col.objects.link(fl)
        m = bpy.data.materials.new("Studio_Floor")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*floor_color, 1)
        b.inputs["Roughness"].default_value = 0.35
        me.materials.append(m)
    return col


def camera(name="Cam", loc=(6, -6, 2), target=(-1.3, 0, 0.6), lens=70, ortho=None):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    cam_data.clip_end = 200
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new(name, cam_data)
    sc.collection("_Studio").objects.link(cam)
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


# Named viewpoints around the car (centre of car ~ x=-1.3)
CX = -1.2855  # (869 - 3441)/2 /1000
VIEWS = {
    "front34": dict(loc=(CX + 6.2, 4.6, 1.55), target=(CX + 0.2, 0, 0.62), lens=55),
    "rear34": dict(loc=(CX - 6.2, 4.6, 1.75), target=(CX - 0.2, 0, 0.62), lens=55),
    "front34_r": dict(loc=(CX + 6.2, -4.6, 1.55), target=(CX + 0.2, 0, 0.62), lens=55),
    "side_r": dict(loc=(CX, -30.0, 0.70), target=(CX, 0, 0.70), lens=50, ortho=4.9),
    "side": dict(loc=(CX, 30.0, 0.70), target=(CX, 0, 0.70), lens=50, ortho=4.9),
    "front": dict(loc=(30, 0, 0.70), target=(0, 0, 0.70), lens=50, ortho=2.3),
    "rear": dict(loc=(-30, 0, 0.70), target=(-3, 0, 0.70), lens=50, ortho=2.3),
    "top": dict(loc=(CX, 0, 30), target=(CX, 0, 0), lens=50, ortho=4.9),
    "bay": dict(loc=(1.6, 1.3, 1.9), target=(0.12, 0.0, 0.50), lens=32),
    "under": dict(loc=(-1.3, 2.2, -2.6), target=(-1.3, 0.0, 0.2), lens=22),
    "chassis_side": dict(loc=(-1.3, 7.5, 0.45), target=(-1.3, 0.0, 0.40), lens=40),
    "wheel_fl": dict(loc=(0.0, 2.6, 0.32), target=(0, 0.75, 0.32), lens=50),
    # close-ups for detail checks
    "hl_close": dict(loc=(2.2, 1.55, 0.95), target=(0.62, 0.70, 0.67), lens=60),
    "tl_close": dict(loc=(-4.9, 1.9, 1.15), target=(-3.20, 0.62, 0.88), lens=55),
    "rear_close": dict(loc=(-6.4, 1.2, 1.55), target=(-3.20, 0.0, 0.95), lens=45),
    "intake_close": dict(loc=(2.6, 1.5, 0.55), target=(0.75, 0.70, 0.38), lens=55),
    "side_close": dict(loc=(-1.8, 3.6, 0.85), target=(-1.8, 0.85, 0.75), lens=35),
    "cockpit": dict(loc=(-1.75, 0.37, 1.12), target=(-0.6, 0.15, 0.85), lens=24, fill=True),
    "interior_rear": dict(loc=(-2.9, 0.0, 1.20), target=(-0.8, 0.0, 0.80), lens=20, fill=True),
}


def render(path, view="front34", res=(1600, 900), samples=64, engine="CYCLES",
           transparent=False, denoise=True, extra=None):
    scn = bpy.context.scene
    v = dict(VIEWS[view]) if isinstance(view, str) else dict(view)
    fill = v.pop("fill", False)
    cam = camera("Cam_" + (view if isinstance(view, str) else "custom"), **v)
    fills = cabin_fill() if fill else []
    scn.camera = cam
    scn.render.engine = engine
    scn.cycles.samples = samples
    scn.cycles.device = "CPU"
    scn.cycles.use_denoising = denoise
    try:
        scn.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    scn.cycles.max_bounces = 8
    scn.cycles.transparent_max_bounces = 16
    scn.render.film_transparent = transparent
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    for ob in fills:
        bpy.data.objects.remove(ob, do_unlink=True)
    return path


def cabin_fill(strength=1.0):
    """Soft area lights under the roof for interior views (the headliner and
    the body shell block the studio softbox).  Temporary: removed after the
    render.  Views opt in with ``fill=True``."""
    col = sc.collection("_Studio")
    out = []
    for name, loc, size, energy in (("Fill_Cabin_F", (-1.45, 0.0, 1.24), (1.0, 1.1), 16.0),
                                    ("Fill_Cabin_R", (-2.35, 0.0, 1.22), (0.8, 1.1), 10.0),
                                    ("Fill_Cabin_Boot", (-3.05, 0.0, 1.20), (0.4, 0.9), 6.0)):
        L = bpy.data.lights.new(name, "AREA")
        L.shape = "RECTANGLE"
        L.size, L.size_y = size
        L.energy = energy * strength
        ob = bpy.data.objects.new(name, L)
        ob.location = loc
        ob.visible_camera = False      # light only, never seen as a white panel
        ob.visible_glossy = False      # nor reflected in the windscreen
        ob.visible_transmission = False
        col.objects.link(ob)
        out.append(ob)
    return out
