"""Evaluation of the body outer skin from the characteristic lines.

The skin is generated as a structured grid: rows = transverse stations along
X, columns = points around the half section (bottom centre -> roof centre).
Between key points the section is a cubic Hermite curve with controllable
tangents (crease or smooth) and a convex/concave "bulge" term.
"""
from __future__ import annotations

import numpy as np

from ..core.curves import Line
from . import lines as L

KEYS = ["K0", "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"]
SEGS = [KEYS[i] + KEYS[i + 1] for i in range(8)]


class BodyLines:
    """Vectorised evaluation of all characteristic lines (inputs in metres)."""

    def __init__(self):
        self.z_top = Line(L.Z_TOP)
        self.z_bot = Line(L.Z_BOT)
        self.k1w = Line(L.K1_W)
        self.k2w, self.k2z = Line(L.K2_W), Line(L.K2_Z)
        self.k3w, self.k3z = Line(L.K3_W), Line(L.K3_Z)
        self.k4w, self.k4z = Line(L.K4_W), Line(L.K4_Z)
        self.k5w, self.k5z = Line(L.K5_W), Line(L.K5_Z)
        self.k6w, self.k6z = Line(L.K6_W), Line(L.K6_Z)
        self.k7w, self.k7z = Line(L.K7_W), Line(L.K7_Z)
        # bulge / crease tables hold dimensionless values (x in mm)
        self._bulge_tables = {k: np.asarray(v, float) for k, v in L.BULGE.items()}
        self.x_front = L.Z_TOP[0][0] * 1e-3
        self.x_rear = L.Z_TOP[-1][0] * 1e-3
        # extent where K5..K7 exist (they collapse to the top centre outside)
        self.k5_range = (L.K5_W[-1][0] * 1e-3, L.K5_W[0][0] * 1e-3)
        self.k6_range = (L.K6_W[-1][0] * 1e-3, L.K6_W[0][0] * 1e-3)
        self.k7_range = (L.K7_W[-1][0] * 1e-3, L.K7_W[0][0] * 1e-3)

    def crease(self, table, x):
        t = np.asarray(table, float)
        return np.interp(x * 1e3, t[::-1, 0], t[::-1, 1])

    def bulge_at(self, seg, x):
        t = self._bulge_tables[seg]
        return np.interp(x * 1e3, t[::-1, 0], t[::-1, 1])

    def keypoints(self, x):
        """Return dict K -> (w, z) arrays for station(s) x (metres)."""
        x = np.atleast_1d(np.asarray(x, float))
        zt, zb = self.z_top(x), self.z_bot(x)
        K = {}
        K["K0"] = (np.zeros_like(x), zb)
        K["K1"] = (self.k1w(x), zb + L.K1_DZ * 1e-3)
        K["K2"] = (self.k2w(x), self.k2z(x))
        K["K3"] = (self.k3w(x), self.k3z(x))
        K["K4"] = (self.k4w(x), self.k4z(x))
        for name, wl, zl, rng in (("K5", self.k5w, self.k5z, self.k5_range),
                                  ("K6", self.k6w, self.k6z, self.k6_range),
                                  ("K7", self.k7w, self.k7z, self.k7_range)):
            inside = (x >= rng[0]) & (x <= rng[1])
            w = np.where(inside, wl(x), 0.0)
            z = np.where(inside, zl(x), zt)
            K[name] = (np.maximum(w, 0.0), z)
        K["K8"] = (np.zeros_like(x), zt)
        # enforce z ordering sanity near the tips: no key point above the top
        # or below the bottom centre-line.
        for k in KEYS[1:8]:
            w, z = K[k]
            K[k] = (w, np.clip(z, zb, np.maximum(zt, zb)))
        return K


def hermite(p0, p1, t0, t1, n, bulge=0.0, cluster=0.0):
    """Sample n points (excluding p1) of a cubic Hermite segment (2D).

    cluster (0..1) concentrates samples towards both ends (cosine spacing
    blend) so that creases at key points keep a tight radius when shaded."""
    s = np.linspace(0.0, 1.0, n, endpoint=False)
    if cluster:
        s = (1 - cluster) * s + cluster * 0.5 * (1 - np.cos(np.pi * s))
    s = s[:, None]
    h00 = 2 * s**3 - 3 * s**2 + 1
    h10 = s**3 - 2 * s**2 + s
    h01 = -2 * s**3 + 3 * s**2
    h11 = s**3 - s**2
    pts = h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1
    if bulge:
        d = p1 - p0
        ln = np.linalg.norm(d)
        if ln > 1e-9:
            nrm = np.array([d[1], -d[0]]) / ln  # outward for CCW travel
            pts = pts + nrm * (bulge * ln * 4 * s * (1 - s))
    return pts


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v * 0


