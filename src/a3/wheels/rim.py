"""Audi exclusive 18" "5-arm rotor" cast wheel, 8J x 18 H2 ET46, 5x112, CB 57.1
(part 8V0 601 025 AN, gloss black with diamond-turned face).

Wheel-local frame (metres in the output, millimetres in the tables below):
    origin = wheel centre (tyre centre plane), +Y = OUTBOARD (wheel axis),
    +X = forward, +Z = up  (i.e. the frame of the LEFT wheels; right wheels are
    the same casting rotated 180 deg about Z).
Face coordinates (p, q) = (-x, z): the 2D image of the wheel seen from outside
(as in a side photo of the left side of the car), angles CCW in that image.

Construction (one welded mesh):
  * barrel: surface of revolution of the real rim section (J flanges, 5 deg
    bead seats, H2 humps, reverse drop centre, inner wall);
  * spoke disc: the diamond-turned face is a surface of revolution h_f(r)
    (a lathe can only produce that) with the 5 windows and the central star
    recess cut out; windows are lofted tunnels (crisp diamond edge, micro
    chamfer, 8 deg casting draft) down to the cast back surface h_b(r), which
    carries the lightening pockets behind each arm;
  * hub: star-shaped recess (cap seat + 5 bolt lobes), spherical bolt seats,
    centre bore 57.1, flat mounting face at y = +ET.
Status of dimensions: C confirmed, S secondary source, E estimate.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.interpolate import PchipInterpolator

from .. import spec
from . import builder as B

MM = 1e-3

# ----------------------------------------------------------------- key sizes
BEAD_R = spec.RIM_DIAMETER_IN * 25.4 / 2      # 228.6  C  (18" bead seat diameter)
FLANGE_IN = spec.RIM_WIDTH_IN * 25.4 / 2      # 101.6  C  (8J: width between flanges)
FLANGE_H = 17.5                               # C  ETRTO "J" flange height
ET = spec.RIM_OFFSET                          # 46   C
PCD_R = spec.PCD / 2                          # 56   C
BORE_R = spec.CENTRE_BORE / 2                 # 28.55 C
LIP_R = 245.5                                 # E  outer edge of diamond-cut lip (bead r + J height)
WIN_R_OUT = 233.8                             # E  windows run under the lip (photo: lip ring ~ 0.08 R)
BOLT_SEAT_R = 10.2                            # E  R13 ball-seat bore at the pocket floor
BOLT_HOLE_R = 7.5                             # E  M14x1.5 clearance
POCKET_FLOOR = 68.0                           # E  floor of the star recess (y)
CAP_R = 30.5                                  # S  4B0 601 170 A: 61 mm cap
CAP_SEAT_Y = 60.0                             # E
DRAFT = math.radians(8.0)                     # E  casting draft of window walls
N_REV = 200                                   # revolve segments (shared lip ring)
N_WIN = 120                                   # vertices per window outline
WIN_PHASE = 0.0                               # deg: angular phase of window 0

# Diamond-turned face profile y = h_f(r)  (E, fitted to photos: ~29 mm dish)
_HF = PchipInterpolator(
    [0, 36, 60, 80, 100, 130, 160, 190, 214, 228, 238, 245.5],
    [82.5, 83.0, 84.0, 85.6, 87.8, 92.0, 97.0, 102.6, 108.0, 111.6, 113.3, 113.6])
# Cast back surface of the spoke disc y = h_b(r)  (E)
_HB = PchipInterpolator(
    [0, 74, 82, 95, 120, 150, 180, 205, 220, 226],
    [ET, ET, 48.5, 54.0, 60.5, 66.5, 72.5, 79.0, 85.0, 88.0])


# barrel inner wall radius as function of y near the outboard flange (matches
# barrel_profile); the outer ends of the window walls follow it
_WALL_R = PchipInterpolator([40, 62, 72, 82, 92, 99, 103, 106.6, 110, 112, 115],
                            [217.4, 217.6, 218.4, 220.5, 221.6, 222.6, 224.6, 227.6,
                             231.6, 235.6, 245.0])


def h_f(r):
    return _HF(np.clip(r, 0, LIP_R))


def h_b(r):
    return _HB(np.clip(r, 0, 226))


def face_lift(pq):
    """(p,q) mm -> 3D point (mm) on the diamond face."""
    pq = np.asarray(pq).reshape(-1, 2)
    r = np.hypot(pq[:, 0], pq[:, 1])
    return np.stack([-pq[:, 0], h_f(r), pq[:, 1]], 1)


def pq_to_3d(pq, y):
    pq = np.asarray(pq).reshape(-1, 2)
    return np.stack([-pq[:, 0], np.broadcast_to(y, len(pq)), pq[:, 1]], 1)


# ----------------------------------------------------------------- outlines
# Window outline: (r [mm], alpha [deg, CCW from the window centre line]).
# Measured on a rectified photo of the wheel (white A3 S line, Wikimedia
# Commons), median of three windows, R_lip = 246 mm; the boundary of the
# dark region is the diamond-cut edge (flanks lie inside it)  (S/E).
# The CW flank is the almost straight, slightly offset edge (-31..-24 deg);
# the CCW flank is the long curved edge that bulges to +34 deg at r ~ 0.6 R and
# sweeps back towards the hub -> thin arms that flare strongly into the lip.
WINDOW_CP = [
    (61.0, -14.0), (66.4, -21.5), (73.8, -28.0), (83.6, -30.6), (98.4, -30.8),
    (113.0, -30.0), (128.0, -29.0), (142.7, -28.2), (157.4, -27.4), (172.0, -26.7),
    (187.0, -26.0), (201.7, -25.2), (216.5, -24.5), (226.0, -23.8), (231.0, -22.2),
    (233.2, -18.5), (233.8, -10.0), (233.8, 0.0), (233.2, 8.5), (231.0, 13.5),
    (226.0, 16.8), (216.5, 20.5), (201.7, 25.2), (187.0, 29.6), (172.0, 31.8),
    (157.4, 32.8), (142.7, 33.0), (128.0, 32.2), (113.0, 30.2), (98.4, 26.8),
    (83.6, 21.2), (73.8, 15.0), (66.4, 7.5), (61.5, 0.0), (59.8, -7.0),
]
WIN_SCALE = 1.00     # angular scale about the window centre (spoke width tuning vs photo)
LOBE_REL = -40.0     # deg, bolt lobe direction relative to window centre (photo ~-35, E)


def window_outline(k, n=N_WIN):
    cp = np.array(WINDOW_CP)
    cp[:, 1] = 2.5 + (cp[:, 1] - 2.5) * WIN_SCALE
    beta = math.radians(WIN_PHASE + 72.0 * k)
    ang = beta + np.radians(cp[:, 1])
    pts = np.stack([-cp[:, 0] * np.sin(ang), cp[:, 0] * np.cos(ang)], 1)
    dense = B.catmull_closed(pts, 24)
    return B.ccw(B.resample_closed(dense, n))


def bolt_angles():
    """Bolt directions in face coords (rad, CCW from +q): just CW of each window's
    straight edge, i.e. at the root of each arm (photo)."""
    return [math.radians(WIN_PHASE + 72.0 * k + LOBE_REL) for k in range(5)]


def star_outline(n=480):
    """Star recess: cap circle r=37 united with 5 bolt lobes (soft union)."""
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rr = [np.full(n, 37.0)]
    w, L = 14.5, PCD_R          # lobe half width, lobe centre distance
    for b in bolt_angles():
        d = np.angle(np.exp(1j * (th - b)))
        # farthest point of capsule (segment 0..L, radius w) along each ray
        c, s = np.cos(d), np.abs(np.sin(d))
        disc = (L * c) ** 2 - (L * L - w * w)
        r_end = np.where(disc >= 0, L * c + np.sqrt(np.maximum(disc, 0)), 0)
        r_side = np.where(s > 1e-6, w / np.maximum(s, 1e-6), 1e3)
        r_cap = np.where(L * c <= 0, 0, np.minimum(r_side, r_end))
        r_cap = np.where(s * L < w, np.maximum(r_end, 0), r_cap)
        rr.append(np.maximum(r_cap, 0))
    R = np.array(rr)
    p = 10.0
    r = (np.sum(R ** p, axis=0)) ** (1 / p)            # smooth union
    # visible convex corners -> slight rounding by smoothing in polar
    k = np.array([1, 4, 6, 4, 1], float) / 16
    for _ in range(2):
        r = np.convolve(np.concatenate([r[-2:], r, r[:2]]), k, "valid")
    # star is a hole in the face: (p,q) with angle th from +q CCW
    pts = np.stack([-r * np.sin(th), r * np.cos(th)], 1)
    return B.ccw(pts)


# ----------------------------------------------------------------- profiles
def barrel_profile():
    """Closed rim section (r, y) mm, starting at the lip edge, running round the
    OUTBOARD flange, along the tyre side (outer surface), round the inboard
    flange and back along the inner surface.  Each point carries a material
    flag: 1 = diamond-turned, 0 = gloss black.  Values: C where ETRTO-driven,
    E otherwise."""
    P = [
        (LIP_R, 113.6, 1),            # lip edge (shared with the face ring)
        (246.3, 113.25, 1),
        (246.85, 112.5, 1),
        (247.05, 111.4, 1),
        (247.0, 109.6, 1),            # flange OD (turned)
        (246.6, 107.6, 0),
        (245.6, 105.6, 0),
        (243.8, 103.7, 0),
        (241.4, 102.4, 0),
        (238.5, 101.75, 0),
        (234.0, 101.6, 0),            # flange inner face (bead contact) C
        (230.6, 101.4, 0),
        (229.3, 100.6, 0),
        (BEAD_R, 99.0, 0),            # 5 deg bead seat C
        (227.0, 82.0, 0),
        (227.9, 79.0, 0),             # H2 hump  C (profile E)
        (227.4, 75.5, 0),
        (225.2, 72.8, 0),
        (223.6, 69.0, 0),             # outboard ledge
        (223.4, 20.0, 0),
        (223.0, -12.0, 0),
        (221.0, -16.0, 0),            # drop-centre flank (reverse well)  E
        (213.0, -24.5, 0),
        (210.5, -28.5, 0),            # well bottom r~210  E
        (210.5, -51.0, 0),
        (212.5, -55.0, 0),
        (221.0, -66.0, 0),
        (225.2, -72.8, 0),
        (227.4, -75.5, 0),
        (227.9, -79.0, 0),            # inboard hump
        (227.0, -82.0, 0),
        (BEAD_R, -99.0, 0),
        (229.3, -100.6, 0),
        (230.6, -101.4, 0),
        (234.0, -101.6, 0),
        (238.5, -101.75, 0),
        (241.4, -102.4, 0),
        (243.8, -103.7, 0),
        (245.6, -105.6, 0),
        (246.6, -107.6, 0),
        (247.0, -109.6, 0),
        (247.05, -111.4, 0),
        (246.6, -112.9, 0),
        (245.3, -113.7, 0),
        (242.0, -114.0, 0),           # inboard flange back face
        (237.5, -113.6, 0),
        (234.0, -112.0, 0),
        (231.5, -109.0, 0),
        (229.5, -105.0, 0),
        (222.5, -98.0, 0),            # inner wall, ~6 mm section
        (221.5, -84.0, 0),
        (220.5, -77.5, 0),
        (216.0, -70.0, 0),
        (206.5, -58.5, 0),
        (204.5, -53.5, 0),
        (204.5, -27.0, 0),
        (206.0, -22.0, 0),
        (213.5, -13.0, 0),
        (216.8, -7.0, 0),
        (217.2, 20.0, 0),
        (217.6, 62.0, 0),
        (218.4, 72.0, 0),
        (220.5, 82.0, 0),
        (221.6, 92.0, 0),
        (222.6, 99.0, 0),
        (224.6, 103.0, 0),            # inner face of the outboard flange
        (227.6, 106.6, 0),            # (window walls run along it, see WALL_R)
        (231.6, 110.0, 0),
        (235.6, 112.0, 0),
        (241.0, 113.0, 0),            # closes just under the face (hidden)
    ]
    return P


# ----------------------------------------------------------------- build
def revolve_rings(mb, prof_ry, n, mat_seg, closed_profile, rings=None, flip=False):
    """Add rings for a (r,y) profile revolved about the local Y axis.
    ``rings`` may pre-supply some ring index arrays (dict profile_index->ring).
    Quad normals follow the left normal of the profile direction in (r,y)."""
    th = 2 * math.pi * np.arange(n) / n
    c, s = np.cos(th), np.sin(th)
    out = []
    for i, (r, y) in enumerate(prof_ry):
        if rings and i in rings:
            out.append(rings[i])
            continue
        out.append(mb.add(np.stack([r * c, np.full(n, y), r * s], 1) * MM))
    m = len(out)
    rng = range(m) if closed_profile else range(m - 1)
    for i in rng:
        j = (i + 1) % m
        mb.loft(out[i], out[j], mat_seg[i], True, flip)
    return out


def ring_pq(r, n):
    """2D (p,q) coordinates of a revolve ring of radius r (same vertex order)."""
    th = 2 * math.pi * np.arange(n) / n
    return np.stack([-r * np.cos(th), r * np.sin(th)], 1)


def build_rim(mb, mat_black=0, mat_diamond=1, detail="high"):
    step = 6.0 if detail == "high" else 10.0
    n_rev = N_REV

    # ---- barrel ---------------------------------------------------------
    prof = barrel_profile()
    pr = [(r, y) for r, y, _ in prof]
    # profile orientation: outboard lip -> outside (tyre side) -> inboard -> inner
    # this runs CW in (r,y)?  ensure outward normals (left normal) = outside:
    a = 0.5 * sum(pr[i][0] * pr[(i + 1) % len(pr)][1] - pr[(i + 1) % len(pr)][0] * pr[i][1]
                  for i in range(len(pr)))
    flip = a > 0   # CCW -> left normal points inside -> flip
    mats = [mat_diamond if (prof[i][2] and prof[(i + 1) % len(prof)][2]) else mat_black
            for i in range(len(prof))]
    rings = revolve_rings(mb, pr, n_rev, mats, True, flip=flip)
    lip_ring = rings[0]
    lip_pq = ring_pq(LIP_R, n_rev)

    # ---- windows --------------------------------------------------------
    win_top, win_back, win_back_pq = [], [], []
    for k in range(5):
        W = window_outline(k)
        top = mb.add(face_lift(W) * MM)
        win_top.append((W, top))
        # micro chamfer on the black flank side (catches a highlight line)
        W1 = B.offset_closed(W, -0.55)
        r1 = np.hypot(W1[:, 0], W1[:, 1])
        ring1 = mb.add(pq_to_3d(W1, h_f(r1) - 0.55) * MM)
        prev = top
        mb.loft(prev, ring1, mat_black)
        prev = ring1
        # straight drafted wall, a few rings so long walls shade evenly
        for t in (0.12, 0.3, 0.55, 0.8, 1.0):
            depth_est = (h_f(r1) - h_b(r1))
            Wt = B.offset_closed(W, -(0.55 + math.tan(DRAFT) * depth_est * t))
            rt = np.hypot(Wt[:, 0], Wt[:, 1])
            # outer end of the window: wall follows the flange/barrel inner wall
            y0 = (1 - t) * (h_f(rt) - 0.55) + t * h_b(rt)
            rn = _softmin(rt, _WALL_R(y0) - 0.6, 1.2)
            Wt = Wt * (rn / rt)[:, None]
            rt = rn
            y = (1 - t) * (h_f(rt) - 0.55) + t * h_b(rt)
            ring = mb.add(pq_to_3d(Wt, y) * MM)
            mb.loft(prev, ring, mat_black)
            prev = ring
        win_back.append(prev)
        win_back_pq.append(Wt)

    # ---- star recess (cap + bolt lobes) ---------------------------------
    S = star_outline()
    rs = np.hypot(S[:, 0], S[:, 1])
    s_top = mb.add(face_lift(S) * MM)
    S1 = B.offset_closed(S, -0.5)
    s1 = mb.add(pq_to_3d(S1, h_f(np.hypot(*S1.T)) - 0.5) * MM)
    mb.loft(s_top, s1, mat_black)
    depth = h_f(rs) - POCKET_FLOOR
    S2 = B.offset_closed(S, -(0.5 + math.tan(math.radians(4)) * depth))
    s2 = mb.add(pq_to_3d(S2, POCKET_FLOOR + 1.5) * MM)
    mb.loft(s1, s2, mat_black)
    S3 = B.offset_closed(S2, -0.8)
    s3 = mb.add(pq_to_3d(S3, POCKET_FLOOR) * MM)
    mb.loft(s2, s3, mat_black)

    # bolt seats and holes
    bolt_floor, bolt_back, bolt_back_pq = [], [], []
    for b in bolt_angles():
        c = np.array([-PCD_R * math.sin(b), PCD_R * math.cos(b)])
        prev = None
        seat = [(BOLT_SEAT_R, POCKET_FLOOR), (10.6, POCKET_FLOOR - 2.0),
                (9.6, POCKET_FLOOR - 4.2), (8.2, POCKET_FLOOR - 6.4),
                (BOLT_HOLE_R, POCKET_FLOOR - 7.5), (BOLT_HOLE_R, ET)]
        for i, (r, y) in enumerate(seat):
            ring2 = B.circle(r, 40, c)
            ring = mb.add(pq_to_3d(ring2, y) * MM)
            if prev is None:
                bolt_floor.append((ring2, ring))
            else:
                mb.loft(prev, ring, mat_black)
            prev = ring
        bolt_back.append(prev)
        bolt_back_pq.append(ring2)

    # centre: cap seat, bore
    cen = [(CAP_R, POCKET_FLOOR), (CAP_R, CAP_SEAT_Y), (BORE_R + 1.0, CAP_SEAT_Y),
           (BORE_R, CAP_SEAT_Y - 1.0), (BORE_R, ET + 1.5), (BORE_R + 1.5, ET)]
    prev = None
    for i, (r, y) in enumerate(cen):
        ring2 = B.circle(r, 96)
        ring = mb.add(pq_to_3d(ring2, y) * MM)
        if prev is None:
            cen_floor = (ring2, ring)
        else:
            # annulus (cap seat) faces +Y: ring order shrinking -> same loft rule
            mb.loft(prev, ring, mat_black)
        prev = ring
    cen_back = (ring2, prev)

    # floor of the star recess
    holes = [S3] + [f[0] for f in bolt_floor] + [cen_floor[0]]
    hidx = [s3] + [f[1] for f in bolt_floor] + [cen_floor[1]]
    mb.cdt_fill(holes, hidx, B.polar_grid(30, 75, 4.0),
                lambda p: pq_to_3d(p, POCKET_FLOOR) * MM, mat_black, min_dist=1.8)

    # ---- diamond face -----------------------------------------------------
    loops = [lip_pq, S] + [w[0] for w in win_top]
    lidx = [lip_ring, s_top] + [w[1] for w in win_top]
    mb.cdt_fill(loops, lidx, B.polar_grid(36, LIP_R, step),
                lambda p: face_lift(p) * MM, mat_diamond, min_dist=step * 0.45)

    # ---- back of the spoke disc ------------------------------------------
    R_BACK = 224.0
    back_outer_pq = ring_pq(R_BACK, n_rev)
    # hidden closing strip lip -> back, kept inside the barrel section
    prev = lip_ring
    for (r, y) in ((236.0, 110.0), (224.0, 95.0), (R_BACK, float(h_b(R_BACK)))):
        q = ring_pq(r, n_rev)
        ring = mb.add(np.stack([-q[:, 0], np.full(n_rev, y), q[:, 1]], 1) * MM)
        mb.loft(prev, ring, mat_black)
        prev = ring
    back_outer = prev

    allw = win_back_pq

    def back_lift(p):
        r = np.hypot(p[:, 0], p[:, 1])
        d = B.min_dist_to_polylines(p, allw)
        pocket = 9.0 * _smooth(d, 5.0, 11.0) * _smooth(r, 100, 118) * (1 - _smooth(r, 188, 204))
        return pq_to_3d(p, h_b(r) + pocket) * MM

    loops = [back_outer_pq] + win_back_pq + bolt_back_pq + [cen_back[0]]
    lidx = [back_outer] + win_back + bolt_back + [cen_back[1]]
    mb.cdt_fill(loops, lidx, B.polar_grid(BORE_R, R_BACK, step * 1.45),
                back_lift, mat_black, flip=True, min_dist=step * 0.4)
    return mb


def _softmin(x, c, k):
    """smooth min(x, c) with blend width k"""
    return -k * np.logaddexp(-np.asarray(x) / k, -c / k)


def _smooth(x, a, b):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------- hardware
CAP_FACE_Y = 81.6        # E  cap face just below the spoke face (h_f(0) ~ 82.5)


def _cap_dome(r):
    return CAP_FACE_Y + 1.1 * (1 - (np.asarray(r) / CAP_R) ** 2)


def build_cap(mb, m_body, m_rings):
    """Centre cap 4B0 601 170 A: slightly domed 61 mm cap, raised chrome rings."""
    n = 96
    prof = [(CAP_R - 0.2, CAP_SEAT_Y + 0.5), (CAP_R - 0.2, CAP_FACE_Y - 2.4),
            (CAP_R - 0.6, CAP_FACE_Y - 0.9), (CAP_R - 1.6, CAP_FACE_Y - 0.1)]
    rings = []
    th = 2 * math.pi * np.arange(n) / n
    for r, y in prof:
        rings.append(mb.add(pq_to_3d(np.stack([r * np.cos(th), r * np.sin(th)], 1), y) * MM))
    for a, b in zip(rings[:-1], rings[1:]):
        mb.loft(a, b, m_body)
    mb.cap(rings[0], m_body, flip=True)
    # domed face (CDT so the rings can be laid on top)
    outer = np.stack([(CAP_R - 1.6) * np.cos(th), (CAP_R - 1.6) * np.sin(th)], 1)
    mb.cdt_fill([outer], [rings[-1]], B.polar_grid(0, CAP_R - 2.5, 3.0, n_min=8),
                lambda p: pq_to_3d(p, _cap_dome(np.hypot(p[:, 0], p[:, 1]))) * MM, m_body, min_dist=1.0)
    # Audi rings: 4 x torus, D = 13.6 mm, overlapping, along p (horizontal)
    D, tw, hgt = 13.6, 1.55, 1.25
    Rm = (D - tw) / 2
    spacing = D - 0.27 * D
    nu, nv = 40, 8
    for i in range(4):
        cpx = (i - 1.5) * spacing
        u = 2 * math.pi * np.arange(nu) / nu
        v = 2 * math.pi * np.arange(nv) / nv
        U, V = np.meshgrid(u, v, indexing="ij")
        rr = Rm + 0.5 * tw * np.cos(V)
        p = cpx + rr * np.cos(U)
        q = rr * np.sin(U)
        yy = _cap_dome(np.hypot(p, q)) + 0.15 + hgt * 0.5 * (1 + np.sin(V)) * (np.sin(V) > -0.2) \
            + 0.5 * hgt * np.sin(V) * (np.sin(V) <= -0.2)
        pts = np.stack([-p, yy, q], -1).reshape(-1, 3) * MM
        base = mb.add(pts)
        idx = base.reshape(nu, nv)
        for a in range(nu):
            for b in range(nv):
                a2, b2 = (a + 1) % nu, (b + 1) % nv
                mb.face((idx[a, b], idx[a, b2], idx[a2, b2], idx[a2, b]), m_rings)


def build_bolts(mb, m_bolt):
    """M14x1.5 wheel bolts, 17 mm hex, captive ball-seat collar (E)."""
    AF = 17.0
    rc = AF / 2 / math.cos(math.radians(30))
    y_seat = POCKET_FLOOR
    for b in bolt_angles():
        c = np.array([-PCD_R * math.sin(b), PCD_R * math.cos(b)])
        # collar / washer with spherical seat (revolve)
        th = 2 * math.pi * np.arange(36) / 36
        prof = [(7.0, y_seat - 9.0), (8.3, y_seat - 6.3), (9.6, y_seat - 3.6), (10.15, y_seat - 0.4),
                (10.6, y_seat + 0.4), (10.6, y_seat + 2.6), (9.9, y_seat + 3.2)]
        rings = [mb.add(pq_to_3d(c + np.stack([r * np.cos(th), r * np.sin(th)], 1), y) * MM)
                 for r, y in prof]
        for a, bb in zip(rings[:-1], rings[1:]):
            mb.loft(a, bb, m_bolt)
        mb.cap(rings[0], m_bolt, flip=True)
        mb.cap(rings[-1], m_bolt)
        # hex head with chamfered corners, 11.5 mm high, 30 deg top chamfer
        hx = []
        for k in range(6):
            a0 = math.radians(60 * k + b * 180 / math.pi + 15)
            for e in (-4.0, 4.0):
                aa = a0 + math.radians(e)
                rr = (AF / 2) / math.cos(math.radians(30 - abs(e)))   # on the flat
                hx.append((rr * math.cos(aa), rr * math.sin(aa)))
        hx = B.ccw(np.array(hx))
        y0, y1 = y_seat + 3.0, y_seat + 14.5
        top_r = AF / 2 * 0.96
        ring0 = mb.add(pq_to_3d(c + hx, y0) * MM)
        ring1 = mb.add(pq_to_3d(c + hx, y1 - 1.6) * MM)
        circ = hx / np.linalg.norm(hx, axis=1, keepdims=True) * np.minimum(
            np.linalg.norm(hx, axis=1, keepdims=True), top_r)
        ring2 = mb.add(pq_to_3d(c + circ, y1) * MM)
        mb.loft(ring0, ring1, m_bolt)
        mb.loft(ring1, ring2, m_bolt)
        mb.cap(ring0, m_bolt, flip=True)
        mb.fan(ring2, pq_to_3d(c[None], y1 + 0.3)[0] * MM, m_bolt)


def build_valve(mb, m_metal, m_rubber, angle_deg=0.0):
    """Metal TPMS-style valve stem through the outboard barrel ledge, between
    two arms (visible through window 0)."""
    from .brakes import revolve_local
    a = math.radians(WIN_PHASE + angle_deg)
    radial = np.array([math.sin(a), 0.0, math.cos(a)])   # image dir (p,q)=(-sin a, cos a) -> (x,z)
    ax = -0.55 * radial + np.array([0, 0.835, 0])
    ax /= np.linalg.norm(ax)
    base = radial * 217.0 + np.array([0, 66.0, 0])
    prof = [(5.6, -4.0), (5.6, 1.0), (6.2, 1.5), (6.2, 5.5), (4.1, 6.0), (4.1, 26.0),
            (4.6, 26.5), (4.6, 37.0), (4.0, 37.6)]
    mats = [m_metal] * 6 + [m_rubber] * 3
    # revolve_local takes the axis through (x, 0, z); shift by the y of base along axis
    t = base[1] / ax[1]
    o = base - ax * t
    prof2 = [(r, h + t) for r, h in prof]
    revolve_local(mb, prof2, 16, (o[0], o[2]), m_metal, axis=ax, mats=mats)
