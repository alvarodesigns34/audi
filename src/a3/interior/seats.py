"""Seats: S line sport front seats in black leather (perforated centre panels,
rock-grey contrast stitching), rear bench with 60/40 backrest and three head
restraints.

Upholstery is modelled as continuous 'slabs': a loft of closed cross-sections
(rounded rectangle whose front edge is modulated by a lateral profile), so the
bolsters are part of the same surface as the centre insert, exactly like a
trimmed seat.  Seams are real geometry: a soft groove is pressed into the
surface where two leather panels meet, and the thread (dashed stitches) runs
alongside it.  Faces of the insert zones carry the perforated leather
material.

Front seat local frame: origin at the H-point, axes parallel to the car.
"""
from __future__ import annotations

import math

import numpy as np

from ..core import mesh
from ..core.curves import smoothstep
from . import _geo as g
from . import layout

COL_F = "Interior/Seats/Front"
COL_R = "Interior/Seats/Rear"


# ---------------------------------------------------------------------------
# slab construction
# ---------------------------------------------------------------------------

def section(W, D, m, rf=0.045, rb=0.022, nf=112, dc=0.0):
    """Closed section (y, d) of an upholstered slab.

    W, D: full width / depth; m(y) -> front offset (bolsters +, insert -,
    seam grooves).  Returns points and a per-point flag 'front' (1 on the
    trimmed face).  Order: back centre -> +y side -> front (+y to -y) -> -y
    side -> back.
    """
    hw, hd = W / 2, D / 2
    P, F = [], []

    def add(y, d, f):
        P.append((y, d + dc))
        F.append(f)
    # back line +y half
    for y in np.linspace(0, hw - rb, 8, endpoint=False):
        add(y, -hd, 0)
    for a in np.linspace(-math.pi / 2, 0, 5, endpoint=False):
        add(hw - rb + rb * math.cos(a), -hd + rb + rb * math.sin(a), 0)
    for d in np.linspace(-hd + rb, hd - rf, 6, endpoint=False):
        add(hw, d, 0)
    me = m(hw - rf)
    for a in np.linspace(0, math.pi / 2, 10, endpoint=False):
        w = math.sin(a) ** 2
        add(hw - rf + rf * math.cos(a), hd - rf + rf * math.sin(a) + me * w, 0.5)
    for y in np.linspace(hw - rf, -(hw - rf), nf):
        add(y, hd + m(y), 1)
    me = m(-(hw - rf))
    for a in np.linspace(math.pi / 2, math.pi, 10)[1:]:
        w = math.sin(a) ** 2
        add(-(hw - rf) + rf * math.cos(a), hd - rf + rf * math.sin(a) + me * w, 0.5)
    for d in np.linspace(hd - rf, -hd + rb, 6)[1:]:
        add(-hw, d, 0)
    for a in np.linspace(math.pi, 3 * math.pi / 2, 5)[1:]:
        add(-(hw - rb) + rb * math.cos(a), -hd + rb + rb * math.sin(a), 0)
    for y in np.linspace(-(hw - rb), 0, 8)[1:-1]:
        add(y, -hd, 0)
    return np.array(P), np.array(F)


def seat_profile(hw, wi, hb, dep, groove=0.0045, crest=0.72, side_drop=0.5, extra=None):
    """Lateral front-offset function for a seat zone.
    hw: half width, wi: insert half width, hb: bolster height above the insert
    edge, dep: insert depression (centre), groove: seam groove depth."""
    def m(y):
        a = abs(y)
        yn = a / hw
        win = wi / hw
        ins = -dep * (1 - (a / max(wi, 1e-6)) ** 2) if a < wi else 0.0
        b = hb * smoothstep(win, win + (crest - win) * 1.4, yn)
        b *= 1 - side_drop * smoothstep(crest + 0.08, 1.0, yn)
        gr = -groove * math.exp(-((a - wi) / 0.0055) ** 2)
        v = ins + b + gr
        if extra is not None:
            v += extra(y)
        return v
    return m


