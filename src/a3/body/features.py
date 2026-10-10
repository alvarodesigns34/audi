"""Local surface features applied to the structured skin grid (left half)
before meshing: displacements along the surface normal.

* hood ribs     : the two creases of the 8V bonnet running from the upper
                  corners of the Singleframe grille back towards the A-pillar
                  bases (a "V" opening towards the windscreen); the panel
                  between them is raised, so each rib is a crisp step.
* arch flares   : the shoulders over the wheels (the surface around the
                  arch is pushed out a few mm, fading over ~0.15 m).
* tailgate band : horizontal "light band" between the tail lamps: upper
                  crease z 0.973 (just above the rings) and a step at z 0.877
                  over the recessed licence-plate area (sline_rear ray casts).

All amplitudes are estimates (E) tuned against photographs.
"""
from __future__ import annotations

import numpy as np

from ..spec import m as mm

# hood rib line in plan (x, y) m, from the grille corner to the windscreen
HOOD_RIB = ((0.792, 0.392), (-0.335, 0.622))
HOOD_RIB_H = 0.0055          # E  height of the raised centre panel
HOOD_RIB_W = 0.050           # E  width over which it rises

ARCH_FLARE = 0.006           # E  outward push at the arch edge
ARCH_FLARE_FADE = 0.075      # E  e-folding distance away from the arch

TG_BAND = (0.877, 0.973)     # S  tailgate band z range (m)
TG_BAND_OUT = 0.005          # E  band stands out of the surface below/above
TG_BAND_HALF = 0.600         # E  half width where it merges into the lamps


def _normals(P):
    du = np.gradient(P, axis=0)
    dv = np.gradient(P, axis=1)
    n = np.cross(du, dv)
    ln = np.linalg.norm(n, axis=-1, keepdims=True)
    n = n / np.maximum(ln, 1e-12)
    # orient outwards: the roof centre must point up
    i, j = P.shape[0] // 2, P.shape[1] - 2
    if n[i, j, 2] < 0:
        n = -n
    return n


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hood_ribs(P, n):
    (ax, ay), (bx, by) = HOOD_RIB
    a = np.array([ax, ay])
    b = np.array([bx, by])
    L = np.linalg.norm(b - a)
    t_hat = (b - a) / L
    xy = P[..., :2]
    rel = xy - a
    t = (rel @ t_hat) / L
    # signed distance, positive towards the centre line (smaller y)
    nrm = np.array([-t_hat[1], t_hat[0]])          # points to the -y (centre) side
    s = rel @ nrm
    H = HOOD_RIB_H * _smooth((t - 0.06) / 0.16) * _smooth((1.0 - t) / 0.18)
    on_hood = (n[..., 2] > 0.55) & (t > 0) & (t < 1) & (P[..., 2] > 0.68)
    D = np.where(on_hood & (s > 0), H * np.sqrt(np.clip(s / HOOD_RIB_W, 0, 1)), 0.0)
    return D


def arch_flares(P, n):
    D = np.zeros(P.shape[:2])
    from .openings import ARCH_CZ, ARCH_R, ARCH_R_REAR
    for xc, r in ((0.0, mm(ARCH_R)), (-2.636, mm(ARCH_R_REAR))):
        rho = np.hypot(P[..., 0] - xc, P[..., 2] - mm(ARCH_CZ))
        d = rho - r
        side = np.abs(n[..., 1]) > 0.45
        upper = P[..., 2] > mm(ARCH_CZ) - 0.06
        f = _smooth((d + 0.02) / 0.02) * np.exp(-np.maximum(d, 0) / ARCH_FLARE_FADE)
        D += np.where(side & upper, ARCH_FLARE * f, 0.0)
    return D


def tailgate_band(P, n):
    z0, z1 = TG_BAND
    z = P[..., 2]
    rear = (n[..., 0] < -0.45) & (P[..., 0] < -3.15)
    y = np.abs(P[..., 1])
    w = _smooth((TG_BAND_HALF - y) / 0.10)
    # edges with ~10 mm transitions (the rear-cap rings are ~8 mm apart) - plateau standing out by TG_BAND_OUT
    band = _smooth((z - z0) / 0.009) * _smooth((z1 - z) / 0.012)
    # the plate recess below the band is set back a little more
    recess = -0.003 * _smooth((z0 - 0.010 - z) / 0.010) * _smooth((z - 0.700) / 0.03)
    return np.where(rear, w * (TG_BAND_OUT * band + recess), 0.0)


def apply(P):
    """Displace grid points (nu, nv, 3) along their normals; returns new grid."""
    n = _normals(P)
    D = hood_ribs(P, n) + arch_flares(P, n) + tailgate_band(P, n)
    out = P + n * D[..., None]
    # keep the centre line on y = 0
    out[..., 1] = np.where(np.abs(P[..., 1]) < 1e-9, 0.0, out[..., 1])
    return out
