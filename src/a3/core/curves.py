"""1D/2D curve utilities used to describe the vehicle's characteristic lines.

Characteristic lines are written as tables of (x, value) control points in
millimetres and evaluated with shape-preserving monotone cubic (PCHIP)
interpolation, which never overshoots between control points — important so
that a crisp body line does not acquire ripples.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator, CubicSpline


class Line:
    """value(x) from control points, PCHIP or natural cubic."""

    def __init__(self, pts, kind="pchip", scale=1e-3):
        p = np.asarray(sorted(pts, key=lambda t: t[0]), float) * scale
        self.x0, self.x1 = p[0, 0], p[-1, 0]
        if kind == "pchip":
            self.f = PchipInterpolator(p[:, 0], p[:, 1], extrapolate=True)
        else:
            self.f = CubicSpline(p[:, 0], p[:, 1], bc_type="natural", extrapolate=True)

    def __call__(self, x):
        return self.f(np.clip(x, self.x0, self.x1))

    def d(self, x):
        return self.f.derivative()(np.clip(x, self.x0, self.x1))


def catmull_rom(points, n_per_seg=8, closed=False, alpha=0.5):
    """Centripetal Catmull-Rom spline through points (N x D)."""
    P = np.asarray(points, float)
    if closed:
        P = np.vstack([P[-1], P, P[0], P[1]])
    else:
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]

        def tj(ti, a, b):
            return ti + max(np.linalg.norm(b - a), 1e-9) ** alpha

        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        ts = np.linspace(t1, t2, n_per_seg, endpoint=False)
        for t in ts:
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    if not closed:
        out.append(P[-2])
    return np.array(out)


def resample(poly, n, closed=False):
    """Uniform arc-length resampling of a polyline."""
    P = np.asarray(poly, float)
    if closed:
        P = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    t = np.linspace(0, total, n, endpoint=not closed)
    out = np.empty((n, P.shape[1]))
    for k in range(P.shape[1]):
        out[:, k] = np.interp(t, s, P[:, k])
    return out


def rounded_polygon(pts, radii, n_arc=8):
    """Polygon (2D) with each corner filleted by its radius."""
    P = np.asarray(pts, float)
    n = len(P)
    if np.isscalar(radii):
        radii = [radii] * n
    out = []
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        r = radii[i]
        if r <= 0:
            out.append(b)
            continue
        v1 = (a - b) / np.linalg.norm(a - b)
        v2 = (c - b) / np.linalg.norm(c - b)
        ang = np.arccos(np.clip(np.dot(v1, v2), -1, 1))
        if ang < 1e-3 or abs(ang - np.pi) < 1e-3:
            out.append(b)
            continue
        d = r / np.tan(ang / 2)
        d = min(d, 0.49 * np.linalg.norm(a - b), 0.49 * np.linalg.norm(c - b))
        r_eff = d * np.tan(ang / 2)
        p1 = b + v1 * d
        p2 = b + v2 * d
        bis = (v1 + v2) / np.linalg.norm(v1 + v2)
        center = b + bis * (r_eff / np.sin(ang / 2))
        a1 = np.arctan2(*(p1 - center)[::-1])
        a2 = np.arctan2(*(p2 - center)[::-1])
        da = (a2 - a1 + np.pi) % (2 * np.pi) - np.pi
        for t in np.linspace(0, 1, n_arc):
            th = a1 + da * t
            out.append(center + r_eff * np.array([np.cos(th), np.sin(th)]))
    return np.array(out)


def superellipse(a, b, n=4.0, count=64, center=(0, 0)):
    t = np.linspace(0, 2 * np.pi, count, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2 / n)
    y = b * np.sign(s) * np.abs(s) ** (2 / n)
    return np.stack([x + center[0], y + center[1]], 1)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)