def slab(name, col, us, sec_fn, place_fn, mat_main, mat_insert=None, insert_fn=None,
         cap_end=True, smooth=70):
    """Loft sections sec_fn(u)->(pts(n,2), flags) placed by place_fn(u, y, d)->xyz.
    insert_fn(u, y) -> bool selects faces that get mat_insert."""
    secs, meta = [], []
    for u in us:
        p, f = sec_fn(u)
        xyz = np.array([place_fn(u, y, d) for y, d in p])
        secs.append(xyz)
        meta.append((u, p[:, 0], f))
    pts = np.stack(secs)
    ob = mesh.grid_object(name, pts, closed_u=False, closed_v=True, collection=col,
                          material=mat_main, smooth=False, cap_u=cap_end)
    if mat_insert is not None and insert_fn is not None:
        idx = mesh.material_index(ob, mat_insert)
        nv = pts.shape[1]
        polys = ob.data.polygons
        k = 0
        for i in range(len(us) - 1):
            for j in range(nv):
                if k >= len(polys):
                    break
                j2 = (j + 1) % nv
                u = us[i]
                y = 0.5 * (meta[i][1][j] + meta[i][1][j2])
                fr = min(meta[i][2][j], meta[i][2][j2])
                if fr >= 1 and insert_fn(u, y):
                    polys[k].material_index = idx
                k += 1
    mesh.recalc_normals(ob)
    mesh.shade_smooth(ob, smooth)
    return ob


def end_round(us_core, u_end, r, n=6, sign=1):
    """Extra stations rounding a slab end: returns (u, k) with k=section scale."""
    out = []
    for t in np.linspace(0, 1, n + 1)[1:]:
        th = t * (math.pi / 2) * 0.96
        out.append((u_end + sign * r * math.sin(th), math.cos(th)))
    return out


# ---------------------------------------------------------------------------
# front seat
# ---------------------------------------------------------------------------

