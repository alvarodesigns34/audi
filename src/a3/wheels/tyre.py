"""225/40 R18 92Y ultra-high-performance summer tyre (generic, no trademarks).

Wheel-local frame as in rim.py (+Y outboard).  Units: mm in tables, metres out.

* Carcass: surface of revolution of a realistic section (bead, rim protector
  rib, sidewall, rounded shoulder, slightly crowned tread) with the two
  continuous centre ribs and the four circumferential grooves cut straight
  into the section (crisp groove walls).  A coarse inner liner closes it.
* Tread blocks (both shoulders and the inner intermediate rib) are real
  geometry, built per pitch in the unwrapped (s, u) tread plane -- s along
  the circumference, u arc length across the section -- and wrapped onto the
  section with p(s,u,h) = rot(s/R0) * (P(u) - h N(u)).  The pattern is
  asymmetric: open, angled lateral grooves + sipes inboard (water), closed
  lateral grooves with a stiff bridge outboard (cornering).
* Sidewall lettering "225/40 R18 92Y" (+ TUBELESS / RADIAL) in 0.6 mm relief:
  Blender text converted to mesh and bent onto the sidewall.
* Load deflection: the unloaded geometry is kept rotationally symmetric (so
  the wheel can spin in a configurator / driving game) and the static
  deflection to the 306 mm loaded radius is stored as shape key "Loaded"
  (flattened contact patch + sidewall bulge), enabled by default so the car
  stands on the ground.  Set it to 0 for a spinning wheel.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from scipy.interpolate import PchipInterpolator

from .. import spec
from . import builder as B
from . import rim

MM = 1e-3
R0 = spec.TYRE_DIAMETER / 2          # 318.6 C  unloaded radius
R_STAT = spec.TYRE_STATIC_RADIUS      # 306   E  loaded static radius
TREAD_D = 7.5                         # E  new tread depth (UHP summer 7-8 mm)
N_PITCH = 60                          # E  pitches around the circumference
N_SEG = 180                           # carcass revolve segments (sagitta 0.05 mm at R0)
L_PITCH = 2 * math.pi * R0 / N_PITCH

# Outboard half of the outer section (r, y), from the crown to the bead.  E,
# built from 225 section width on 8J (+~4 mm), 90 mm section height, J-flange.
_HALF = [
    (318.6, 0.0), (318.4, 25.0), (317.8, 45.0), (316.9, 62.0), (315.7, 75.0),
    (313.9, 86.0), (311.2, 95.0), (307.4, 102.0), (302.4, 107.4), (296.2, 111.0),
    (289.0, 113.3), (281.0, 114.6), (274.0, 115.0), (267.0, 114.8), (261.5, 114.5),
    (258.2, 115.4), (255.6, 116.9), (253.2, 117.1), (251.0, 115.2), (249.3, 111.6),
    (247.8, 108.3), (245.6, 105.3), (242.6, 103.1), (238.6, 102.15),
    (233.0, 101.85), (229.7, 101.75),
]
# bead base + inner liner (hidden), outboard half, continuing from the toe
_LINER = [(228.9, 99.0), (227.4, 86.0), (232.0, 84.0), (250.0, 88.0), (272.0, 95.0),
          (292.0, 92.0), (303.0, 80.0), (306.5, 55.0), (307.0, 0.0)]

# circumferential layout, u = arc length from the crown centre, + outboard (E)
G1 = (-62.0, -53.0)
R2 = (-53.0, -27.0)
G2 = (-27.0, -16.0)
R3 = (-16.0, 10.0)        # continuous centre rib
G3 = (10.0, 21.0)
R4 = (21.0, 47.0)         # continuous outer rib
G4 = (47.0, 54.0)
SH_IN = (-104.0, -62.0)   # inboard shoulder blocks
SH_OUT = (54.0, 104.0)    # outboard shoulder blocks
FADE = (82.0, 112.0)      # groove base rises back to the surface on the shoulder


class Section:
    """Arc-length parameterised outer section P(u) with normals N(u)."""

    def __init__(self):
        half = np.array(_HALF)
        full = np.vstack([half[::-1] * [1, -1], half[1:]])          # inboard -> outboard
        # dense resample with PCHIP along the polyline parameter
        t = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(full, axis=0), axis=1))])
        fr = PchipInterpolator(t, full[:, 0])
        fy = PchipInterpolator(t, full[:, 1])
        tt = np.linspace(0, t[-1], 4000)
        pts = np.stack([fr(tt), fy(tt)], 1)
        s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
        i0 = np.argmin(np.abs(pts[:, 1]) + (pts[:, 0] < 300) * 1e3)
        self.u = s - s[i0]
        self.pts = pts
        d = np.gradient(pts, axis=0)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        # direction of increasing u runs inboard->outboard: N = outward
        self.n = np.stack([d[:, 1], -d[:, 0]], 1)
        if self.n[i0, 0] < 0:
            self.n = -self.n
        self.umin, self.umax = self.u[0], self.u[-1]

    def P(self, u):
        u = np.asarray(u, float)
        return np.stack([np.interp(u, self.u, self.pts[:, 0]),
                         np.interp(u, self.u, self.pts[:, 1])], -1)

    def N(self, u):
        u = np.asarray(u, float)
        n = np.stack([np.interp(u, self.u, self.n[:, 0]),
                      np.interp(u, self.u, self.n[:, 1])], -1)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)

    def at(self, u, h):
        """section point (r, y) at arc length u, depth h below the surface"""
        return self.P(u) - np.asarray(h)[..., None] * self.N(u)

    def u_of_y_side(self, y):
        """arc length of the outboard sidewall point at lateral y (not used)"""
        raise NotImplementedError


def _smooth(x, a, b):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def fade(u):
    """1 in the tread, -> 0 on the shoulder where grooves run out"""
    au = np.abs(u)
    return 1 - _smooth(au, FADE[0], FADE[1])


def base_depth(u):
    return TREAD_D * fade(u)


# ----------------------------------------------------------------------- carcass
def _side_samples(sec, u0, u1, n=22):
    """curvature-adaptive samples along the sidewall"""
    u = np.linspace(u0, u1, 400)
    n_ = sec.N(u)
    turn = np.concatenate([[0], np.cumsum(np.abs(np.diff(np.unwrap(np.arctan2(n_[:, 1], n_[:, 0])))))])
    arc = (u - u0) / (u1 - u0)
    w = arc + 1.6 * turn / max(turn[-1], 1e-9)
    t = np.linspace(0, w[-1], n)
    return np.interp(t, w, u)


def carcass_profile(sec):
    """Outer section with the groove floor in the tread zone and the two
    continuous ribs standing proud.  Returns list of (r, y)."""
    u_lo, u_hi = -FADE[1], FADE[1]
    us = np.linspace(u_lo, u_hi, 38)
    walls = [R3, R4]
    out = []
    # outer part inboard of the tread zone (bead -> shoulder)
    for u in _side_samples(sec, sec.umin, u_lo)[:-1]:
        out.append(tuple(sec.P(u)))
    # tread zone with walls
    edges = [e for w in walls for e in w]
    us = [x for x in us if min(abs(x - e) for e in edges) > 1.2]
    keys = sorted(set(np.round(us, 4)) | set(edges))
    for u in keys:
        inside = [w for w in walls if w[0] < u < w[1]]
        at_edge = [w for w in walls if abs(u - w[0]) < 1e-6 or abs(u - w[1]) < 1e-6]
        if at_edge:
            w = at_edge[0]
            lo = tuple(sec.at(u, base_depth(u)))
            hi = tuple(sec.at(u, 0.0))
            # rounded rib edge: small chamfer
            if abs(u - w[0]) < 1e-6:
                out += [lo, tuple(sec.at(u + 0.0, 0.8)), tuple(sec.at(u + 0.8, 0.0))]
            else:
                out += [tuple(sec.at(u - 0.8, 0.0)), tuple(sec.at(u, 0.8)), lo]
        elif inside:
            out.append(tuple(sec.at(u, 0.0)))
        else:
            out.append(tuple(sec.at(u, base_depth(u))))
    for u in _side_samples(sec, u_hi, sec.umax)[1:]:
        out.append(tuple(sec.P(u)))
    # hidden liner (outboard toe -> crown -> inboard toe)
    liner = list(_LINER[:3]) + [_LINER[4], _LINER[6], _LINER[8]]
    liner_full = liner + [(r, -y) for r, y in liner[::-1][1:]]
    out += liner_full
    return out


# ----------------------------------------------------------------------- blocks
def _side(u, s0, slope, bow, umid):
    """lateral groove centreline: s(u)"""
    x = u - umid
    return s0 + slope * x + bow * x * x


def block_polys():
    """Tread block polygons for ONE pitch in (s, u) mm (CCW)."""
    polys = []
    L = L_PITCH
    nu = 9
    # --- inboard shoulder: open angled lateral groove (5 mm) + sipe (1.2 mm)
    u = np.linspace(SH_IN[0], SH_IN[1], nu)
    um = 0.5 * (SH_IN[0] + SH_IN[1])
    c1 = _side(u, 0.0, -0.10, 0.0016, um)      # lateral groove centre line
    c2 = c1 + L                                # next pitch
    cs = c1 + 0.52 * L                         # sipe
    gw, sw = 5.2 / 2, 1.2 / 2
    a = np.stack([c1 + gw, u], 1)
    b = np.stack([cs - sw, u], 1)
    polys.append(np.vstack([a, b[::-1]]))
    a = np.stack([cs + sw, u], 1)
    b = np.stack([c2 - gw, u], 1)
    polys.append(np.vstack([a, b[::-1]]))
    # --- inner intermediate rib R2: blocks separated by slanted 1.6 mm sipes
    u = np.linspace(R2[0], R2[1], 5)
    um = 0.5 * (R2[0] + R2[1])
    c1 = _side(u, 0.30 * L, 0.55, 0.0, um)
    c2 = c1 + L
    a = np.stack([c1 + 0.8, u], 1)
    b = np.stack([c2 - 0.8, u], 1)
    polys.append(np.vstack([a, b[::-1]]))
    # --- outboard shoulder: lateral groove (4.5 mm) that closes at u=ub and
    #     continues as a 0.8 mm sipe through the stiff bridge next to G4
    ub = 61.0
    u = np.concatenate([np.linspace(SH_OUT[0], ub - 1.5, 3), np.linspace(ub - 0.5, ub + 1.5, 3),
                        np.linspace(ub + 4.0, SH_OUT[1], nu)])
    um = 0.5 * (ub + SH_OUT[1])
    c1 = _side(u, 0.62 * L, 0.12, -0.0012, um)
    hw = 0.4 + (4.5 / 2 - 0.4) * _smooth(u, ub - 1.0, ub + 1.5)
    a = np.stack([c1 + hw, u], 1)
    b = np.stack([c1 + L - hw, u], 1)
    polys.append(np.vstack([a, b[::-1]]))
    return [B.ccw(np.asarray(q, float)) for q in polys]


def add_block(mb, sec, poly, ds, mat):
    """poly in (s,u) for pitch offset ds; builds top + walls."""
    poly = np.asarray(poly, float).copy()
    poly[:, 0] += ds
    # densify edges to ~4 mm so the wrap follows the curvature
    dense = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        k = max(1, int(np.ceil(np.linalg.norm(b - a) / 6.5)))
        for t in range(k):
            dense.append(a + (b - a) * t / k)
    poly = np.array(dense)

    def wrap(su, h):
        su = np.asarray(su).reshape(-1, 2)
        h = np.broadcast_to(h, len(su))
        ry = sec.at(su[:, 1], h)
        th = su[:, 0] / R0
        return np.stack([ry[:, 0] * np.cos(th), ry[:, 1], ry[:, 0] * np.sin(th)], 1) * MM

    top = mb.add(wrap(poly, 0.0))
    # chamfer ring (0.5 mm) and drafted wall to the groove floor (+0.6 sink)
    p1 = B.offset_closed(poly, 0.45)
    r1 = mb.add(wrap(p1, 0.5))
    mb.loft(top, r1, mat)
    p2 = B.offset_closed(poly, 0.45 + 0.08 * TREAD_D)
    hb = base_depth(p2[:, 1]) + 0.6
    r2 = mb.add(wrap(p2, hb))
    mb.loft(r1, r2, mat)
    inner = B.rect_grid(poly[:, 0].min(), poly[:, 0].max(), poly[:, 1].min(), poly[:, 1].max(), 9.0)
    mb.cdt_fill([poly], [top], inner, lambda p: wrap(p, 0.0), mat, flip=True, min_dist=2.5)


# ----------------------------------------------------------------------- lettering
def sidewall_y(sec):
    """y(r) of the outboard sidewall between the protector and shoulder."""
    u = np.linspace(60, sec.umax, 2000)
    P = sec.P(u)
    sel = (P[:, 0] > 262) & (P[:, 0] < 306) & (P[:, 1] > 0)
    r, y = P[sel, 0], P[sel, 1]
    o = np.argsort(r)
    return lambda rr: np.interp(rr, r[o], y[o])


def text_mesh(body, size, extrude=0.3, resolution=3):
    cu = bpy.data.curves.new("tyre_txt", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = resolution
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new("tyre_txt", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    v = np.array([vv.co[:] for vv in me.vertices])
    f = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    return v, f


def add_text(mb, sec, body, size, rho, psi_c, mat, relief=0.6, flip_bottom=False):
    v, f = text_mesh(body, size, extrude=relief / 2)
    if len(v) == 0:
        return
    ys = sidewall_y(sec)
    tx, ty, tz = v[:, 0], v[:, 1], v[:, 2] + relief / 2   # tz in [0, relief]
    if flip_bottom:
        # text along the lower arc, readable from outside (baseline towards rim)
        psi = psi_c + tx / rho
        rr = rho - ty
    else:
        psi = psi_c - tx / rho
        rr = rho + ty
    yv = ys(rr) - 0.25 + tz          # base sunk 0.25 into the sidewall
    p, q = -rr * np.sin(psi), rr * np.cos(psi)
    pts = np.stack([-p, yv, q], 1) * MM
    base = mb.add(pts)
    for face in f:
        idx = [base[i] for i in face]
        if flip_bottom:
            idx = idx[::-1]
        mb.face(idx, mat)


# ----------------------------------------------------------------------- build
def build_tyre(mb, mat_rubber=0, mat_text=1, detail="high"):
    sec = Section()
    prof = carcass_profile(sec)
    a = 0.5 * sum(prof[i][0] * prof[(i + 1) % len(prof)][1] - prof[(i + 1) % len(prof)][0] * prof[i][1]
                  for i in range(len(prof)))
    rim.revolve_rings(mb, prof, N_SEG, [mat_rubber] * len(prof), True, flip=a > 0)
    polys = block_polys()
    for k in range(N_PITCH):
        for poly in polys:
            add_block(mb, sec, poly, k * L_PITCH, mat_rubber)
    # lettering (outboard sidewall), twice around
    for c in (0.0, math.pi):
        add_text(mb, sec, "225/40 R18 92Y", 15.5, 279.0, c, mat_text)
        add_text(mb, sec, "TUBELESS", 7.0, 281.0, c + math.radians(62), mat_text, 0.45)
        add_text(mb, sec, "RADIAL", 7.0, 281.0, c - math.radians(58), mat_text, 0.45)
    return sec


def add_load_shape_key(ob):
    """Shape key 'Loaded': static deflection to R_STAT on a flat floor."""
    me = ob.data
    if me.shape_keys is None:
        ob.shape_key_add(name="Basis", from_mix=False)
    sk = ob.shape_key_add(name="Loaded", from_mix=False)
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) / MM
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    r = np.hypot(x, z)
    phi = np.arctan2(x, -z)                       # 0 = straight down
    c = np.cos(phi)
    # target radius for the crown: flat floor at R_STAT, softened transition
    lim = np.where(c > 0.2, R_STAT / np.maximum(c, 0.2), 1e4)
    k = 3.0
    r_t = -k * np.logaddexp(-R0 / k, -lim / k)    # soft min(R0, floor)
    delta = np.maximum(R0 - r_t, 0)               # crown compression at this phi
    w = np.clip((r - 246.0) / (R0 - 246.0), 0, 1) ** 1.15
    dr = -delta * w
    bulge = 0.30 * delta * np.sin(np.pi * np.clip((r - 246.0) / (R0 - 246.0), 0, 1)) \
        * _smooth(np.abs(y), 60, 100)
    nr = np.maximum(r + dr, 1e-6)
    ex, ez = x / np.maximum(r, 1e-6), z / np.maximum(r, 1e-6)
    newx, newz = nr * ex, nr * ez
    newy = y + np.sign(y) * bulge
    out = np.stack([newx, newy, newz], 1) * MM
    sk.data.foreach_set("co", out.ravel())
    sk.value = 1.0
    return sk
