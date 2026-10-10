"""Brakes and wheel-end hardware behind the wheel (2.0 TDI 110 kW).

Front: ventilated disc 312 x 25 (40 straight vanes visible at the rim of the
disc), single-piston floating caliper (FN3 / TRW type) on a carrier with two
guide pins, pads, dust shield, hub flange + pilot, steering knuckle, outer CV
joint and boot.
Rear: solid disc 272 x 10, floating caliper with integrated electric parking
brake actuator (gearbox + motor behind the housing), dust shield, wheel
carrier.

Wheel-local frame of the LEFT wheels (+Y outboard, +X forward, +Z up), mm in
the tables, metres in the meshes.  Right-hand parts are mirror images (Y -> -Y),
because calipers, knuckles and shields ARE mirrored parts on a car.

Caliper position: on the photos of the S line car the caliper body shows in
the window AHEAD of the hub on both axles (leading position, around axle
height).  That agrees with the MQB layout (steering tie rod behind the axle),
so the calipers are placed at theta = 0 (pointing +X).  Status E/S.
"""
from __future__ import annotations

import math

import numpy as np

from .. import spec
from ..core import mesh as cmesh
from . import builder as B
from .rim import revolve_rings, ET

MM = 1e-3
N_DISC = 120


# -------------------------------------------------------------- primitives
def rounded_rect(a0, a1, b0, b1, rad, nc=3):
    """closed CCW loop in (a,b)"""
    rad = min(rad, 0.49 * (a1 - a0), 0.49 * (b1 - b0))
    pts = []
    for (ca, cb, t0) in ((a1 - rad, b0 + rad, -90), (a1 - rad, b1 - rad, 0),
                         (a0 + rad, b1 - rad, 90), (a0 + rad, b0 + rad, 180)):
        for k in range(nc + 1):
            t = math.radians(t0 + 90 * k / nc)
            pts.append((ca + rad * math.cos(t), cb + rad * math.sin(t)))
    return np.array(pts)


def polar_box(mb, r0, r1, y0, y1, th0, th1, rad, mat, n_th=10, taper=True, rad_end=None):
    """Rounded-rectangle (r,y) section swept round the wheel axis from th0 to
    th1 (radians); ends softened by shrinking the last stations."""
    prof = rounded_rect(r0, r1, y0, y1, rad)
    c = prof.mean(0)
    ths = list(np.linspace(th0, th1, n_th))
    sc_ = [1.0] * n_th
    if taper:
        d = (rad_end or rad) / ((r0 + r1) / 2)
        ths = [th0] + [th0 + d * 0.45] + ths[1:-1] + [th1 - d * 0.45, th1]
        sc_ = [0.80, 0.96] + [1.0] * (n_th - 2) + [0.96, 0.80]
    rings = []
    for th, s in zip(ths, sc_):
        p = c + (prof - c) * s
        rings.append(mb.add(np.stack([p[:, 0] * math.cos(th), p[:, 1], p[:, 0] * math.sin(th)], 1) * MM))
    mb.grid(rings, mat)
    mb.cap(rings[0], mat)
    mb.cap(rings[-1], mat, flip=True)
    return rings


def revolve_local(mb, prof, n, centre_xz, mat, axis=(0, 1, 0), cap0=True, cap1=True,
                  mats=None):
    """Revolve a (rho, h) profile around an axis through (x, ?, z) with direction
    ``axis`` (unit, in the local frame).  h is measured along the axis from the
    point (centre_x, 0, centre_z)."""
    ax = np.asarray(axis, float)
    ax /= np.linalg.norm(ax)
    ref = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 0, 1.0])
    e1 = np.cross(ax, ref)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    o = np.array([centre_xz[0], 0.0, centre_xz[1]])
    th = 2 * math.pi * np.arange(n) / n
    rings = []
    for rho, h in prof:
        pts = o[None] + h * ax[None] + rho * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2)
        rings.append(mb.add(pts * MM))
    for i in range(len(rings) - 1):
        mb.loft(rings[i], rings[i + 1], mats[i] if mats else mat)
    if cap0:
        mb.cap(rings[0], mat)
    if cap1:
        mb.cap(rings[-1], mat, flip=True)
    return rings