def front_seat(ctx, L, side, name):
    """side +1 driver (left, +y), -1 passenger."""
    H = L.h_point(side)
    col = COL_F
    lea = ctx.mat("leather_black")
    perf = ctx.mat("leather_perforated")
    stitch = g.Batch(f"{name}_Stitching", col, ctx.mat("stitch_grey"))

    # ---- cushion: stations along x (rear -> front), section in (y, z) ---------
    cp = math.tan(math.radians(11))              # E cushion rake
    z0 = -0.118                                  # E section centre below H at x=0
    WI_C = 0.122                                 # E insert half width
    X_SEAM = 0.300                               # E transverse seam before the front roll

    def c_params(x):
        hb = 0.060 * smoothstep(-0.10, 0.05, x) * (1 - 0.65 * smoothstep(0.22, 0.42, x))
        return 0.520 - 0.02 * smoothstep(0.25, 0.45, x), 0.105, hb

    def c_sec(u):
        x, k = u
        W, D, hb = c_params(x)
        tr = -0.0045 * math.exp(-((x - X_SEAM) / 0.006) ** 2)
        m = seat_profile(W / 2, WI_C, hb, 0.008,
                         extra=lambda y: tr * (1 - smoothstep(WI_C - 0.01, WI_C + 0.005, abs(y))))
        p, f = section(W * (0.88 + 0.12 * k), D * k, m, rf=0.040 * max(k, 0.3), dc=0.0)
        return p, f

    def c_place(u, y, d):
        x, k = u
        return H + np.array([x, y, z0 + x * cp + d])

    xs = list(np.linspace(-0.14, 0.40, 46))
    us = [(x, 1.0) for x in xs] + [(x, k) for x, k in end_round(xs, 0.40, 0.045, 7)]
    cushion = slab(f"{name}_Cushion", col, us, c_sec, c_place, lea, perf,
                   lambda u, y: abs(y) < WI_C - 0.002 and u[0] < X_SEAM - 0.004)
    ctx.register(f"{name}_cushion", cushion)
    surf = g.Surface(cushion)
    for s in (1, -1):
        pts = [c_place((x, 1.0), s * (WI_C + 0.008), 0.06) for x in np.linspace(-0.08, 0.38, 50)]
        g.stitch_on(stitch, surf, pts, (0, 0, 1), lateral=(0.0, s * 0.0045))
    pts = [c_place((X_SEAM + 0.007, 1.0), y, 0.06) for y in np.linspace(-WI_C, WI_C, 40)]
    g.stitch_on(stitch, surf, pts, (0, 0, 1))

    # ---- backrest: stations along u (height), section in (y, forward) --------
    a = math.radians(L.torso_front_deg)
    up = np.array([-math.sin(a), 0, math.cos(a)])
    fw = np.array([math.cos(a), 0, math.sin(a)])
    piv = np.array([-0.150, 0.0, -0.085])        # E recliner pivot w.r.t. H
    HB = 0.680                                   # E backrest height to the top roll
    U_SH = 0.505                                 # E shoulder-band seam
    WI_B = 0.130

    def b_params(u):
        W = 0.535 - 0.055 * smoothstep(0.42, 0.66, u)          # shoulders narrower
        D = 0.150 - 0.030 * smoothstep(0.30, 0.65, u)
        hb = 0.095 * smoothstep(0.0, 0.10, u) * (1 - 0.70 * smoothstep(0.32, 0.62, u))
        lum = 0.018 * math.exp(-((u - 0.17) / 0.10) ** 2)
        return W, D, hb, lum

    def b_sec(uu):
        u, k = uu
        W, D, hb, lum = b_params(u)
        ins = u < U_SH
        tr = -0.005 * math.exp(-((u - U_SH) / 0.007) ** 2)
        m = seat_profile(W / 2, WI_B if ins else 0.0, hb, 0.010 if ins else 0.0,
                         groove=0.0045 if ins else 0.0,
                         extra=lambda y: (lum * (1 - (abs(y) / WI_B) ** 2) if abs(y) < WI_B else 0.0)
                         + tr * (1 - smoothstep(WI_B, W / 2 - 0.02, abs(y))) - 0.004 * (not ins))
        p, f = section(W * (0.72 + 0.28 * k ** 0.6), D * k, m, rf=0.045 * max(k, 0.3), dc=0.0)
        return p, f

    def b_place(uu, y, d):
        u, k = uu
        return H + piv + up * u + np.array([0, y, 0]) + fw * d

    ub = list(np.linspace(0.0, HB, 56))
    us = [(u, 1.0) for u in ub] + [(u, k) for u, k in end_round(ub, HB, 0.050, 7)]
    back = slab(f"{name}_Backrest", col, us, b_sec, b_place, lea, perf,
                lambda uu, y: abs(y) < WI_B - 0.002 and uu[0] < U_SH - 0.004 and uu[0] > 0.03)
    ctx.register(f"{name}_backrest", back)
    surf = g.Surface(back)
    for s in (1, -1):
        pts = [b_place((u, 1.0), s * (WI_B + 0.008), 0.12) for u in np.linspace(0.04, U_SH, 50)]
        g.stitch_on(stitch, surf, pts, fw, lateral=(0.0, -s * 0.0045))
    pts = [b_place((U_SH + 0.008, 1.0), y, 0.12) for y in np.linspace(-0.23, 0.23, 70)]
    g.stitch_on(stitch, surf, pts, fw + 0.3 * up)

    # back shell (hard plastic) behind the slab
    def s_sec(uu):
        u, k = uu
        W, D, hb, lum = b_params(u)
        p, f = section((W - 0.006) * (0.92 + 0.08 * k), 0.05 * k, lambda y: 0.0, rf=0.02, rb=0.018,
                       nf=24)
        return p, f

    def s_place(uu, y, d):
        u, k = uu
        W, D, hb, lum = b_params(u)
        return H + piv + up * u + np.array([0, y, 0]) + fw * (d - D / 2 - 0.012)
    ub2 = list(np.linspace(0.02, HB - 0.01, 24))
    us = [(u, 1.0) for u in ub2] + [(u, k) for u, k in end_round(ub2, HB - 0.01, 0.03, 4)]
    shell = slab(f"{name}_BackShell", col, us, s_sec, s_place, ctx.mat("hard_plastic"))

    # ---- head restraint (rounded trapezoid, stitched perimeter) -------------
    hr_u = HB + 0.135
    def hr_sec(uu):
        u, k = uu
        t = (u - (hr_u - 0.095)) / 0.19
        W = 0.270 - 0.040 * t                           # wider at the bottom
        p, f = section(W * (0.85 + 0.15 * k), 0.090 * k,
                       lambda y: -0.010 * (y / (W / 2)) ** 2, rf=0.035 * max(k, 0.3), rb=0.03, nf=50)
        return p, f

    def hr_place(uu, y, d):
        u, k = uu
        return H + piv + up * u + np.array([0, y, 0]) + fw * (d + 0.005)
    uh = list(np.linspace(hr_u - 0.095, hr_u + 0.075, 16))
    us = [(u, k) for u, k in end_round(uh, uh[0], 0.02, 5, sign=-1)][::-1] + [(u, 1.0) for u in uh] \
        + [(u, k) for u, k in end_round(uh, uh[-1], 0.025, 6)]
    hr = slab(f"{name}_Headrest", col, us, hr_sec, hr_place, lea, cap_end=True)
    surf = g.Surface(hr)
    pts = []
    for t in np.linspace(0, 2 * math.pi, 120):
        u = hr_u - 0.010 + 0.072 * math.sin(t)
        w = (0.270 - 0.040 * ((u - (hr_u - 0.095)) / 0.19)) / 2 - 0.018
        pts.append(hr_place((u, 1.0), w * math.cos(t), 0.06))
    g.stitch_on(stitch, surf, pts, fw)
    for s in (1, -1):
        p0 = H + piv + up * (HB - 0.02) + np.array([0, s * 0.085, 0]) + fw * 0.0
        p1 = H + piv + up * (hr_u - 0.06) + np.array([0, s * 0.085, 0]) + fw * 0.0
        g.tube(f"{name}_Headrest_Post_{'L' if s > 0 else 'R'}", [p0, p1], 0.0042, 12, col,
               ctx.mat("chrome"))
        g.lathe(f"{name}_Headrest_Guide_{'L' if s > 0 else 'R'}",
                [(0.0, 0.0), (0.0080, 0.0), (0.0080, 0.012), (0.0055, 0.0145)],
                origin=tuple(H + piv + up * (HB - 0.006) + np.array([0, s * 0.085, 0])), axis=tuple(up),
                segments=16, col=col, mat=ctx.mat("hard_plastic"))
    stitch.build()
    _base_and_controls(ctx, L, side, name, H)


