"""Four complete wheel corners in "Exterior/Wheels".

Per corner (XX = FL, FR, RL, RR):
    Wheel_XX            empty at the wheel centre = spin pivot (parent of the
                        rotating parts below; spin about its local Y axis)
      Wheel_XX_Rim        cast wheel (black + diamond-turned face)
      Wheel_XX_Hardware   centre cap, 5 bolts, valve
      Wheel_XX_Tyre       225/40 R18 (shape key "Loaded" = static deflection)
      Brake_XX_Disc       brake disc
    Brake_XX_Caliper    caliper, pads, carrier (static, not parented)
    Brake_XX_Hub        hub flange, knuckle / wheel carrier, shield, CV joint

Left and right wheels share the same mesh data: a cast wheel is not mirror
symmetric, the right-hand wheel is the same part turned 180 deg about Z.
Calipers, knuckles and shields are mirrored parts -> mirrored meshes.

Lateral position: spec.wheel_centres() puts the tyre centre plane at
track/2 (tracks are tread-centre to tread-centre); the hub face is at
track/2 + ET (46 mm) and the outer tyre wall at track/2 + ~115.6 mm
(protector rib 117 mm).
"""
from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from .. import spec
from ..core import mesh as cmesh
from ..core import scene as sc
from . import brakes, builder as B, rim, tyre

COL = "Exterior/Wheels"


def _mesh_rim(ctx):
    mb = B.MB()
    rim.build_rim(mb, 0, 1, ctx.detail)
    return mb.build("Wheel_Rim", [ctx.mat("wheel_black"), ctx.mat("wheel_diamond_cut")], COL, 35.0)


def _mesh_hardware(ctx):
    mb = B.MB()
    rim.build_cap(mb, 0, 1)
    rim.build_bolts(mb, 2)
    rim.build_valve(mb, 3, 4, angle_deg=0.0)
    ob = mb.build("Wheel_Hardware", [ctx.mat("wheel_cap"), ctx.mat("badge_chrome"),
                                     ctx.mat("wheel_bolt"), ctx.mat("aluminium_matt"),
                                     ctx.mat("rubber_seal")], COL, 32.0)
    cmesh.recalc_normals(ob)
    return ob


def _mesh_tyre(ctx):
    mb = B.MB()
    tyre.build_tyre(mb, 0, 1, ctx.detail)
    ob = mb.build("Wheel_Tyre", [ctx.mat("tyre"), ctx.mat("tyre_text")], COL, 40.0)
    tyre.add_load_shape_key(ob)
    return ob


def _mesh_disc(ctx, front):
    mb = B.MB()
    if front:
        d = brakes.build_disc_front(mb, 0, 1)
    else:
        d = brakes.build_disc_rear(mb, 0, 1)
    ob = mb.build("Brake_Disc_" + ("F" if front else "R"),
                  [ctx.mat("brake_disc"), ctx.mat("brake_disc_hat")], COL, 40.0)
    cmesh.recalc_normals(ob)
    return ob, d


def _mesh_caliper(ctx, front, d):
    mb = B.MB()
    if front:
        brakes.build_caliper_front(mb, d, 0, 1, 2)
    else:
        brakes.build_caliper_rear(mb, d, 0, 1, 2)
    ob = mb.build("Brake_Caliper_" + ("F" if front else "R"),
                  [ctx.mat("caliper"), ctx.mat("steel_dark"), ctx.mat("brake_pad")], COL, 40.0)
    cmesh.recalc_normals(ob)
    return ob


def _mesh_hub(ctx, front, d):
    mb = B.MB()
    brakes.build_shield(mb, d, 0)
    if front:
        brakes.build_hub_front(mb, 0, 0, 1)
    else:
        brakes.build_hub_rear(mb, 0, 1)
    ob = mb.build("Brake_Hub_" + ("F" if front else "R"),
                  [ctx.mat("steel_dark"), ctx.mat("rubber_seal")], COL, 40.0)
    cmesh.recalc_normals(ob)
    return ob


def _mirrored_data(me, name):
    m2 = me.copy()
    m2.name = name
    m2.transform(Matrix.Diagonal(Vector((1, -1, 1, 1))))
    m2.flip_normals()
    m2.update()
    return m2


def _instance(name, me, loc, rot_z=0.0, parent=None):
    ob = bpy.data.objects.new(name, me)
    sc.link(ob, COL)
    if parent is not None:
        ob.parent = parent
    else:
        ob.location = loc
        ob.rotation_euler = (0, 0, rot_z)
    return ob


def build(ctx):
    sc.collection(COL)
    proto = {}
    proto["rim"] = _mesh_rim(ctx)
    proto["hw"] = _mesh_hardware(ctx)
    proto["tyre"] = _mesh_tyre(ctx)
    for front in (True, False):
        k = "F" if front else "R"
        disc, d = _mesh_disc(ctx, front)
        proto["disc" + k] = disc
        proto["cal" + k] = _mesh_caliper(ctx, front, d)
        proto["hub" + k] = _mesh_hub(ctx, front, d)
    # mirrored data for the right-hand static parts
    mirror = {}
    for k in ("calF", "calR", "hubF", "hubR"):
        mirror[k] = _mirrored_data(proto[k].data, proto[k].data.name + "_R")

    for corner, (x, y, z) in spec.wheel_centres().items():
        left = corner[1] == "L"
        front = corner[0] == "F"
        ax = "F" if front else "R"
        rz = 0.0 if left else math.pi
        piv = bpy.data.objects.new("Wheel_" + corner, None)
        piv.empty_display_type = "ARROWS"
        piv.empty_display_size = 0.15
        sc.link(piv, COL)
        piv.location = (x, y, z)
        piv.rotation_euler = (0, 0, rz)
        ctx.register("wheel_" + corner, piv)
        parts = (("Rim", proto["rim"].data), ("Hardware", proto["hw"].data),
                 ("Tyre", proto["tyre"].data))
        for nm, me in parts:
            ob = _instance(f"Wheel_{corner}_{nm}", me, None, parent=piv)
            ctx.register(f"wheel_{corner}_{nm.lower()}", ob)
        ob = _instance(f"Brake_{corner}_Disc", proto["disc" + ax].data, None, parent=piv)
        ctx.register(f"brake_{corner}_disc", ob)
        for nm, key in (("Caliper", "cal" + ax), ("Hub", "hub" + ax)):
            me = proto[key].data if left else mirror[key]
            ob = _instance(f"Brake_{corner}_{nm}", me, (x, y, z))
            ctx.register(f"brake_{corner}_{nm.lower()}", ob)
    # remove the prototype objects (their meshes live on in the instances)
    for ob in proto.values():
        bpy.data.objects.remove(ob, do_unlink=True)
    # shape keys are per mesh: the shared tyre keeps "Loaded" = 1 for all four
    return ctx