def tube(mb, path, radius, mat, sides=10, cap=True):
    path = np.asarray(path, float)
    fr = cmesh.parallel_transport_frames(path, False, (0, 0, 1))
    th = 2 * math.pi * np.arange(sides) / sides
    rad = np.broadcast_to(np.asarray(radius, float), (len(path),))
    rings = []
    for i, (t, nn, bb) in enumerate(fr):
        pts = path[i] + rad[i] * (np.cos(th)[:, None] * nn + np.sin(th)[:, None] * bb)
        rings.append(mb.add(pts * MM))
    mb.grid(rings, mat)
    if cap:
        mb.cap(rings[0], mat)
        mb.cap(rings[-1], mat, flip=True)


def box(mb, centre, size, mat, rot_z=0.0):
    cx, cy, cz = centre
    sx, sy, sz = (s / 2 for s in size)
    v = np.array([[-sx, -sy, -sz], [sx, -sy, -sz], [sx, sy, -sz], [-sx, sy, -sz],
                  [-sx, -sy, sz], [sx, -sy, sz], [sx, sy, sz], [-sx, sy, sz]])
    c, s = math.cos(rot_z), math.sin(rot_z)
    R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])   # rotation about Y (wheel axis)
    v = v @ R.T + np.array(centre)
    i = mb.add(v * MM)
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        mb.face([i[k] for k in f], mat)


def polar_pt(r, th, y):
    return np.array([r * math.cos(th), y, r * math.sin(th)])


# -------------------------------------------------------------- discs
def build_disc_front(mb, m_face, m_hat):
    R_O = spec.BRAKE_FRONT_DISC[0] / 2          # 156  S
    T = spec.BRAKE_FRONT_DISC[1]                # 25   S
    y_out = 46.0 - 20.6                         # E  disc height 45.6 (hat face -> inner face)
    y_in = y_out - T
    plate = 7.5                                 # E  each friction plate
    r_in = 100.0                                # E  friction ring inner radius
    # hat + outboard plate (closed section, outward normals)
    P = [(32.5, 46.0), (77.0, 46.0), (81.0, 45.0), (83.2, 42.5), (84.6, 31.0),
         (87.0, 27.0), (91.0, y_out), (R_O - 0.8, y_out), (R_O, y_out - 0.8),
         (R_O, y_out - plate + 0.6), (R_O - 0.6, y_out - plate), (r_in, y_out - plate),
         (86.0, y_out - plate + 1.0), (79.5, 22.0), (78.4, 40.0), (76.0, 40.0), (32.5, 40.0)]
    mats = [m_hat] * len(P)
    for i in range(6, 10):
        mats[i] = m_face
    _revolve_closed(mb, P, N_DISC, mats)
    # inboard plate
    Q = [(r_in, y_in + plate), (R_O - 0.6, y_in + plate), (R_O, y_in + plate - 0.6),
         (R_O, y_in + 0.8), (R_O - 0.8, y_in), (r_in + 1.0, y_in), (r_in, y_in + 1.0)]
    _revolve_closed(mb, Q, N_DISC, [m_face] * len(Q))
    # vanes
    nv = 40
    for k in range(nv):
        th = 2 * math.pi * (k + 0.5) / nv
        _vane(mb, r_in + 1.5, R_O - 0.4, y_in + plate - 0.4, y_out - plate + 0.4, th, 3.4, 5.6, m_hat)
    return dict(r_out=R_O, y_out=y_out, y_in=y_in, r_pad=(r_in + 4, R_O - 2))


def build_disc_rear(mb, m_face, m_hat):
    R_O = spec.BRAKE_REAR_DISC[0] / 2           # 136 S
    T = spec.BRAKE_REAR_DISC[1]                 # 10  S
    y_out = 46.0 - 28.0                         # E
    y_in = y_out - T
    r_in = 94.0                                 # E
    P = [(32.5, 46.0), (72.0, 46.0), (76.0, 45.0), (78.2, 42.5), (79.4, 26.0),
         (81.5, y_out + 1.6), (85.0, y_out), (R_O - 0.8, y_out), (R_O, y_out - 0.8),
         (R_O, y_in + 0.8), (R_O - 0.8, y_in), (r_in, y_in), (76.5, y_in + 1.0),
         (74.0, 20.0), (73.2, 40.0), (71.0, 40.0), (32.5, 40.0)]
    mats = [m_hat] * len(P)
    for i in range(6, 11):
        mats[i] = m_face
    _revolve_closed(mb, P, N_DISC, mats)
    return dict(r_out=R_O, y_out=y_out, y_in=y_in, r_pad=(r_in + 2, R_O - 2))