def _base_and_controls(ctx, L, side, name, H):
    col = COL_F
    plast = ctx.mat("hard_plastic")
    sat = ctx.mat("black_satin")
    s = side
    objs = []
    # cushion pan / lower trim (under the slab)
    pan = g.rbox(f"{name}_CushionPan", (0.50, 0.48, 0.05), (0.10, 0, -0.195), 0.015, 2, col, plast)
    objs.append(pan)
    # outboard side shield, height pump lever, recline wheel, lumbar knob
    sh = g.pillow(f"{name}_SideShield", (0.50, 0.022, 0.095), (0, 0, 0), (3.2, 2.2, 3.2), 10, col,
                  plast, fn=lambda p: p @ g.rot_y(math.radians(-8)).T + np.array([0.06, s * 0.262, -0.170]))
    objs.append(sh)
    lev = g.pillow(f"{name}_HeightLever", (0.15, 0.014, 0.026), (0, 0, 0), (3.0, 2.2, 2.6), 8, col,
                   sat, fn=lambda p: p @ g.rot_y(math.radians(-14)).T + np.array([0.05, s * 0.277, -0.160]))
    objs.append(lev)
    kn = g.lathe(f"{name}_ReclineWheel", [(0.0, 0.018), (0.024, 0.018), (0.028, 0.012),
                                          (0.028, 0.0), (0.0, 0.0)],
                 origin=(-0.140, s * 0.262, -0.105), axis=(0, s, 0), segments=32, col=col, mat=sat)
    objs.append(kn)
    rib = g.Batch(f"{name}_ReclineWheel_Ribs", col, sat)
    for k in range(18):
        th = 2 * math.pi * k / 18
        c = np.array([-0.140 + 0.0285 * math.cos(th), s * (0.262 + 0.009), -0.105 + 0.0285 * math.sin(th)])
        v, f = g.box_verts(c, np.array([math.cos(th), 0, math.sin(th)]) * 0.0015, (0, 0.008, 0),
                           np.array([-math.sin(th), 0, math.cos(th)]) * 0.002)
        rib.add(v, f)
    objs.append(rib.build())
    lk = g.lathe(f"{name}_LumbarKnob", [(0.0, 0.010), (0.012, 0.010), (0.014, 0.0), (0.0, 0.0)],
                 origin=(-0.190, s * 0.272, 0.010), axis=(0, s, 0), segments=24, col=col, mat=sat)
    objs.append(lk)
    # seat rails + covers
    for yy in (0.20, -0.20):
        objs.append(g.rbox(f"{name}_Rail_{'L' if yy > 0 else 'R'}", (0.62, 0.032, 0.026),
                           (0.05, yy, L.floor_z - H[2] + 0.013), 0.004, 2, col, ctx.mat("steel_dark")))
        objs.append(g.rbox(f"{name}_RailCover_{'L' if yy > 0 else 'R'}", (0.07, 0.040, 0.030),
                           (-0.28, yy, L.floor_z - H[2] + 0.016), 0.006, 2, col, plast))
    for yy in (0.20, -0.20):
        objs.append(g.rbox(f"{name}_Riser_{'L' if yy > 0 else 'R'}", (0.36, 0.022, 0.07),
                           (0.08, yy, -0.215 + 0.0), 0.004, 2, col, ctx.mat("steel_dark")))
    for o in objs:
        g.set_verts(o, g.verts_of(o) + H)


