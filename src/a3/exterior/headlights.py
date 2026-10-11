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


def _shrink(P, d, k_mm, c=None):
    """Offset a closed loop inwards by k_mm in the plane normal to d."""
    c = P.mean(0) if c is None else c
    lat = c - P
    lat -= np.outer(lat @ d, d)
    lat /= np.linalg.norm(lat, axis=1)[:, None] + 1e-12
    # smooth the offset direction (corners)
    for _ in range(4):
        lat = (np.roll(lat, 1, 0) + 2 * lat + np.roll(lat, -1, 0)) / 4
        lat /= np.linalg.norm(lat, axis=1)[:, None] + 1e-12
    return P + lat * k_mm * 1e-3


def _band(name, outer, inner, col, mat, flip=False):
    """Closed ring surface between two loops with the same point count."""
    g = np.array([outer, inner])
    return mesh.grid_object(name, g, closed_v=True, collection=col, material=mat, flip=flip)


def _unit(ctx, ref, surf, mirror):
    """Xenon plus unit (8V pre-facelift, photos yellow.jpg / sline_front.jpg):
    dark border round the whole lens, a white light-guide channel (LED daytime
    running light) following the lower edge and both ends, a thin chrome rim
    inside it, a recessed dark-grey bezel with the bi-xenon projector at the
    outer end and a horizontal chrome blade over the inner reflector.
    Depths behind the lens E."""
    sfx = ".R" if mirror else ".L"
    s = -1 if mirror else 1
    d = op.headlight_dir(mirror)
    tmp = scene.temp_collection("_tmp_patch")

    # ---- outer lens (body-flush) ------------------------------------------------
    cut = op.headlight_cutter("HL_cut" + sfx, surf, tmp, mirror=mirror, depth_in=0.05,
                              depth_out=0.05)
    lens = st.patch_with_cutter(ref, cut, "Headlight_Lens" + sfx, COL, ctx.mat("lens_clear"))
    st.offset(lens, 0.0006)
    mesh.solidify(lens, 0.003, offset=-1.0)
    mesh.shade_smooth(lens, 60)

    P = op.headlight_outline(surf, mirror, n=240)
    if mirror:
        P = P[::-1]
    c = P.mean(0)
    # ---- housing: border band + bucket back -------------------------------------
    b0 = P - d * 0.004
    b1 = _shrink(P, d, 7.0, c) - d * 0.012
    _band("Headlight_Border" + sfx, b0, b1, COL, ctx.mat("lamp_border"))
    rows = [b0, P - d * 0.03, c + (P - c) * 0.92 - d * 0.075, c + (P - c) * 0.80 - d * 0.12]
    mesh.grid_object("Headlight_Housing" + sfx, np.array(rows), closed_v=True, collection=COL,
                     material=ctx.mat("lamp_housing"))
    back = rows[-1]
    nb = len(back)
    verts = list(map(tuple, back)) + [tuple(back.mean(0))]
    faces = [(nb, i, (i + 1) % nb) for i in range(nb)]
    mesh.object_from_pydata("Headlight_Back" + sfx, verts, faces, COL, ctx.mat("lamp_housing"))

    # ---- white light-guide channel (DRL) ------------------------------------------
    g0 = b1
    g1 = _shrink(P, d, 21.0, c) - d * 0.022
    guide = _band("Headlight_DRL_Channel" + sfx, g0, g1, COL, ctx.mat("lamp_guide_white"))
    # the top run of the channel is covered by the bezel: keep the white band only
    # along the lower edge and up both ends (faces whose centre is below the
    # straight line joining the two ends' upper corners)
    H = np.asarray(op.HEADLIGHT_3D, float) * 1e-3 * [1, s, 1]
    zt = lambda y: np.interp(abs(y), [0.44, 0.60, 0.75, 0.86], [0.684, 0.700, 0.716, 0.722])
    bi = mesh.material_index(guide, ctx.mat("lamp_bezel_grey"))
    for f in guide.data.polygons:
        cc = f.center
        if cc.z > zt(cc.y) - 0.006 and 0.52 < abs(cc.y) < 0.80:
            f.material_index = bi
    # LED strip inside the channel (emissive in the viewer's lights mode)
    mid = _shrink(P, d, 14.0, c) - d * 0.019
    keep = np.array([not (p[2] > zt(p[1]) - 0.004 and 0.52 < abs(p[1]) < 0.80) for p in mid])
    run = _longest(mid, keep)
    if len(run) > 10:
        mesh.tube_along("Headlight_DRL_LED" + sfx, resample(run, 120), 0.0018, sides=8,
                        collection=COL, material=ctx.mat("led_white"))
    # thin chrome rim inside the channel
    r0 = g1
    r1 = _shrink(P, d, 24.0, c) - d * 0.026
    _band("Headlight_ChromeRim" + sfx, r0, r1, COL, ctx.mat("chrome"))
    # recessed dark-grey bezel filling the inside
    in_loop = r1
    rows = [in_loop, c + (in_loop - c) * 0.85 - d * 0.03, c + (in_loop - c) * 0.6 - d * 0.045]
    mesh.grid_object("Headlight_Bezel" + sfx, np.array(rows), closed_v=True, collection=COL,
                     material=ctx.mat("lamp_bezel_grey"), flip=True)
    cb = rows[-1]
    nb = len(cb)
    verts = list(map(tuple, cb)) + [tuple(cb.mean(0) - d * 0.005)]
    faces = [(nb, (i + 1) % nb, i) for i in range(nb)]
    mesh.object_from_pydata("Headlight_BezelBack" + sfx, verts, faces, COL,
                            ctx.mat("lamp_bezel_grey"))

    # ---- bi-xenon projector (outer end) and inner chrome blade ---------------------
    def anchor(x, y, z, depth):
        q = _on_skin(surf, np.array([x, s * y, z]), d)
        return q - d * depth

    pc = anchor(0.560, 0.800, 0.690, 0.040)
    pr = 0.030
    bowl = mesh.revolve("Headlight_ProjectorBowl" + sfx,
                        np.array([[pr * 1.35, 0.0], [pr * 1.25, -0.006], [pr * 0.7, -0.03],
                                  [pr * 0.2, -0.04]]), 48, axis="X", collection=COL,
                        material=ctx.mat("reflector"))
    _orient(bowl, pc, d)
    t = np.linspace(0, math.pi / 2, 12)
    dome = np.stack([pr * np.cos(t), 0.004 + 0.014 * np.sin(t)], 1)
    ob = mesh.revolve("Headlight_ProjectorLens" + sfx, dome, 48, axis="X", collection=COL,
                      material=ctx.mat("glass_tinted"))
    _orient(ob, pc, d)
    ring = mesh.revolve("Headlight_ProjectorRing" + sfx,
                        np.array([[pr * 1.30, 0.002], [pr * 1.06, 0.009], [pr * 0.98, 0.004]]),
                        48, axis="X", collection=COL, material=ctx.mat("chrome"))
    _orient(ring, pc, d)
    blade = [anchor(x, y, z, 0.034) for x, y, z in
             ((0.770, 0.505, 0.678), (0.735, 0.585, 0.685), (0.690, 0.655, 0.692),
              (0.640, 0.715, 0.698))]
    mesh.sweep_profile("Headlight_Blade" + sfx, resample(catmull_rom(np.array(blade), 8), 30),
                       np.array([[-0.0012, -0.004], [0.0012, -0.004], [0.0012, 0.004],
                                 [-0.0012, 0.004]]), collection=COL, material=ctx.mat("chrome"))
    for k, (x, y, z) in enumerate(((0.745, 0.560, 0.668), (0.700, 0.630, 0.676))):
        q = anchor(x, y, z, 0.040)
        r = mesh.revolve(f"Headlight_Reflector_{k}" + sfx,
                         np.array([[0.018, 0.0], [0.016, -0.006], [0.008, -0.02], [0.0, -0.024]]),
                         32, axis="X", collection=COL, material=ctx.mat("reflector"))
        _orient(r, q, d)
    # amber turn signal LED row behind the chrome blade
    am = np.array([anchor(x, y, z, 0.038) for x, y, z in
                   ((0.765, 0.52, 0.688), (0.725, 0.60, 0.694), (0.680, 0.67, 0.700))])
    mesh.tube_along("Headlight_Indicator" + sfx, resample(catmull_rom(am, 8), 30), 0.0020,
                    sides=8, collection=COL, material=ctx.mat("led_amber"))


def _longest(loop, mask):
    n = len(loop)
    if mask.all():
        return loop
    start = int(np.argmin(mask))
    best, cur = [], []
    for k in range(n):
        i = (start + k) % n
        if mask[i]:
            cur.append(i)
        else:
            best = cur if len(cur) > len(best) else best
            cur = []
    best = cur if len(cur) > len(best) else best
    return loop[best]


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
