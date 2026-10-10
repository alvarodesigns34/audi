"""Xenon plus headlights with LED daytime running light guide (8V pre-facelift).

Layout (photographs of the 8V xenon unit, sline_front.jpg / yellow.jpg): the
unit wraps round the front corner from the grille chamfer (inner tip) to the
fender (upper rear corner).  Bi-xenon projector in the outer part, a
reflector bowl / turn-signal module inboard of it, a titanium-grey inner
bezel and an LED light guide running along the lower edge - the
characteristic "wave" - rising at the inner end.  The outer lens is cut from
the body surface so it is flush with the bumper / fender.
"""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..body import surftools as st
from ..core import mesh, scene
from ..core.curves import catmull_rom, resample

COL = "Exterior/Lights"


def _on_skin(surf, p, d):
    """Project point p onto the skin along -d (d = outward view direction)."""
    from mathutils import Vector
    hit = surf.bvh.ray_cast(Vector(p + d * 0.4), Vector(-d), 0.8)
    return np.array(hit[0][:]) if hit[0] is not None else p


def _unit(ctx, ref, surf, mirror):
    sfx = ".R" if mirror else ".L"
    s = -1 if mirror else 1
    lens_m = ctx.mat("lens_clear")
    house = ctx.mat("lamp_housing")
    refl = ctx.mat("reflector")
    bezel = ctx.mat("titanium_grey")
    led = ctx.mat("led_white")
    amber = ctx.mat("led_amber")
    d = op.headlight_dir(mirror)
    tmp = scene.temp_collection("_tmp_patch")

    # ---- outer lens (body-flush) ------------------------------------------------
    cut = op.headlight_cutter("HL_cut" + sfx, surf, tmp, mirror=mirror, depth_in=0.05,
                              depth_out=0.05)
    lens = st.patch_with_cutter(ref, cut, "Headlight_Lens" + sfx, COL, lens_m)
    st.offset(lens, 0.0006)
    mesh.solidify(lens, 0.003, offset=-1.0)
    mesh.shade_smooth(lens, 60)

    # ---- housing bucket (tapering back along -d) ---------------------------------
    P = op.headlight_outline(surf, mirror, n=200)
    c = P.mean(0)
    rows = [P - d * 0.004]
    for depth, k in ((0.03, 0.97), (0.07, 0.90), (0.12, 0.78)):
        rows.append(c + (P - c) * k - d * depth)
    grid = np.array(rows)
    mesh.grid_object("Headlight_Housing" + sfx, grid, closed_v=True, cap_u=False,
                     collection=COL, material=house, flip=mirror)
    back = rows[-1]
    nb = len(back)
    verts = list(map(tuple, back)) + [tuple(back.mean(0))]
    faces = [(nb, (i + 1) % nb, i) if not mirror else (nb, i, (i + 1) % nb) for i in range(nb)]
    mesh.object_from_pydata("Headlight_Back" + sfx, verts, faces, COL, house)

    # ---- titanium inner bezel (upper part of the unit, recessed) -----------------
    bz = lens.copy()
    bz.data = lens.data.copy()
    bz.name = "Headlight_Bezel" + sfx
    scene.link(bz, COL)
    bz.data.materials.clear()
    bz.data.materials.append(bezel)
    co = mesh.mesh_arrays(bz)
    cc = co.mean(0)
    co = cc + (co - cc) * 0.92 - d * 0.04
    mesh.set_mesh_arrays(bz, co)
    mesh.shade_smooth(bz, 50)

    # ---- bi-xenon projector (outer) and reflector / turn module (inner) ----------
    def anchor(x, y, z, depth):
        q = _on_skin(surf, np.array([x, s * y, z]), d)
        return q - d * depth

    def bowl(centre, r, name):
        prof = np.array([[r * 1.25, 0.0], [r * 1.18, -0.006], [r * 0.6, -0.03], [r * 0.2, -0.042]])
        ob = mesh.revolve(name + sfx, prof, 48, axis="X", center=(0, 0, 0),
                          collection=COL, material=refl)
        _orient(ob, centre, d)
        return ob

    pc = anchor(0.585, 0.790, 0.682, 0.045)
    pr = 0.031
    bowl(pc, pr, "Headlight_ProjectorBowl")
    t = np.linspace(0, math.pi / 2, 12)
    dome = np.stack([pr * np.cos(t), 0.004 + 0.013 * np.sin(t)], 1)
    ob = mesh.revolve("Headlight_ProjectorLens" + sfx, dome, 48, axis="X",
                      collection=COL, material=ctx.mat("glass_tinted"))
    _orient(ob, pc, d)
    ring = mesh.revolve("Headlight_ProjectorRing" + sfx,
                        np.array([[pr * 1.28, 0.002], [pr * 1.06, 0.008], [pr * 0.98, 0.004]]),
                        48, axis="X", collection=COL, material=ctx.mat("chrome"))
    _orient(ring, pc, d)
    rc = anchor(0.700, 0.640, 0.668, 0.050)
    bowl(rc, 0.026, "Headlight_Reflector")
    # chrome eyebrow blade over the inner module (typical of the 8V xenon unit)
    brow = [anchor(x, y, z, 0.03) for x, y, z in
            ((0.775, 0.50, 0.690), (0.735, 0.60, 0.698), (0.670, 0.69, 0.708),
             (0.610, 0.75, 0.714))]
    mesh.tube_along("Headlight_Brow" + sfx, resample(np.array(brow), 30), 0.0022, sides=8,
                    collection=COL, material=ctx.mat("chrome"))

    # ---- LED DRL light guide: along the lower edge, up the inner end -------------
    H = np.asarray(op.HEADLIGHT_3D, float) * 1e-3
    if mirror:
        H = H * [1, -1, 1]
    lower = np.vstack([H[10:], H[:1]])           # lower outer corner -> inner tip
    cen = H.mean(0)
    guide = cen + (lower - cen) * 0.88
    guide = np.array([_on_skin(surf, g, d) - d * 0.014 for g in guide])
    guide = resample(catmull_rom(guide, 8), 90)
    mesh.tube_along("Headlight_DRL_Guide" + sfx, guide, 0.0042, sides=10, collection=COL,
                    material=led)
    am = guide - d * 0.010
    mesh.tube_along("Headlight_Indicator" + sfx, am, 0.0026, sides=8, collection=COL,
                    material=amber)


def _orient(ob, centre, d):
    """Rotate an object modelled about the +X axis so +X points along d, then
    move it to centre."""
    from mathutils import Matrix, Vector
    q = Vector((1, 0, 0)).rotation_difference(Vector(tuple(d)))
    M = Matrix.Translation(Vector(tuple(centre))) @ q.to_matrix().to_4x4()
    ob.data.transform(M)
    ob.data.update()


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    for mirror in (False, True):
        _unit(ctx, ref, surf, mirror)
    tmp = scene.temp_collection("_tmp_patch")
    for o in list(tmp.objects):
        scene.delete(o)
