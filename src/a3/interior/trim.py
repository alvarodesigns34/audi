"""Cabin trim: carpet with transmission tunnel and toe board, floor mats with
edging, headliner, A/B/C/D pillar trims, sill trims, rear side (quarter)
trims, luggage compartment cover.  All surfaces follow ``layout`` so they can
be refitted to the body shell later.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from ..core.curves import smoothstep
from . import _geo as g
from . import layout

COL = "Interior/Trim"


def floor_z(L, x, y):
    """Carpet height at (x, y): flat pan, rounded tunnel, toe board ramp,
    sill rise at the sides, rear seat riser."""
    fz = L.floor_z
    ay = abs(y)
    hw = L.tunnel_w / 2
    tun = L.tunnel_h * (1 - smoothstep(hw - 0.05, hw + 0.035, ay))
    # tunnel narrows/lowers toward the rear seat (exhaust tunnel), E
    tun *= 1 - 0.35 * smoothstep(-1.9, -2.3, x)
    z = fz + tun
    # toe board: 45 deg ramp from the heel area up to the bulkhead (E)
    z = np.maximum(z, fz + (x - (L.toe_board_x - 0.17)) * 1.15)
    # sides rise into the sill trims
    z += 0.10 * smoothstep(0.60, 0.70, ay)
    # under the rear bench: raised floor (fuel tank)
    z = np.maximum(z, fz + 0.12 * smoothstep(-2.38, -2.46, x))
    return z


def _carpet(ctx, L):
    xs = np.concatenate([np.linspace(-0.45, -0.75, 12), np.linspace(-0.76, -2.55, 72)])
    ys = np.linspace(-0.72, 0.72, 97)
    pts = np.zeros((len(xs), len(ys), 3))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            z = floor_z(L, x, y)
            z = min(z, 0.62)
            pts[i, j] = (x, y, z)
    ob = mesh.grid_object("Trim_Carpet", pts, collection=COL, material=ctx.mat("carpet"), smooth=False)
    mesh.recalc_normals(ob)
    # make sure the normals face up
    if ob.data.polygons[len(ob.data.polygons) // 2].normal.z < 0:
        ob.data.flip_normals()
    mesh.shade_smooth(ob, 60)
    ctx.register("carpet", ob)
    return ob


def _mats(ctx, L):
    """Four carpet mats with rubber-edged binding, 8 mm thick (front mats wrap
    up the toe board a little)."""
    from ..core.curves import rounded_polygon
    specs = [
        ("Mat_FL", 1, (-0.70, -1.30), (0.17, 0.60), 0.06),
        ("Mat_FR", -1, (-0.66, -1.30), (0.17, 0.60), 0.06),
        ("Mat_RL", 1, (-1.98, -2.36), (0.17, 0.60), 0.05),
        ("Mat_RR", -1, (-1.98, -2.36), (0.17, 0.60), 0.05),
    ]
    for nm, s, (x0, x1), (y0, y1), r in specs:
        # build as a grid draped on the floor (inside the outline)
        nx, ny = 40, 26
        X = np.linspace(x0, x1, nx)
        Y = np.linspace(s * y0, s * y1, ny)
        pts = np.zeros((nx, ny, 3))
        for i, x in enumerate(X):
            for j, y in enumerate(Y):
                pts[i, j] = (x, y, floor_z(L, x, y) + 0.006)
        mat = mesh.grid_object(nm, pts, collection=COL, material=ctx.mat("carpet"), smooth=False)
        mesh.solidify(mat, 0.006, offset=1.0)
        mesh.add_bevel(mat, 0.003, segments=2, angle_deg=40)
        mesh.recalc_normals(mat)
        mesh.shade_smooth(mat, 50)
        # binding (edging) around the perimeter
        edge = np.array([(x, y, floor_z(L, x, y) + 0.008) for x, y in
                         rounded_polygon([(x0 - 0.004, s * (y0 - 0.004)), (x0 - 0.004, s * (y1 + 0.004)),
                                          (x1 + 0.004, s * (y1 + 0.004)), (x1 + 0.004, s * (y0 - 0.004))],
                                         0.004, 3)])
        from ..core.curves import resample
        edge = resample(edge, 160, closed=True)
        g.tube(nm + "_Binding", edge, 0.0055, 8, COL, ctx.mat("mat_edge"), closed=True)
        # heel pad on the driver mat
        if nm == "Mat_FL":
            hp = np.array([(x, y, floor_z(L, x, y) + 0.0135) for x, y in
                           rounded_polygon([(-0.74, 0.28), (-0.74, 0.46), (-0.92, 0.46), (-0.92, 0.28)],
                                           0.02, 4)])
            V = np.vstack([hp, hp.mean(0)[None]])
            F = [(i, (i + 1) % len(hp), len(hp)) for i in range(len(hp))]
            pad = g.mk("Mat_FL_HeelPad", V, F, COL, ctx.mat("rubber_pad"), smooth=None)
            mesh.solidify(pad, 0.003, offset=-1.0)
            # ribs
            rb = g.Batch("Mat_FL_HeelPad_Ribs", COL, ctx.mat("rubber_pad"))
            for k in range(8):
                xx = -0.75 - k * 0.022
                v, f = g.box_verts((xx, 0.37, floor_z(L, xx, 0.37) + 0.0145), (0.003, 0, 0), (0, 0.08, 0),
                                   (0, 0, 0.0015))
                rb.add(v, f)
            rb.build()


def _headliner(ctx, L):
    """Domed headliner from the windscreen header to the tailgate, edges
    rolling down into the side rails."""
    xs = np.linspace(L.ws_top[0] + 0.02, L.d_pillar_x[1] - 0.02, 70)
    ys = np.linspace(-1, 1, 61)
    pts = np.zeros((len(xs), len(ys), 3))
    for i, x in enumerate(xs):
        for j, t in enumerate(ys):
            yw = L.roof_side_y + 0.035
            y = t * yw
            z = float(L.roof_z(x, y))
            # rolls down at the side rails (grab handle area) and at the front header
            z -= 0.05 * smoothstep(0.80, 1.0, abs(t)) ** 1.5
            z -= 0.03 * smoothstep(L.ws_top[0] - 0.06, L.ws_top[0] + 0.02, x)
            z -= 0.03 * smoothstep(L.d_pillar_x[1] + 0.10, L.d_pillar_x[1] - 0.02, x)
            pts[i, j] = (x, y, z)
    ob = mesh.grid_object("Trim_Headliner", pts, collection=COL, material=ctx.mat("headliner"), smooth=False)
    mesh.recalc_normals(ob)
    if ob.data.polygons[len(ob.data.polygons) // 2].normal.z > 0:
        ob.data.flip_normals()
    mesh.shade_smooth(ob, 60)
    # front console for the interior lights (8V: map lights + SOS-less panel)
    xh = L.ws_top[0] - 0.09
    zr = float(L.roof_z(xh, 0.0))
    g.rbox("Trim_RoofConsole", (0.16, 0.20, 0.022), (xh, 0, zr - 0.011), 0.008, 3, COL,
           ctx.mat("black_satin"))
    for s in (1, -1):
        g.rbox(f"Trim_RoofConsole_Lens_{'L' if s > 0 else 'R'}", (0.050, 0.060, 0.004),
               (xh - 0.01, s * 0.050, zr - 0.0225), 0.002, 2, COL, ctx.mat("lens_clear"))
    # rear dome light
    xr = -2.40
    zr = float(L.roof_z(xr, 0.0))
    g.rbox("Trim_RearDomeLight", (0.08, 0.14, 0.012), (xr, 0, zr - 0.006), 0.005, 2, COL,
           ctx.mat("lens_clear"))
    return ob


def _pillar(ctx, name, path, widths, depth, mat, out_dir):
    """Pillar trim: a crowned strip swept along path, its width varying,
    bulging into the cabin (out_dir = unit vector toward the body side)."""
    path = np.asarray(path, float)
    n = len(path)
    t = np.gradient(path, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    secs = []
    nv = 14
    for i in range(n):
        o = np.asarray(out_dir[i] if np.ndim(out_dir) == 2 else out_dir, float)
        o = o - np.dot(o, t[i]) * t[i]
        o /= np.linalg.norm(o)
        side = np.cross(t[i], o)
        w = widths[i]
        sec = []
        for k in range(nv):
            a = math.pi * k / (nv - 1)
            sec.append(path[i] + side * (w / 2) * math.cos(a) - o * depth * max(math.sin(a), 0.0) ** 0.5)
        sec.append(path[i] - side * (w / 2) + o * 0.01)
        sec.append(path[i] + side * (w / 2) + o * 0.01)
        secs.append(sec)
    ob = mesh.grid_object(name, np.array(secs), closed_v=True, collection=COL, material=mat,
                          smooth=False, cap_u=True)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 50)
    return ob


def _pillars(ctx, L):
    hl = ctx.mat("headliner")
    for s, nm in ((1, "L"), (-1, "R")):
        # A pillar: from the dash corner up along the screen edge to the roof rail
        ax, ay, az = L.a_pillar_base
        top = (L.ws_top[0] + 0.03, s * (L.roof_side_y + 0.02), L.ws_top[1] - 0.02)
        P = np.array([(ax + (top[0] - ax) * u, s * (ay + (abs(top[1]) - ay) * u),
                       az + (top[2] - az) * u) for u in np.linspace(0, 1, 24)])
        W = np.linspace(0.085, 0.065, 24)
        _pillar(ctx, f"Trim_APillar_{nm}", P, W, 0.020, hl, (0.15, s, 0.30))
        # B pillar upper (belt -> roof) and lower (floor -> belt, between the doors)
        bx = L.b_pillar_x
        P = np.array([(bx, s * (0.700 - 0.08 * u ** 1.3), 1.00 + (float(L.roof_z(bx, 0.6)) - 0.05 - 1.00) * u)
                      for u in np.linspace(0, 1, 18)])
        _pillar(ctx, f"Trim_BPillar_Upper_{nm}", P, np.linspace(0.105, 0.080, 18), 0.030, hl, (0, s, 0))
        P = np.array([(bx, s * 0.712, z) for z in np.linspace(0.30, 1.01, 12)])
        _pillar(ctx, f"Trim_BPillar_Lower_{nm}", P, np.full(12, 0.090), 0.025, ctx.mat("hard_plastic"),
                (0, s, 0))
        # belt height adjuster rail on the B pillar
        g.rbox(f"Trim_BPillar_BeltAdjuster_{nm}", (0.03, 0.012, 0.09),
               (bx, s * 0.655, 1.14), 0.004, 2, COL, ctx.mat("black_satin"))
        # C pillar (behind the rear door) up to the roof
        c0, c1 = L.c_pillar_x
        P = np.array([(c0 + (c1 - c0) * u, s * (0.695 - 0.075 * u ** 1.2), 1.03 + (1.25 - 1.03) * u)
                      for u in np.linspace(0, 1, 18)])
        _pillar(ctx, f"Trim_CPillar_{nm}", P, np.linspace(0.20, 0.16, 18), 0.035, hl, (0, s, 0.2))
        # D pillar at the tailgate
        d0, d1 = L.d_pillar_x
        P = np.array([(d0 + (d1 - d0) * u, s * (0.66 - 0.07 * u), 0.98 + (1.24 - 0.98) * u)
                      for u in np.linspace(0, 1, 16)])
        _pillar(ctx, f"Trim_DPillar_{nm}", P, np.linspace(0.12, 0.10, 16), 0.03, hl, (-0.4, s, 0))
        # rear quarter trim (beside the rear seat back / luggage area)
        xs = np.linspace(L.rear_door_x[1] - 0.01, d0 + 0.02, 24)
        zs = np.linspace(0.40, 1.03, 20)
        pts = np.array([[(x, s * (0.685 - 0.04 * smoothstep(0.85, 1.03, z)
                                  + 0.02 * (1 - smoothstep(0.40, 0.50, z))), z) for z in zs] for x in xs])
        q = mesh.grid_object(f"Trim_Quarter_{nm}", pts, collection=COL, material=ctx.mat("hard_plastic"),
                             smooth=False)
        mesh.solidify(q, 0.004, offset=-1.0 if s > 0 else 1.0)
        mesh.recalc_normals(q)
        mesh.shade_smooth(q, 50)
        # sill trims (inner door sills) with aluminium S line scuff plates on top
        for (x0, x1), tag in ((L.front_door_x, "F"), (L.rear_door_x, "R")):
            x0_, x1_ = x0 - 0.02, x1 + 0.02
            sill = g.rbox(f"Trim_Sill_{tag}{nm}", (x0_ - x1_, 0.07, 0.10), ((x0_ + x1_) / 2, s * 0.715, 0.29),
                          0.015, 3, COL, ctx.mat("hard_plastic"))
            plate = g.rbox(f"Trim_ScuffPlate_{tag}{nm}", (x0_ - x1_ - 0.06, 0.055, 0.004),
                           ((x0_ + x1_) / 2, s * 0.722, 0.342), 0.0015, 2, COL, ctx.mat("aluminium_brushed"))
            if tag == "F":
                t = g.text_mesh(f"Trim_ScuffPlate_{tag}{nm}_Logo", "S line", size=0.016, col=COL,
                                mat=ctx.mat("black_satin"), extrude=0.0003)
                t.data.transform(g.frame(((x0_ + x1_) / 2, s * 0.722, 0.344), (0, 0, 1), (-1, 0, 0) if s > 0 else (-1, 0, 0)))


def _parcel_shelf(ctx, L):
    """Luggage compartment cover behind the rear backrest."""
    x0 = L.rear_back_top[0] - 0.05
    x1 = L.d_pillar_x[0] + 0.02
    nx, ny = 20, 30
    pts = np.zeros((nx, ny, 3))
    for i, x in enumerate(np.linspace(x0, x1, nx)):
        for j, y in enumerate(np.linspace(-0.62, 0.62, ny)):
            pts[i, j] = (x, y, 1.005 + 0.01 * (x - x0) / (x1 - x0))
    sh = mesh.grid_object("Trim_ParcelShelf", pts, collection=COL, material=ctx.mat("carpet"), smooth=False)
    mesh.solidify(sh, 0.008, offset=-1.0)
    mesh.add_bevel(sh, 0.003, 2, 40)
    mesh.recalc_normals(sh)
    mesh.shade_smooth(sh, 50)


def build(ctx):
    L = layout.get(ctx)
    _carpet(ctx, L)
    _mats(ctx, L)
    _headliner(ctx, L)
    _pillars(ctx, L)
    _parcel_shelf(ctx, L)
