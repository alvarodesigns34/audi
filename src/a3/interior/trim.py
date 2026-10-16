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
    z += 0.10 * smoothstep(0.62, 0.74, ay)
    # under the rear bench: raised floor (fuel tank)
    z = np.maximum(z, fz + 0.12 * smoothstep(-2.38, -2.46, x))
    return z


def _carpet(ctx, L):
    xs = np.concatenate([np.linspace(-0.45, -0.75, 12), np.linspace(-0.76, -2.55, 72)])
    ys = np.linspace(-0.76, 0.76, 101)
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
    """Domed headliner from the windscreen header to the tailgate: roof skin
    moved down by ``L.liner_drop``, edges rolling down into the side rails just
    inside the side glass tops."""
    P = layout.probe(ctx)
    x0, x1 = L.ws_top[0] + 0.012, L.tailgate_x + 0.02
    xs = np.linspace(x0, x1, 72)
    ys = np.linspace(-1, 1, 61)
    pts = np.zeros((len(xs), len(ys), 3))
    for i, x in enumerate(xs):
        # half width: inside the skin at the roof-rail height (narrows at the tailgate)
        zr = float(L.roof_z(x, L.roof_side_y))
        yw = min(L.roof_side_y + 0.02, P.side_y(x, zr) - 0.035)
        for j, t in enumerate(ys):
            y = t * yw
            z = float(L.roof_z(x, y))
            z -= 0.035 * smoothstep(0.82, 1.0, abs(t)) ** 1.5       # rolls into the side rails
            z -= 0.025 * smoothstep(x0 - 0.06, x0, x)               # header roll
            z -= 0.030 * smoothstep(x1 + 0.10, x1, x)               # tailgate roll
            pts[i, j] = (x, y, z)
    ob = mesh.grid_object("Trim_Headliner", pts, collection=COL, material=ctx.mat("headliner"), smooth=False)
    mesh.recalc_normals(ob)
    if ob.data.polygons[len(ob.data.polygons) // 2].normal.z > 0:
        ob.data.flip_normals()
    mesh.shade_smooth(ob, 60)
    xh = x0 - 0.10
    zr = float(L.roof_z(xh, 0.0))
    g.rbox("Trim_RoofConsole", (0.16, 0.20, 0.022), (xh, 0, zr - 0.011), 0.008, 3, COL,
           ctx.mat("black_satin"))
    for s in (1, -1):
        g.rbox(f"Trim_RoofConsole_Lens_{'L' if s > 0 else 'R'}", (0.050, 0.060, 0.004),
               (xh - 0.01, s * 0.050, zr - 0.0225), 0.002, 2, COL, ctx.mat("lens_clear"))
    xr = -2.30
    zr = float(L.roof_z(xr, 0.0))
    g.rbox("Trim_RearDomeLight", (0.08, 0.14, 0.012), (xr, 0, zr - 0.004), 0.005, 2, COL,
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
        sec.append(path[i] - side * (w / 2) + o * 0.008)
        sec.append(path[i] + side * (w / 2) + o * 0.008)
        secs.append(sec)
    ob = mesh.grid_object(name, np.array(secs), closed_v=True, collection=COL, material=mat,
                          smooth=False, cap_u=True)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 50)
    return ob


def _on_skin(P, pts, s, inset):
    """Move (x, |y|, z) points to |y| = skin - inset on side s."""
    return np.array([(x, s * (P.side_y(x, z) - inset), z) for x, _, z in pts])


def _pillars(ctx, L):
    P = layout.probe(ctx)
    hl = ctx.mat("headliner")
    for s, nm in ((1, "L"), (-1, "R")):
        # A pillar: from the dash corner up along the screen edge to the header
        a0, a1 = np.array(L.a_pillar_base), np.array(L.a_pillar_top)
        pts = np.array([a0 + (a1 - a0) * u for u in np.linspace(0, 1, 24)])
        pts = np.array([(x, s * (P.side_y(x, z) - (0.066 - 0.020 * u)), z)
                        for (x, _, z), u in zip(pts, np.linspace(0, 1, len(pts)))])
        _pillar(ctx, f"Trim_APillar_{nm}", pts, np.linspace(0.080, 0.062, 24), 0.018, hl, (0.15, s, 0.30))
        # B pillar upper (belt -> headliner) and lower (sill -> belt, between the doors)
        bx = L.b_pillar_x
        zb = float(L.belt_z(bx))
        zt = float(L.roof_z(bx, 0.6)) - 0.01
        pts = _on_skin(P, [(bx, 0, z) for z in np.linspace(zb - 0.02, zt, 18)], s, 0.032)
        _pillar(ctx, f"Trim_BPillar_Upper_{nm}", pts, np.linspace(0.100, 0.080, 18), 0.022, hl, (0, s, 0))
        pts = _on_skin(P, [(bx, 0, z) for z in np.linspace(0.30, zb - 0.01, 12)], s, L.door_inset + 0.005)
        _pillar(ctx, f"Trim_BPillar_Lower_{nm}", pts, np.full(12, 0.060), 0.015, ctx.mat("hard_plastic"),
                (0, s, 0))
        g.rbox(f"Trim_BPillar_BeltAdjuster_{nm}", (0.03, 0.010, 0.09),
               (bx, s * (P.side_y(bx, 1.15) - 0.058), 1.15), 0.004, 2, COL, ctx.mat("black_satin"))
        # C pillar divider between the rear door window and the quarter light
        c0, c1 = L.c_pillar_x
        z0c = float(L.belt_z(c0))
        pts = [(c0 + (c1 - c0) * u, 0, z0c + (float(L.roof_z(c1, 0.6)) - 0.01 - z0c) * u)
               for u in np.linspace(0, 1, 16)]
        _pillar(ctx, f"Trim_CPillar_{nm}", _on_skin(P, pts, s, 0.030), np.full(16, 0.075), 0.018, hl,
                (0, s, 0.2))
        # D pillar: wide trim from the quarter-light rear edge back to the tailgate
        dl = np.array(L.dlo_rear)
        pts = [(x - 0.060, 0, z) for x, z in dl if z < 1.30]
        dp = _pillar(ctx, f"Trim_DPillar_{nm}", _on_skin(P, pts, s, 0.055),
                     np.linspace(0.12, 0.09, len(pts)), 0.020, hl, (0, s, 0.1))
        g.keep_inside(ctx, dp, 0.008)
        # rear quarter trim below the belt (beside the rear backrest / luggage area)
        xs = np.linspace(L.quarter_x[0], L.quarter_x[1], 26)
        rows = []
        for x in xs:
            b = float(L.belt_z(x))
            col_ = []
            for z in np.linspace(0.40, b, 20):
                y = P.side_y(x, min(z, b - 0.05)) - (L.door_inset - 0.015)
                t = smoothstep(b - 0.04, b, z)
                y = y * (1 - t) + (P.side_y(x, b + 0.008) - L.glass_clear) * t
                col_.append((x, s * y, z))
            rows.append(col_)
        q = mesh.grid_object(f"Trim_Quarter_{nm}", np.array(rows), collection=COL,
                             material=ctx.mat("hard_plastic"), smooth=False)
        mesh.solidify(q, 0.004, offset=-1.0 if s > 0 else 1.0)
        mesh.recalc_normals(q)
        mesh.shade_smooth(q, 50)
        # sill trims (inner door sills) with aluminium S line scuff plates on top
        for (x0, x1), tag in ((L.front_door_x, "F"), ((L.rear_door_x[0], -2.17), "R")):
            x0_, x1_ = x0 - 0.01, x1 + 0.01
            ys = P.side_y((x0 + x1) / 2, 0.30) - 0.165
            g.rbox(f"Trim_Sill_{tag}{nm}", (x0_ - x1_, 0.08, 0.10), ((x0_ + x1_) / 2, s * ys, 0.29),
                   0.015, 3, COL, ctx.mat("hard_plastic"))
            g.rbox(f"Trim_ScuffPlate_{tag}{nm}", (x0_ - x1_ - 0.06, 0.060, 0.004),
                   ((x0_ + x1_) / 2, s * (ys + 0.005), 0.342), 0.0015, 2, COL, ctx.mat("aluminium_brushed"))
            if tag == "F":
                t = g.text_mesh(f"Trim_ScuffPlate_{tag}{nm}_Logo", "S line", size=0.016, col=COL,
                                mat=ctx.mat("black_satin"), extrude=0.0003)
                t.data.transform(g.frame(((x0_ + x1_) / 2, s * (ys + 0.005), 0.344), (0, 0, 1), (-1, 0, 0)))


def _parcel_shelf(ctx, L):
    """Luggage compartment cover behind the rear backrest."""
    x0 = L.rear_back_top[0] - 0.05
    x1 = L.tailgate_x + 0.03
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
