"""Door trim panels (8V Sportback, 4 doors).

Each trim is a (x, z) grid whose inboard offset is a smooth field: window sill
roll at the top, upper soft-touch zone, leather insert (raised 4 mm, stitched),
armrest with integrated pull handle, chrome opener in a recess, window
switches, speaker with the 8V aluminium trim ring (rounded triangle) and a
crosshatched grille, map pocket.  Panels are modelled for the left side (+y)
and mirrored for the right.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from ..core.curves import smoothstep
from . import _geo as g
from . import layout

COL = "Interior/Doors"


class DoorShape:
    """Inboard surface y(x, z) of one (left) door trim, derived from the outer
    body skin moved inboard by ``L.door_inset`` (so the trim follows the door's
    curvature and tumblehome) and rolled out to the glass at the belt line."""

    def __init__(self, L, front=True, probe=None):
        self.front = front
        self.L = L
        self.P = probe if probe is not None else layout.probe(None)
        if front:
            self.x0, self.x1 = L.front_door_x       # front (larger x) -> rear
        else:
            self.x0, self.x1 = L.rear_door_x
        self.belt = float(L.belt_z(0.5 * (self.x0 + self.x1)))
        self.zb = L.floor_z + 0.045
        re = np.array(L.rear_door_edge)
        self._rz, self._rx = re[:, 0], re[:, 1]

    def belt_at(self, x):
        return float(self.L.belt_z(x))

    def x_edges(self, z):
        """front / rear x of the trim at height z."""
        if self.front:
            return self.x0, self.x1
        return self.x0, float(np.interp(z, self._rz, self._rx))

    def y(self, x, z):
        """Inboard surface |y| (smaller = further into the cabin)."""
        L, P = self.L, self.P
        b = self.belt_at(x)
        zc = min(z, b - 0.05)
        y = P.side_y(x, zc) - L.door_inset
        y += 0.012 * smoothstep(0.55, 0.30, z)                      # lower panel slightly outboard
        y -= 0.016 * smoothstep(b - 0.15, b - 0.06, z) * (1 - smoothstep(b - 0.04, b, z))  # sill shoulder
        # window-sill cap rolls out to just inside the glass at the belt
        yg = P.side_y(x, b + 0.008) - L.glass_clear
        t = smoothstep(b - 0.040, b + 0.002, z)
        y = y * (1 - t) + yg * t
        xf, xr = self.x_edges(z)
        e = min(abs(x - xf), abs(x - xr))
        y += 0.020 * (1 - smoothstep(0.0, 0.025, e)) * (1 - t)      # rounded front/rear edges
        y += 0.020 * (1 - smoothstep(0.0, 0.025, z - self.zb))      # rounded bottom edge
        return y


def _panel(ctx, D, name):
    nx, nz = 80, 60
    S = np.linspace(0, 1, nx)
    T = np.linspace(0, 1, nz)
    pts = np.zeros((nx, nz, 3))
    for i, s in enumerate(S):
        xm = D.x0 + (D.x1 - D.x0) * s
        for j, t in enumerate(T):
            ztop = D.belt_at(xm) + 0.003
            z = D.zb + (ztop - D.zb) * (1 - (1 - t) ** 1.15)
            xf, xr = D.x_edges(z)
            x = xf + (xr - xf) * s
            z = D.zb + (D.belt_at(x) + 0.003 - D.zb) * (1 - (1 - t) ** 1.15)
            pts[i, j] = (x, D.y(x, z), z)
    ob = mesh.grid_object(name, pts, collection=COL, material=ctx.mat("soft_touch"), smooth=False)
    mesh.recalc_normals(ob)
    # lower half (below the armrest) in hard grained plastic
    idx = mesh.material_index(ob, ctx.mat("hard_plastic"))
    for p in ob.data.polygons:
        if p.center.z < D.zb + 0.30:
            p.material_index = idx
    mesh.shade_smooth(ob, 50)
    return ob


def _insert(ctx, D, name, x0, x1, z0, z1, slope, stitch):
    """Leather insert: raised cushion panel following the trim surface,
    upper edge sloping (8V wedge), with a stitched border."""
    nx, nz = 46, 16
    pts = np.zeros((nx, nz, 3))
    for i, s in enumerate(np.linspace(0, 1, nx)):
        x = x0 + (x1 - x0) * s
        zt = z1 - slope * s
        for j, t in enumerate(np.linspace(0, 1, nz)):
            z = z0 + (zt - z0) * t
            e = min(s, 1 - s) * (x0 - x1)
            ez = min(t, 1 - t) * (zt - z0)
            puff = 0.0045 * smoothstep(0.0, 0.018, e) * smoothstep(0.0, 0.016, ez)
            pts[i, j] = (x, D.y(x, z) - 0.0015 - puff, z)
    ob = mesh.grid_object(name, pts, collection=COL, material=ctx.mat("leather_black"), smooth=False)
    mesh.solidify(ob, 0.003, offset=1.0)
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, 50)
    surf = g.Surface(ob)
    border = []
    m = 0.010
    for s in np.linspace(0, 1, 60):
        border.append((x0 - m + (x1 - x0 + 2 * m) * s, z1 - m - slope * s))
    for t in np.linspace(0, 1, 16)[1:]:
        border.append((x1 + m, z1 - m - slope - (z1 - slope - z0 - 2 * m) * t))
    for s in np.linspace(1, 0, 60)[1:]:
        border.append((x0 - m + (x1 - x0 + 2 * m) * s, z0 + m))
    for t in np.linspace(0, 1, 16)[1:-1]:
        border.append((x0 - m, z0 + m + (z1 - m - z0 - m) * t))
    pts3 = [(x, D.y(x, z) - 0.01, z) for x, z in border]
    g.stitch_on(stitch, surf, pts3, (0, -1, 0))
    return ob


def _grille_mesh(ctx, D, name, inner):
    """Crosshatch strips clipped to the inner outline (diamond mesh)."""
    def contains(pts):
        """Even-odd point-in-polygon test (vectorised)."""
        x, y = pts[:, 0][:, None], pts[:, 1][:, None]
        a, b = inner, np.roll(inner, -1, axis=0)
        cond = (a[:, 1] > y) != (b[:, 1] > y)
        xi = a[:, 0] + (y - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1] + 1e-12)
        return np.sum(cond & (x < xi), axis=1) % 2 == 1
    gr = g.Batch(name, COL, ctx.mat("grille_black"))
    cx, cz = inner.mean(0)
    R = np.max(np.linalg.norm(inner - [cx, cz], axis=1))
    pitch = 0.0055
    for ang in (math.radians(45), math.radians(-45)):
        d = np.array([math.cos(ang), math.sin(ang)])
        nrm = np.array([-d[1], d[0]])
        for k in np.arange(-R, R, pitch):
            ts = np.linspace(-R, R, 120)
            pts = np.array([cx, cz]) + nrm * k + ts[:, None] * d
            inside = contains(pts)
            if not inside.any():
                continue
            idx = np.where(inside)[0]
            a, b = pts[idx[0]], pts[idx[-1]]
            m = (a + b) / 2
            hl = np.linalg.norm(b - a) / 2
            y = D.y(m[0], m[1]) + 0.001
            v, f = g.box_verts((m[0], y, m[1]), (d[0] * hl, 0, d[1] * hl),
                               (0, 0.0008, 0), (nrm[0] * 0.0007, 0, nrm[1] * 0.0007))
            gr.add(v, f)
    return gr.build()


def _door(ctx, L, front, side_name):
    D = DoorShape(L, front, layout.probe(ctx))
    nm = f"Door_{'F' if front else 'R'}{side_name}"
    objs = []
    stitch = g.Batch(f"{nm}_Stitching", COL, ctx.mat("stitch_grey"))
    panel = _panel(ctx, D, f"{nm}_Trim")
    objs.append(panel)
    xf, xr = D.x0, D.x1
    # the front ~0.40 m of the front door sits beside the dash end (which wraps
    # back to x~-0.95), so its visible features start behind that line (E)
    xv = xf - 0.42 if front else xf
    b = D.belt
    # leather insert (wedge: higher at the front)
    if front:
        ins = _insert(ctx, D, f"{nm}_Insert", xv - 0.04, xr + 0.10, b - 0.235, b - 0.115, 0.030, stitch)
    else:
        ins = _insert(ctx, D, f"{nm}_Insert", xf - 0.12, D.x_edges(b - 0.18)[1] + 0.07, b - 0.235,
                      b - 0.125, 0.030, stitch)
    objs.append(ins)
    # armrest: horizontal pad with rounded inboard face; pull cup at its front
    za = b - 0.270 if front else b - 0.275
    za_ = b - 0.270
    a0, a1 = (xv - 0.14, xr + 0.08) if front else (xf - 0.10, D.x_edges(za_)[1] + 0.07)

    def arm_fn(p, a0=a0, a1=a1, za=za):
        q = p.copy()
        u = (q[:, 0] - q[:, 0].min()) / (np.ptp(q[:, 0]) + 1e-9)
        q[:, 2] += 0.010 * u        # rises slightly toward the rear
        return q
    cxa = (a0 + a1) / 2
    ya = D.y(cxa, za) - 0.030
    ya = D.y(cxa, za) - 0.040
    arm = g.pillow(f"{nm}_Armrest", (a0 - a1, 0.095, 0.055), (cxa, ya, za), (3.4, 2.4, 2.6), 14, COL,
                   ctx.mat("leather_black"), fn=arm_fn)
    objs.append(arm)
    surf = g.Surface(arm)
    pts = [(x, ya - 0.040, za + 0.024) for x in np.linspace(a0 - 0.02, a1 + 0.02, 50)]
    g.stitch_on(stitch, surf, pts, (0, -0.4, 1))
    # pull handle: diagonal bar from the armrest front up toward the insert
    p0 = np.array([a0 - 0.030, D.y(a0, za) - 0.055, za + 0.012])
    p1 = np.array([a0 + 0.110, D.y(a0 + 0.10, za + 0.13) - 0.006, za + 0.140])
    path = np.array([p0 + (p1 - p0) * t + np.array([0, -0.020 * math.sin(math.pi * t), 0])
                     for t in np.linspace(0, 1, 18)])
    prof = g.rrect(0.026, 0.036, 0.011, 4)
    hd = g.sweep(f"{nm}_PullHandle", path, prof, COL, ctx.mat("soft_touch"), up=(0, 1, 0))
    objs.append(hd)
    # opener: chrome lever in a dark recess near the top front
    xo, zo = (xv - 0.02, b - 0.080) if front else (xf - 0.11, b - 0.080)
    yo = D.y(xo, zo)
    rec = g.pillow(f"{nm}_Opener_Recess", (0.12, 0.020, 0.040), (xo, yo + 0.004, zo), (3.0, 2.2, 3.0), 10,
                   COL, ctx.mat("black_satin"))
    objs.append(rec)
    lev = g.pillow(f"{nm}_Opener_Lever", (0.095, 0.014, 0.016), (xo - 0.004, yo - 0.007, zo + 0.002),
                   (3.0, 2.4, 2.6), 10, COL, ctx.mat("chrome"))
    objs.append(lev)
    # window switches on the armrest front (driver door: 4 + child lock)
    sw_n = 4 if (front and side_name == "L") else 1
    for k in range(sw_n):
        xs = a0 - 0.020 - (k % 2) * 0.030
        zs = za + 0.024
        ys = ya + (-0.012 if k < 2 else 0.012) if sw_n == 4 else ya
        s = g.rbox(f"{nm}_WindowSwitch_{k}", (0.026, 0.016, 0.010), (xs, ys, zs), 0.003, 2, COL,
                   ctx.mat("black_satin"))
        objs.append(s)
    pnl = g.rbox(f"{nm}_SwitchBezel", (0.075 if sw_n == 4 else 0.040, 0.050, 0.004),
                 (a0 - 0.035, ya, za + 0.0195), 0.004, 2, COL, ctx.mat("piano_black"))
    objs.append(pnl)
    if front and side_name == "L":
        # mirror adjust knob + fold switch, next to the opener (as in photo a)
        km = g.lathe(f"{nm}_MirrorKnob", [(0.0, 0.012), (0.009, 0.012), (0.011, 0.008), (0.011, 0.0),
                                          (0.0, 0.0)],
                     origin=(xo + 0.075, yo - 0.002, zo - 0.010), axis=(0, -1, 0), segments=24, col=COL,
                     mat=ctx.mat("knurl_alu"))
        objs.append(km)
    # speaker (lower front) and map pocket
    r = 0.112 if front else 0.085                  # E 8V door speaker trim ~250 mm wide
    cx = (xv - 0.20) if front else xf - 0.16
    cz = D.zb + (0.255 if front else 0.225)
    from ..core.curves import rounded_polygon
    tri = np.array([(cx + 1.20 * r, cz + 0.62 * r), (cx - 0.95 * r, cz + 0.50 * r),
                    (cx - 0.85 * r, cz - 0.90 * r), (cx + 0.55 * r, cz - 0.90 * r)])
    outline = rounded_polygon(tri, [0.025, 0.05, 0.05, 0.05], 8)
    inner = np.array([cx, cz]) + (outline - [cx, cz]) * 0.88

    def lift(poly, dy):
        return np.array([(x, D.y(x, z) - dy, z) for x, z in poly])
    o_up, i_up = lift(outline, 0.007), lift(inner, 0.007)
    o_dn, i_dn = lift(outline, -0.003), lift(inner, -0.003)
    secs = np.stack([o_dn, o_up, i_up, i_dn], 1)
    ring = mesh.grid_object(f"{nm}_Speaker_Trim", secs, closed_u=True, collection=COL,
                            material=ctx.mat("inlay_alu"), smooth=False)
    mesh.recalc_normals(ring)
    mesh.shade_smooth(ring, 35)
    objs.append(ring)
    back = lift(inner, -0.002)
    V = np.vstack([back, back.mean(0)[None]])
    F = [(i, (i + 1) % len(back), len(back)) for i in range(len(back))]
    objs.append(g.mk(f"{nm}_Speaker_Backing", V, F, COL, ctx.mat("black_textured"), smooth=None))
    objs.append(_grille_mesh(ctx, D, f"{nm}_Speaker_Grille", inner))
    # map pocket: lip running along the bottom behind the speaker
    zp = D.zb + 0.115
    p0x, p1x = D.x_edges(zp)[0] - 0.05, D.x_edges(zp)[1] + 0.05
    pts = np.array([(x, D.y(x, zp) - 0.035, zp) for x in np.linspace(p0x, p1x, 40)])
    pk = g.sweep(f"{nm}_Pocket_Lip", pts, g.rrect(0.014, 0.030, 0.006, 4), COL,
                 ctx.mat("hard_plastic"), up=(0, 0, 1))
    objs.append(pk)
    wall = []
    for x in np.linspace(p0x, p1x, 40):
        wall.append([(x, D.y(x, zz) - 0.035 * smoothstep(D.zb, zp, zz), zz)
                     for zz in np.linspace(D.zb + 0.005, zp, 8)])
    objs.append(mesh.grid_object(f"{nm}_Pocket", np.array(wall), collection=COL,
                                 material=ctx.mat("hard_plastic"), smooth=True))
    stitch_ob = stitch.build()
    if stitch_ob is not None:
        objs.append(stitch_ob)
    return objs


def build(ctx):
    L = layout.get(ctx)
    for front in (True, False):
        objs = _door(ctx, L, front, "L")
        for o in objs:
            if o is None:
                continue
            mesh.mirror_copy_y(o, o.name.replace("_FL", "_FR").replace("_RL", "_RR"), o.users_collection[0])