def _revolve_closed(mb, P, n, mats):
    a = 0.5 * sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                  for i in range(len(P)))
    revolve_rings(mb, P, n, mats, True, flip=a > 0)


def _vane(mb, r0, r1, y0, y1, th, w0, w1, mat):
    c, s = math.cos(th), math.sin(th)
    t = np.array([-s, 0, c])
    rad = np.array([c, 0, s])
    yv = np.array([0, 1.0, 0])
    v = []
    for (r, w) in ((r0, w0), (r1, w1)):
        for (dy, dt) in ((y0, -w / 2), (y0, w / 2), (y1, w / 2), (y1, -w / 2)):
            v.append(rad * r + yv * dy + t * dt)
    i = mb.add(np.array(v) * MM)
    for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        mb.face([i[k] for k in f], mat)


# -------------------------------------------------------------- calipers
def build_caliper_front(mb, d, m_cal, m_steel, m_pad, th_c=0.0):
    """Single-piston floating caliper, leading position at theta=th_c."""
    ro, yo, yi = d["r_out"], d["y_out"], d["y_in"]
    rp0, rp1 = d["r_pad"]
    rc = 0.5 * (rp0 + rp1)                     # pad / piston centre radius
    half = math.radians(25.0)                  # pad half arc
    # pads (backing plate + lining), both sides
    for side in (1, -1):
        if side > 0:
            y_l0, y_l1 = yo, yo + 10.0
            y_b0, y_b1 = yo + 10.0, yo + 15.5
        else:
            y_l0, y_l1 = yi - 10.0, yi
            y_b0, y_b1 = yi - 15.5, yi - 10.0
        polar_box(mb, rp0 + 1, rp1 - 1, y_l0, y_l1, th_c - half, th_c + half, 3.0, m_pad, 8)
        polar_box(mb, rp0 - 1, rp1 + 4, y_b0, y_b1, th_c - half - 0.05, th_c + half + 0.05, 2.0, m_steel, 8)
    # outboard fingers (two) and bridge over the disc edge
    yf0, yf1 = yo + 15.5, yo + 26.0
    for sgn in (-1, 1):
        a0 = th_c + sgn * math.radians(3.5)
        a1 = th_c + sgn * math.radians(23.0)
        polar_box(mb, rp0 + 4, ro + 22, yf0, yf1, min(a0, a1), max(a0, a1), 6.0, m_cal, 7)
    polar_box(mb, ro + 3.5, ro + 24, yi - 24.0, yf1, th_c - math.radians(24), th_c + math.radians(24),
              8.0, m_cal, 12)
    # inboard housing: body block + piston cylinder (axis // Y)
    polar_box(mb, rp0 + 2, ro + 22, yi - 34.0, yi - 15.5, th_c - math.radians(21),
              th_c + math.radians(21), 9.0, m_cal, 10)
    cx, cz = rc * math.cos(th_c), rc * math.sin(th_c)
    revolve_local(mb, [(31.0, yi - 15.0), (33.5, yi - 20.0), (33.5, yi - 46.0), (30.0, yi - 52.0),
                       (18.0, yi - 54.5)], 32, (cx, cz), m_cal)
    # bleed nipple + hose union on top of the housing
    tp = polar_pt(ro + 18, th_c + math.radians(14), yi - 38)
    revolve_local(mb, [(4.0, 0), (4.0, 7), (2.6, 8), (2.6, 14)], 10, (tp[0], tp[2]), m_steel,
                  axis=(math.cos(th_c + 0.25), 0, math.sin(th_c + 0.25)))
    # carrier: inboard base + two arms over the disc edge at the pad ends
    for sgn in (-1, 1):
        a = th_c + sgn * math.radians(31.0)
        polar_box(mb, rp0 + 6, ro + 13, yi - 22.0, yo + 14.0, a - math.radians(4.5), a + math.radians(4.5),
                  3.0, m_steel, 5)
        # guide pin boss + rubber boot (axis // Y) at the housing ends
        g = polar_pt(ro + 9, th_c + sgn * math.radians(27.5), 0)
        revolve_local(mb, [(7.5, yi - 15.0), (9.0, yi - 18.0), (9.0, yi - 30.0), (7.0, yi - 33.0),
                           (8.5, yi - 36.0), (6.5, yi - 39.0), (5.0, yi - 41.0)], 16, (g[0], g[2]), m_cal)
    polar_box(mb, rp0 - 6, rp0 + 18, yi - 30.0, yi - 18.0, th_c - math.radians(36), th_c + math.radians(36),
              4.0, m_steel, 10)


