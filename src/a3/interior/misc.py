"""Miscellaneous interior parts: interior mirror with sensor cover, sun
visors, seat belts (webbing, latch plates, buckles), roof grab handles,
belt anchors.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from . import _geo as g
from . import layout

COL = "Interior/Misc"


def _mirror(ctx, L):
    """Auto-dimming frameless-look mirror (pre-facelift 8V: black housing,
    thin frame) on a stem from the rain/light sensor cover."""
    x0 = L.ws_top[0] + 0.09          # E foot on the glass below the header
    z0 = L.ws_z(x0) - 0.012
    sens = g.pillow("Mirror_SensorCover", (0.085, 0.065, 0.024), (x0, 0, z0 - 0.004), (2.6, 2.6, 2.4), 10,
                    COL, ctx.mat("black_satin"),
                    fn=lambda p: p @ g.rot_y(math.radians(-20)).T)
    stem_top = np.array([x0 + 0.015, 0, z0 - 0.020])
    head = np.array([x0 + 0.060, 0, z0 - 0.058])
    g.tube("Mirror_Stem", [stem_top, head + np.array([-0.010, 0, 0.004])], 0.0075, 12, COL,
           ctx.mat("black_satin"))
    body = g.pillow("Mirror_Housing", (0.036, 0.245, 0.062), (0, 0, 0), (2.4, 3.6, 3.0), 14, COL,
                    ctx.mat("black_satin"),
                    fn=lambda p: p @ g.rot_y(math.radians(-8)).T @ g.rot_z(math.radians(0)).T + head)
    glass_c = head + np.array([-0.020, 0, 0])
    nrm = np.array([-1, 0, -0.10])
    gl = g.prism("Mirror_Glass", g.rrect(0.232, 0.053, 0.017, 8), 0.0, 0.0012, COL, ctx.mat("mirror"))
    gl.data.transform(g.frame(glass_c, nrm, (0, -1, 0)))
    fr = g.prism("Mirror_Frame", g.rrect(0.238, 0.059, 0.020, 8), -0.002, 0.0006, COL, ctx.mat("piano_black"))
    fr.data.transform(g.frame(glass_c, nrm, (0, -1, 0)))


def _visors(ctx, L):
    """Sun visors folded up against the headliner, with vanity mirror flap
    and the centre clip."""
    xh = L.ws_top[0] - 0.015
    for s, nm in ((1, "L"), (-1, "R")):
        y0, y1 = 0.08, 0.60
        zc = float(L.roof_z(xh - 0.09, 0.3)) - 0.020

        def fn(p, s=s):
            q = p.copy()
            q[:, 2] -= 0.006 * (q[:, 1] / 0.26) ** 2
            return q
        g.pillow(f"Visor_{nm}", (0.175, y1 - y0, 0.026), (xh - 0.095, s * (y0 + y1) / 2, zc),
                     (3.0, 4.0, 2.4), 14, COL, ctx.mat("headliner"), fn=fn)
        # vanity mirror cover (underside) + hinge rod + clip
        g.rbox(f"Visor_{nm}_VanityCover", (0.075, 0.13, 0.003), (xh - 0.095, s * 0.36, zc - 0.0135),
               0.003, 2, COL, ctx.mat("black_satin"))
        g.tube(f"Visor_{nm}_Rod", [(xh - 0.012, s * 0.58, zc + 0.004), (xh - 0.012, s * 0.12, zc + 0.004)],
               0.0055, 10, COL, ctx.mat("black_satin"))
        g.rbox(f"Visor_{nm}_Hinge", (0.030, 0.035, 0.022), (xh - 0.012, s * 0.60, zc + 0.012), 0.006, 2,
               COL, ctx.mat("black_satin"))
        g.rbox(f"Visor_{nm}_Clip", (0.022, 0.020, 0.018), (xh - 0.012, s * 0.065, zc + 0.010), 0.005, 2,
               COL, ctx.mat("black_satin"))


def _ribbon(name, path, normals, width, thick, col, mat):
    """Seat-belt webbing: flat strip along path with given surface normals."""
    path = np.asarray(path, float)
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    nrm = np.asarray(normals, float)
    side = np.cross(t, nrm)
    side /= np.linalg.norm(side, axis=1)[:, None]
    nrm = np.cross(side, t)
    prof = np.array([(-width / 2, -thick / 2), (width / 2, -thick / 2), (width / 2, thick / 2),
                     (-width / 2, thick / 2)])
    pts = np.stack([path + side * a + nrm * b for a, b in prof], 1)
    ob = mesh.grid_object(name, pts, closed_v=True, collection=col, material=mat, smooth=False, cap_u=True)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 30)
    return ob


def _latch(ctx, name, pos, normal, up):
    """Latch plate (tongue): chrome tongue + black plastic grip."""
    M = g.frame(pos, normal, up)
    a = g.rbox(name + "_Grip", (0.060, 0.050, 0.012), (0, 0.010, 0), 0.005, 2, COL, ctx.mat("black_satin"))
    b = g.rbox(name + "_Tongue", (0.026, 0.040, 0.003), (0, -0.030, 0), 0.0015, 2, COL, ctx.mat("chrome"))
    for o in (a, b):
        o.data.transform(M)


def _buckle(ctx, name, pos, direction):
    """Buckle on a short stalk: black housing with red release button."""
    d = g._n(direction)
    M = g.frame(pos, d, (0, 0, 1) if abs(d[2]) < 0.9 else (1, 0, 0))
    h = g.rbox(name, (0.028, 0.045, 0.075), (0, 0, 0), 0.008, 3, COL, ctx.mat("black_satin"))
    b = g.rbox(name + "_Release", (0.016, 0.028, 0.010), (0.0, 0.0, 0.037), 0.003, 2, COL, ctx.mat("badge_red"))
    sl = g.rbox(name + "_Slot", (0.006, 0.034, 0.004), (0.0, 0.0, 0.0385), 0.001, 1, COL, ctx.mat("rubber_seal"))
    st = g.rbox(name + "_Stalk", (0.022, 0.030, 0.12), (0, 0, -0.095), 0.006, 2, COL, ctx.mat("seatbelt"))
    for o in (h, b, sl, st):
        o.data.transform(M)


def _belts(ctx, L):
    web = ctx.mat("seatbelt")
    bx = L.b_pillar_x
    for s, nm in ((1, "L"), (-1, "R")):
        # front: webbing hangs from the B-pillar D-ring down into the lower pillar
        top = np.array([bx + 0.005, s * 0.640, 1.125])
        path = np.array([top + np.array([0.0, 0.0, -0.015 * k]) for k in range(2)]
                        + [np.array([bx + 0.006, s * (0.655 + 0.018 * u), 1.10 - 0.68 * u])
                           for u in np.linspace(0.02, 1, 24)])
        _ribbon(f"Belt_F{nm}_Webbing", path, np.tile((0, -s, 0), (len(path), 1)), 0.048, 0.0012, COL, web)
        g.rbox(f"Belt_F{nm}_DRing", (0.050, 0.020, 0.040), tuple(top + np.array([0, 0, 0.012])), 0.008, 2, COL,
               ctx.mat("black_satin"))
        _latch(ctx, f"Belt_F{nm}_Latch", (bx + 0.004, s * 0.648, 0.86), (0, -s, 0), (0, 0, 1))
        # lower anchor on the sill, behind the seat (rail end)
        g.rbox(f"Belt_F{nm}_Anchor", (0.06, 0.02, 0.03), (bx + 0.05, s * 0.66, 0.30), 0.006, 2, COL,
               ctx.mat("black_satin"))
        # buckle on the inboard side of each front seat
        H = L.h_point(s)
        _buckle(ctx, f"Belt_F{nm}_Buckle", (H[0] - 0.06, s * 0.125, H[2] - 0.030), (0.25, -s * 0.15, 1))
        # rear outer: webbing from the parcel shelf guide down the C pillar side
        rt = np.array([L.rear_back_top[0] - 0.02, s * 0.58, L.rear_back_top[1] + 0.005])
        path = np.array([rt + np.array([0.10 * u, s * 0.06 * u, -0.45 * u]) for u in np.linspace(0, 1, 16)])
        _ribbon(f"Belt_R{nm}_Webbing", path, np.tile((0.4, -s, 0), (len(path), 1)), 0.048, 0.0012, COL, web)
        g.rbox(f"Belt_R{nm}_Guide", (0.05, 0.06, 0.018), tuple(rt + np.array([0.0, 0, 0.004])), 0.006, 2, COL,
               ctx.mat("black_satin"))
        _latch(ctx, f"Belt_R{nm}_Latch", tuple(rt + np.array([0.09, s * 0.055, -0.40])), (1, -s * 0.5, 0.2),
               (0, 0, 1))
    # rear buckles in the bench crease (pairs for outer seats + centre)
    xb = L.rear_cushion_x[1] + 0.03
    zb = L.h_rear[2] - 0.07
    for k, y in enumerate((0.20, 0.13, -0.09, -0.16, -0.22)):
        _buckle(ctx, f"Belt_Rear_Buckle_{k}", (xb, y, zb), (0.6, 0, 1))
    # centre belt from the roof-mounted retractor cover (Sportback: in the backrest) E
    ct = np.array([L.rear_back_top[0] + 0.01, -0.10, L.rear_back_top[1] - 0.01])
    path = np.array([ct + np.array([0.08 * u, 0, -0.30 * u]) for u in np.linspace(0, 1, 10)])
    _ribbon("Belt_RC_Webbing", path, np.tile((1, 0, 0.3), (len(path), 1)), 0.048, 0.0012, COL, web)


def _grab_handles(ctx, L):
    """Folding roof grab handles over the passenger and rear doors."""
    for s, x, nm in ((-1, -1.55, "FR"), (1, -2.45, "RL"), (-1, -2.45, "RR")):
        y = s * (L.roof_side_y + 0.005)
        z = float(L.roof_z(x, y)) - 0.045
        pts = []
        for u in np.linspace(0, 1, 20):
            a = math.pi * u
            pts.append((x + 0.12 * math.cos(a), y - s * 0.03 * math.sin(a), z - 0.035 * math.sin(a)))
        g.sweep(f"Grab_Handle_{nm}", np.array(pts), g.rrect(0.022, 0.014, 0.006, 4), COL,
                ctx.mat("hard_plastic"), up=(0, 0, 1))


def build(ctx):
    L = layout.get(ctx)
    _mirror(ctx, L)
    _visors(ctx, L)
    _belts(ctx, L)
    _grab_handles(ctx, L)