# ---------------------------------------------------------------------------
# rear bench
# ---------------------------------------------------------------------------

REAR_SEATS = ((0.375, 0.135), (0.0, 0.095), (-0.375, 0.135))   # E (centre y, insert half width)


def rear_profile(W, hb, dep, y_off=0.0):
    """Front offset for the 3-seat rear bench / backrest: inserts with seams,
    mild bolsters between and at the outer ends (offset y_off for split parts)."""
    def m(y):
        yy = y + y_off
        v = 0.0
        for yc, wi in REAR_SEATS:
            a = abs(yy - yc)
            if a < wi:
                v -= dep * (1 - (a / wi) ** 2)
            v -= 0.0045 * math.exp(-((a - wi) / 0.0055) ** 2)
        # outer bolsters
        v += hb * smoothstep(0.52, 0.60, abs(yy))
        # slight crown between seats
        v += 0.25 * hb * math.exp(-((abs(yy) - 0.20) / 0.04) ** 2)
        return v
    return m


def rear_bench(ctx, L):
    col = COL_R
    lea = ctx.mat("leather_black")
    perf = ctx.mat("leather_perforated")
    stitch = g.Batch("Rear_Stitching", col, ctx.mat("stitch_grey"))
    xf, xb = L.rear_cushion_x
    Hr = L.h_point(1, rear=True)
    cp = math.tan(math.radians(9))
    W = 1.30                                       # E bench width between the wheel arches
    z0 = Hr[2] - 0.135

    def in_insert(y):
        return any(abs(y - yc) < wi - 0.002 for yc, wi in REAR_SEATS)

    # cushion (stations along x from the backrest crease to the front edge)
    def c_sec(u):
        x, k = u
        m = rear_profile(W, 0.030, 0.006)
        return section(W * (0.96 + 0.04 * k), 0.13 * k, m, rf=0.045 * max(k, 0.3))

    def c_place(u, y, d):
        x, k = u
        return np.array([x, y, z0 + (x - Hr[0]) * cp + d])
    xs = list(np.linspace(xb - 0.02, xf - 0.04, 34))
    us = [(x, 1.0) for x in xs] + [(x, k) for x, k in end_round(xs, xf - 0.04, 0.05, 7)]
    cush = slab("Rear_Cushion", col, us, c_sec, c_place, lea, perf,
                lambda u, y: in_insert(y) and u[0] < xf - 0.08)
    surf = g.Surface(cush)
    for yc, wi in REAR_SEATS:
        for s in (1, -1):
            pts = [c_place((x, 1.0), yc + s * (wi + 0.008), 0.08) for x in np.linspace(xb + 0.04, xf - 0.06, 40)]
            g.stitch_on(stitch, surf, pts, (0, 0, 1))

    # backrest 60/40 (E: 40 % part behind the driver, +y side)
    a = math.radians(L.torso_rear_deg)
    up = np.array([-math.sin(a), 0, math.cos(a)])
    fw = np.array([math.cos(a), 0, math.sin(a)])
    piv = np.array([xb + 0.035, 0, z0 - 0.03])
    HB = (L.rear_back_top[1] - piv[2]) / math.cos(a)
    split = W / 2 - L.rear_split * W            # y of the split line (40 % part on +y)
    parts = (("40", split + 0.003, W / 2), ("60", -W / 2, split - 0.003))
    for nm, y0, y1 in parts:
        yc_part = (y0 + y1) / 2
        Wp = y1 - y0

        def b_sec(uu, Wp=Wp, yc_part=yc_part):
            u, k = uu
            hb = 0.05 * (1 - 0.6 * smoothstep(0.3, 0.6, u))
            m = rear_profile(W, hb, 0.008, y_off=yc_part)
            return section(Wp * (0.96 + 0.04 * k), 0.13 * k, m, rf=0.035 * max(k, 0.3))

        def b_place(uu, y, d, yc_part=yc_part):
            u, k = uu
            return piv + up * u + np.array([0, y + yc_part, 0]) + fw * d
        ub = list(np.linspace(0.0, HB, 40))
        us = [(u, 1.0) for u in ub] + [(u, k) for u, k in end_round(ub, HB, 0.05, 7)]
        bk = slab(f"Rear_Backrest_{nm}", col, us, b_sec, b_place, lea, perf,
                  lambda uu, y, yc_part=yc_part: in_insert(y + yc_part) and 0.05 < uu[0] < HB * 0.80)
        surf = g.Surface(bk)
        for yc, wi in REAR_SEATS:
            for s in (1, -1):
                yy = yc + s * (wi + 0.008)
                if not (y0 + 0.02 < yy < y1 - 0.02):
                    continue
                pts = [b_place((u, 1.0), yy - yc_part, 0.10) for u in np.linspace(0.06, HB * 0.80, 40)]
                g.stitch_on(stitch, surf, pts, fw)
        # release handle at the top outer corner
        so = 1 if nm == "40" else -1
        p = piv + up * (HB + 0.01) + np.array([0, so * 0.58, 0]) - fw * 0.02
        g.rbox(f"Rear_Backrest_{nm}_Release", (0.040, 0.050, 0.014), tuple(p), 0.006, 2, col,
               ctx.mat("black_satin"))
    # head restraints: outer larger, centre smaller, on posts
    for nm, (yc, _), w, hgt in (("L", REAR_SEATS[0], 0.25, 0.150), ("C", REAR_SEATS[1], 0.21, 0.120),
                                ("R", REAR_SEATS[2], 0.25, 0.150)):
        # outer restraints in the use position; the centre one stowed flush on
        # the backrest top (its normal position when the seat is unoccupied)
        uc = HB + (0.045 if nm != "C" else -0.012) + hgt / 2

        def h_sec(uu, w=w, hgt=hgt):
            u, k = uu
            return section(w * (0.85 + 0.15 * k), 0.085 * k, lambda y: -0.008 * (y / (w / 2)) ** 2,
                           rf=0.03 * max(k, 0.3), rb=0.025, nf=40)

        def h_place(uu, y, d, yc=yc):
            u, k = uu
            return piv + up * u + np.array([0, yc + y, 0]) + fw * d
        uh = list(np.linspace(uc - hgt / 2 + 0.02, uc + hgt / 2 - 0.025, 10))
        us = [(u, k) for u, k in end_round(uh, uh[0], 0.02, 4, sign=-1)][::-1] + [(u, 1.0) for u in uh] \
            + [(u, k) for u, k in end_round(uh, uh[-1], 0.025, 5)]
        slab(f"Rear_Headrest_{nm}", col, us, h_sec, h_place, lea)
        for s in (1, -1):
            p0 = piv + up * (HB - 0.02) + np.array([0, yc + s * 0.06, 0])
            p1 = piv + up * (uc - 0.03) + np.array([0, yc + s * 0.06, 0])
            g.tube(f"Rear_Headrest_{nm}_Post_{'L' if s > 0 else 'R'}", [p0, p1], 0.004, 10, col,
                   ctx.mat("chrome"))
    stitch.build()
    ctx.data["rear_back"] = dict(piv=piv, up=up, fw=fw, HB=HB)


def build(ctx):
    L = layout.get(ctx)
    front_seat(ctx, L, 1, "Seat_FL")
    front_seat(ctx, L, -1, "Seat_FR")
    rear_bench(ctx, L)