def build_caliper_rear(mb, d, m_cal, m_steel, m_pad, th_c=0.0):
    """Floating caliper with electric parking brake actuator (TRW EPB type)."""
    ro, yo, yi = d["r_out"], d["y_out"], d["y_in"]
    rp0, rp1 = d["r_pad"]
    rc = 0.5 * (rp0 + rp1)
    half = math.radians(23.0)
    for side in (1, -1):
        if side > 0:
            y_l0, y_l1, y_b0, y_b1 = yo, yo + 9.0, yo + 9.0, yo + 14.0
        else:
            y_l0, y_l1, y_b0, y_b1 = yi - 9.0, yi, yi - 14.0, yi - 9.0
        polar_box(mb, rp0 + 1, rp1 - 1, y_l0, y_l1, th_c - half, th_c + half, 3.0, m_pad, 8)
        polar_box(mb, rp0 - 1, rp1 + 3, y_b0, y_b1, th_c - half - 0.05, th_c + half + 0.05, 2.0, m_steel, 8)
    yf0, yf1 = yo + 14.0, yo + 23.0
    for sgn in (-1, 1):
        a0 = th_c + sgn * math.radians(3.5)
        a1 = th_c + sgn * math.radians(21.0)
        polar_box(mb, rp0 + 3, ro + 19, yf0, yf1, min(a0, a1), max(a0, a1), 5.0, m_cal, 7)
    polar_box(mb, ro + 3, ro + 20, yi - 22.0, yf1, th_c - math.radians(22), th_c + math.radians(22),
              7.0, m_cal, 12)
    polar_box(mb, rp0 + 2, ro + 19, yi - 30.0, yi - 14.0, th_c - math.radians(19),
              th_c + math.radians(19), 8.0, m_cal, 10)
    cx, cz = rc * math.cos(th_c), rc * math.sin(th_c)
    revolve_local(mb, [(26.0, yi - 13.0), (28.5, yi - 18.0), (28.5, yi - 40.0), (26.0, yi - 44.0)],
                  28, (cx, cz), m_cal)
    # EPB: gearbox housing behind the piston + motor parallel to it (below)
    ym = yi - 44.0
    polar_box(mb, rc - 34, rc + 22, ym - 18.0, ym + 1.0, th_c - math.radians(32), th_c + math.radians(14),
              7.0, m_cal, 10)
    mth = th_c - math.radians(22)
    mx, mz = (rc - 6) * math.cos(mth), (rc - 6) * math.sin(mth)
    revolve_local(mb, [(17.5, ym - 4.0), (18.5, ym + 2.0), (18.5, yi + 2.0), (16.0, yi + 6.0),
                       (9.0, yi + 7.0)], 24, (mx, mz), m_cal)
    # electrical connector on the gearbox
    cp = polar_pt(rc + 14, th_c - math.radians(8), ym - 9.0)
    box(mb, (cp[0], cp[1] - 9.0, cp[2]), (16, 14, 11), m_cal, rot_z=th_c)
    for sgn in (-1, 1):
        a = th_c + sgn * math.radians(29.0)
        polar_box(mb, rp0 + 6, ro + 11, yi - 18.0, yo + 12.0, a - math.radians(4.5), a + math.radians(4.5),
                  3.0, m_steel, 5)
        g = polar_pt(ro + 7, th_c + sgn * math.radians(25.5), 0)
        revolve_local(mb, [(6.5, yi - 14.0), (8.0, yi - 17.0), (8.0, yi - 27.0), (6.0, yi - 30.0),
                           (7.5, yi - 32.0), (5.0, yi - 35.0)], 14, (g[0], g[2]), m_cal)


