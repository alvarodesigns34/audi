"""Xenon plus headlights with LED daytime running light guide (8V pre-facelift).

Layout (from photographs of the 8V xenon unit): bi-xenon projector in the
outer part, a reflector bowl inboard of it, a titanium-grey inner bezel and an
LED light guide running along the lower edge - the characteristic "wave" -
rising at the inner end.  The outer lens is generated from the body surface so
it is flush with the bumper / fender.
"""
from __future__ import annotations

import math

import numpy as np

from ..body import openings as op
from ..body import surftools as st
from ..core import mesh
from ..core.curves import catmull_rom, resample

COL = "Exterior/Lights"


def _outline(surf, mirror=False, n=200):
    pts = np.asarray(op.HEADLIGHT, float) * 1e-3
    if mirror:
        pts = pts * [-1, 1]
    dense = resample(catmull_rom(pts, 6, closed=True), n, closed=True)
    return st.clean_projection(*surf.project(dense, "YZ", side=1))


def _shrink(P, c, k):
    return c + (P - c) * k


def _unit(ctx, ref, surf, mirror):
    sfx = ".R" if mirror else ".L"
    s = -1 if mirror else 1
    lens_m = ctx.mat("lens_clear")
    house = ctx.mat("lamp_housing")
    refl = ctx.mat("reflector")
    bezel = ctx.mat("titanium_grey")
    led = ctx.mat("led_white")
    amber = ctx.mat("led_amber")

    # ---- outer lens (body-flush) ------------------------------------------------
    outline = np.asarray(op.HEADLIGHT, float) * 1e-3
    if mirror:
        outline = outline * [-1, 1]
    lens = st.patch(ref, outline, "YZ", 0.35, 1.0, "Headlight_Lens" + sfx, COL, lens_m)
    st.offset(lens, 0.0006)
    mesh.solidify(lens, 0.003, offset=-1.0)
    mesh.shade_smooth(lens, 60)

    # ---- housing bucket -------------------------------------------------------------
    P, N = _outline(surf, mirror)
    c = P.mean(0)
    rows = [P - np.array([0.004, 0, 0])]
    for d, k in ((0.03, 0.97), (0.07, 0.90), (0.11, 0.80)):
        q = _shrink(P, c, k)
        q[:, 0] = P[:, 0] - d
        rows.append(q)
    grid = np.array(rows)
    hb = mesh.grid_object("Headlight_Housing" + sfx, grid, closed_v=True, cap_u=False,
                          collection=COL, material=house, flip=mirror)
    # back cap
    back = rows[-1]
    verts = list(map(tuple, back)) + [tuple(back.mean(0))]
    nb = len(back)
    faces = [(nb, (i + 1) % nb, i) if not mirror else (nb, i, (i + 1) % nb) for i in range(nb)]
    mesh.object_from_pydata("Headlight_Back" + sfx, verts, faces, COL, house)

    # ---- titanium inner bezel (upper part of the unit) ------------------------------
    bz = st.patch(ref, outline, "YZ", 0.35, 1.0, "Headlight_Bezel" + sfx, COL, bezel)
    co = np.array([v.co[:] for v in bz.data.vertices])
    cc = co.mean(0)
    co = cc + (co - cc) * np.array([1.0, 0.94, 0.86])
    co[:, 0] -= 0.045
    bz.data.vertices.foreach_set("co", co.ravel())
    bz.data.update()
    mesh.shade_smooth(bz, 50)

    # ---- bi-xenon projector (outer) and reflector bowl (inner) -----------------------
    def lamp(y, z, r, name):
        p, n = surf.project([(y, z)], "YZ", side=1)
        x = p[0][0] - 0.05 if p[0] is not None else 0.6
        # chrome cone reflector ring
        prof = np.array([[r * 1.25, 0.0], [r * 1.18, -0.006], [r * 0.6, -0.03], [r * 0.2, -0.04]])
        cone = mesh.revolve(name + "_Bowl" + sfx, prof,
                            48, axis="X", center=(x, y, z), collection=COL, material=refl)
        return x, cone

    # projector: polished ring + dark glass lens dome
    py, pz, pr = s * 0.785, 0.646, 0.030
    x, _ = lamp(py, pz, pr, "Headlight_Projector")
    t = np.linspace(0, math.pi / 2, 12)
    dome = np.stack([pr * np.cos(t), x + 0.004 + 0.012 * np.sin(t)], 1)
    mesh.revolve("Headlight_ProjectorLens" + sfx, dome, 48, axis="X", center=(0, py, pz),
                 collection=COL, material=ctx.mat("glass_tinted"))
    ring = mesh.revolve("Headlight_ProjectorRing" + sfx,
                        np.array([[pr * 1.25, x + 0.004], [pr * 1.05, x + 0.008],
                                  [pr * 0.98, x + 0.004]]), 48, axis="X",
                        center=(0, py, pz), collection=COL, material=ctx.mat("chrome"))
    lamp(s * 0.672, 0.648, 0.026, "Headlight_Reflector")

    # ---- LED DRL light guide along the lower edge and up the inner end -----------
    # lower edge = outline points below the local mid-line
    lower = []
    for p in P:
        yy, zz = abs(p[1]), p[2]
        z_mid = np.interp(yy, [0.53, 0.60, 0.70, 0.80, 0.88], [0.650, 0.640, 0.640, 0.645, 0.660])
        if zz < z_mid - 0.008 or yy < 0.56:
            lower.append(p)
    lower = np.array(lower)
    order = np.argsort(np.abs(lower[:, 1]))
    lower = lower[order]
    guide = _shrink(lower, c, 0.93)
    guide[:, 0] -= 0.012
    guide = resample(guide, 80)
    mesh.tube_along("Headlight_DRL_Guide" + sfx, guide, 0.0042, sides=10, collection=COL,
                    material=led)
    # amber turn signal LEDs behind the guide (pre-facelift: integrated)
    am = guide.copy()
    am[:, 0] -= 0.012
    mesh.tube_along("Headlight_Indicator" + sfx, am, 0.0025, sides=8, collection=COL,
                    material=amber)


def build(ctx):
    ref = ctx.objects["skin_ref"]
    surf = st.Surface(ref)
    for mirror in (False, True):
        _unit(ctx, ref, surf, mirror)