def section(bl: BodyLines, x: float):
    """Half section polyline (N x 2: y>=0, z) from bottom to roof centre."""
    K = bl.keypoints(x)
    P = [np.array([K[k][0][0], K[k][1][0]]) for k in KEYS]
    crease = {
        "K1": 1.0, "K5": 1.0,
        "K6": float(bl.crease(L.K6_CREASE, x)),
        "K7": float(bl.crease(L.K7_CREASE, x)),
    }
    # tangents (direction) at each key point
    tin, tout = [None] * 9, [None] * 9
    for i in range(9):
        if i == 0:
            d = np.array([1.0, 0.0])
            tin[i] = tout[i] = d
            continue
        if i == 8:
            d = np.array([-1.0, 0.0])
            tin[i] = tout[i] = d
            continue
        if i >= 5 and P[i][0] < 1e-6:
            # collapsed onto the top centre line: behave like the roof centre
            d = np.array([-1.0, 0.0])
            tin[i] = tout[i] = d
            continue
        smooth = _unit(P[i + 1] - P[i - 1])
        a = _unit(P[i] - P[i - 1])
        b = _unit(P[i + 1] - P[i])
        c = crease.get(KEYS[i], 0.0)
        tin[i] = _unit((1 - c) * smooth + c * a) if np.any(a) else smooth
        tout[i] = _unit((1 - c) * smooth + c * b) if np.any(b) else smooth
        if KEYS[i] == "K7":
            # v0.3: lift of the K7 out-tangent (deg, towards vertical) - the
            # rounded-box section of the rear roof / spoiler over the wrapped
            # rear glass (a symmetric bulge cannot do it without overshooting
            # the roof centre line)
            lift = np.radians(float(bl.crease(L.K7_LIFT, x)))
            if lift:
                ca, sa = np.cos(lift), np.sin(lift)
                t = tout[i]
                # rotate clockwise in the (y, z) half plane (towards +z for an
                # inward-pointing tangent)
                tout[i] = _unit(np.array([ca * t[0] + sa * t[1], -sa * t[0] + ca * t[1]]))
                if tout[i][1] < 0:
                    tout[i] = _unit(np.array([ca * t[0] - sa * t[1], sa * t[0] + ca * t[1]]))
    out = []
    for i in range(8):
        seg = SEGS[i]
        n = L.SEG_SAMPLES[seg]
        p0, p1 = P[i], P[i + 1]
        ln = np.linalg.norm(p1 - p0)
        pts = hermite(p0, p1, tout[i] * ln, tin[i + 1] * ln, n, bl.bulge_at(seg, x),
                      L.SEG_CLUSTER.get(seg, 0.0))
        out.append(pts)
    out.append(P[8][None])
    sec = np.vstack(out)
    sec[:, 0] = np.maximum(sec[:, 0], 0.0)
    return sec


def column_index():
    """Index of every key point inside a section polyline."""
    idx, c = {}, 0
    for i, seg in enumerate(SEGS):
        idx[KEYS[i]] = c
        c += L.SEG_SAMPLES[seg]
    idx["K8"] = c
    return idx


def stations(x_from, x_to, spacing=0.012):
    """Uniform station positions between the two end-cap split planes."""
    n = max(2, int(np.ceil(abs(x_from - x_to) / spacing)) + 1)
    return np.linspace(x_from, x_to, n)


# --------------------------------------------------------------------------
# End caps: "side profile x plan" surfaces
# --------------------------------------------------------------------------

def _profile_inverse(zfun, x_a, x_b, n=800):
    """Invert a monotone centre-line profile z(x) on [x_a, x_b] -> x(z)."""
    xs = np.linspace(x_a, x_b, n)
    zs = zfun(xs)
    order = np.argsort(zs)
    zs, xs = zs[order], xs[order]
    keep = np.concatenate([[True], np.diff(zs) > 1e-7])
    return zs[keep], xs[keep]