# -------------------------------------------------------------- shield / hub
def build_shield(mb, d, m_steel, th_c=0.0, gap_deg=44.0):
    """Pressed-steel splash shield inboard of the disc, cut out at the caliper."""
    ro, yi = d["r_out"], d["y_in"]
    y0 = yi - 7.0
    prof = [(62.0, y0 - 8.0), (70.0, y0 - 6.0), (ro - 30, y0 - 1.5), (ro - 6, y0),
            (ro + 1.5, y0 + 3.5), (ro + 3.0, y0 + 9.0)]
    t = 0.9
    outer = [(r, y) for r, y in prof]
    inner = [(r, y - t) for r, y in prof[::-1]]
    sec = outer + inner
    n = 72
    a0 = th_c + math.radians(gap_deg)
    a1 = th_c + 2 * math.pi - math.radians(gap_deg)
    th = np.linspace(a0, a1, n)
    rings = []
    for r, y in sec:
        rings.append(mb.add(np.stack([r * np.cos(th), np.full(n, y), r * np.sin(th)], 1) * MM))
    for i in range(len(rings)):
        mb.loft(rings[i], rings[(i + 1) % len(rings)], m_steel, closed=False)
    # end caps
    mb.face([r[0] for r in rings], m_steel)
    mb.face([r[-1] for r in rings][::-1], m_steel)


def build_hub_front(mb, m_steel, m_alu, m_rubber, th_c=0.0):
    # wheel hub flange + pilot (rotates with the wheel in reality; static here)
    revolve_local(mb, [(24.0, 56.0), (28.0, 55.0), (28.4, 46.0), (28.4, 40.0), (66.0, 40.0),
                       (68.0, 37.0), (64.0, 30.0), (45.0, 26.0), (42.0, 5.0)], 48, (0, 0), m_steel)
    # knuckle: bearing boss + arms
    revolve_local(mb, [(40.0, 6.0), (52.0, 2.0), (54.0, -10.0), (54.0, -38.0), (46.0, -46.0)],
                  32, (0, 0), m_alu)
    tube(mb, [(-10, -30, 40), (-14, -50, 110), (-10, -80, 165), (-6, -125, 190), (-4, -165, 232)],
         [24, 20, 18, 22, 28], m_alu)
    tube(mb, [(0, -28, -40), (5, -45, -110), (8, -60, -150)], [24, 20, 17], m_alu)
    tube(mb, [(-30, -30, 0), (-95, -45, 10), (-140, -60, 22)], [20, 16, 12], m_alu)
    # caliper mounting ears to the carrier (leading side)
    for sgn in (-1, 1):
        a = th_c + sgn * math.radians(30)
        p0 = polar_pt(50, a, -24)
        p1 = polar_pt(128, a, -26)
        tube(mb, [p0, 0.5 * (p0 + p1) + np.array([0, -6, 0]), p1], [14, 12, 10], m_alu)
    # outer CV joint + boot (FWD)
    revolve_local(mb, [(30.0, -46.0), (46.0, -52.0), (48.0, -70.0), (44.0, -88.0), (40.0, -92.0),
                       (42.0, -97.0), (34.0, -104.0), (38.0, -110.0), (29.0, -117.0), (33.0, -123.0),
                       (24.0, -130.0), (27.0, -136.0), (17.0, -146.0), (16.0, -175.0)], 32, (0, 0),
                  m_rubber, mats=[m_steel] * 4 + [m_rubber] * 9)


def build_hub_rear(mb, m_steel, m_rubber, th_c=0.0):
    revolve_local(mb, [(24.0, 56.0), (28.0, 55.0), (28.4, 46.0), (28.4, 40.0), (64.0, 40.0),
                       (66.0, 37.0), (60.0, 30.0), (44.0, 24.0), (40.0, 5.0)], 48, (0, 0), m_steel)
    revolve_local(mb, [(38.0, 2.0), (48.0, -2.0), (50.0, -10.0), (50.0, -34.0), (30.0, -40.0)],
                  32, (0, 0), m_steel)
    # wheel carrier arms: trailing arm (forward), spring link (down), upper link
    tube(mb, [(20, -30, 0), (110, -50, 15), (160, -110, 25), (240, -160, 30)], [26, 22, 20, 20], m_steel)
    tube(mb, [(-5, -30, -30), (-10, -60, -100), (-15, -120, -120)], [22, 20, 18], m_steel)
    tube(mb, [(-5, -30, 40), (-15, -60, 120), (-20, -110, 150)], [18, 15, 14], m_steel)
    for sgn in (-1, 1):
        a = th_c + sgn * math.radians(28)
        p0 = polar_pt(46, a, -20)
        p1 = polar_pt(112, a, -22)
        tube(mb, [p0, 0.5 * (p0 + p1) + np.array([0, -5, 0]), p1], [12, 10, 9], m_steel)