class EndCap:
    """Closes the skin beyond a split station with nested rings.

    Each ring is the split-section loop scaled about the nose (or tail)
    centre C in the (y, z) plane; the x of every point is

        x = x_split + (x_c(z) - x_split) * g(|y| / W(z))

    with x_c(z) the centre-line side silhouette, W(z) the split-loop
    half-width at height z and g(u) = (1 - u^m)^(1/n) the plan rounding.
    The surface is therefore a graph over the front (rear) view: it cannot
    fold, and it meets the station loft with matching position.
    """

    def __init__(self, bl, x_split, front=True):
        self.bl = bl
        self.front = front
        self.xs = x_split
        cfg = L.FRONT_CAP if front else L.REAR_CAP
        self.cfg = cfg
        self.zc = cfg["centre_z"] * 1e-3
        tip = bl.x_front if front else bl.x_rear
        self.tip = tip
        self.loop = section(bl, x_split)          # half loop bottom->top
        zt, zb = float(bl.z_top(x_split)), float(bl.z_bot(x_split))
        self.z_lo, self.z_hi = zb, zt
        # centre-line silhouette as functions of z (lower and upper branches)
        self.up_z, self.up_x = _profile_inverse(bl.z_top, x_split, tip)
        self.lo_z, self.lo_x = _profile_inverse(bl.z_bot, x_split, tip)
        self.z_tip = float(bl.z_top(tip))
        # half width of the split loop as a function of z: outermost y
        zz = np.linspace(zb, zt, 600)
        P = self.loop
        W = np.zeros_like(zz)
        for k in range(len(P) - 1):
            (y0, z0), (y1, z1) = P[k], P[k + 1]
            lo, hi = min(z0, z1), max(z0, z1)
            m = (zz >= lo) & (zz <= hi)
            if hi - lo > 1e-9:
                t = (zz[m] - z0) / (z1 - z0)
                W[m] = np.maximum(W[m], y0 + t * (y1 - y0))
            else:
                W[m] = np.maximum(W[m], max(y0, y1))
        self.Wz, self.W = zz, np.maximum(W, 1e-4)
        self.m_tab = np.asarray(cfg["plan_m"], float)
        self.n_tab = np.asarray(cfg["plan_n"], float)

    def x_c(self, z):
        z = np.asarray(z, float)
        upper = np.interp(z, self.up_z, self.up_x)
        lower = np.interp(z, self.lo_z, self.lo_x)
        return np.where(z >= self.z_tip, upper, lower)

    def g(self, u, z):
        zmm = z * 1e3
        m = np.interp(zmm, self.m_tab[:, 0], self.m_tab[:, 1])
        n = np.interp(zmm, self.n_tab[:, 0], self.n_tab[:, 1])
        u = np.clip(u, 0.0, 1.0)
        return (1.0 - u ** m) ** (1.0 / n)

    def x_at(self, y, z):
        W = np.interp(z, self.Wz, self.W)
        return self.xs + (self.x_c(z) - self.xs) * self.g(np.abs(y) / W, z)

    def rings(self, count=70, power=1.35):
        """Ring rows ordered from the split loop (r=1) to the pole (r=0).

        v0.3: dense near the split loop (r = 1 - t^p, p > 1).  v0.2 used
        t^(1/p), i.e. the opposite: the first ring sat at r 0.87, so the
        last ~100 mm of the roof (spoiler) and of the hood leading edge were
        a single flat facet."""
        t = np.linspace(0.0, 1.0, count + 1)[1:]
        r = 1.0 - t ** power               # dense near the split loop
        r = np.concatenate([r[:-1], [0.0]])
        rows = []
        for rk in r:
            y = rk * self.loop[:, 0]
            z = self.zc + rk * (self.loop[:, 1] - self.zc)
            x = self.x_at(y, z)
            rows.append(np.stack([x, y, z], 1))
        return np.array(rows)


def skin_grid(bl: BodyLines | None = None, spacing=0.012):
    bl = bl or BodyLines()
    xf, xr = L.X_FRONT_SPLIT * 1e-3, L.X_REAR_SPLIT * 1e-3
    xs = stations(xf, xr, spacing)
    secs = [section(bl, x) for x in xs]
    nv = len(secs[0])
    mid = np.zeros((len(xs), nv, 3))
    for i, (x, s) in enumerate(zip(xs, secs)):
        mid[i, :, 0] = x
        mid[i, :, 1] = s[:, 0]
        mid[i, :, 2] = s[:, 1]
    front = EndCap(bl, xf, front=True).rings(L.FRONT_CAP["rings"])[::-1]
    rear = EndCap(bl, xr, front=False).rings(L.REAR_CAP["rings"])
    grid = np.concatenate([front, mid[1:-1], rear], 0)
    from . import features
    grid = features.apply(grid)
    return grid, xs
