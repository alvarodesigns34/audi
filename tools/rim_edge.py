"""Detect the outer rim-lip contour of a wheel in a photo (bright alloy ->
dark tyre transition) along rays from an approximate centre.

Usage: python tools/rim_edge.py photo.jpg u v r_min r_max [--n 48] [--debug out.png]
Prints a JSON list of [u, v] points (outliers removed by an ellipse fit).
"""
import argparse
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def fit_ellipse(P):
    x, y = P[:, 0], P[:, 1]
    D = np.stack([x * x, x * y, y * y, x, y, np.ones_like(x)], 1)
    _, _, vt = np.linalg.svd(D)
    return vt[-1]


def ellipse_dist(c, P):
    x, y = P[:, 0], P[:, 1]
    f = c[0] * x * x + c[1] * x * y + c[2] * y * y + c[3] * x + c[4] * y + c[5]
    gx = 2 * c[0] * x + c[1] * y + c[3]
    gy = c[1] * x + 2 * c[2] * y + c[4]
    return np.abs(f) / (np.hypot(gx, gy) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("u", type=float)
    ap.add_argument("v", type=float)
    ap.add_argument("rmin", type=float)
    ap.add_argument("rmax", type=float)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--debug", default="")
    ap.add_argument("--skip", default="", help="angle ranges to skip, deg 'a-b;c-d' (0=right, 90=down)")
    a = ap.parse_args()
    im = Image.open(a.photo).convert("L").filter(ImageFilter.GaussianBlur(1.2))
    g = np.asarray(im, float)
    H, W = g.shape
    skips = [tuple(map(float, s.split("-"))) for s in a.skip.split(";") if s]
    pts = []
    for ang in np.linspace(0, 360, a.n, endpoint=False):
        if any(lo <= ang <= hi for lo, hi in skips):
            continue
        t = np.radians(ang)
        rs = np.arange(a.rmin, a.rmax, 0.5)
        us = a.u + rs * np.cos(t)
        vs = a.v + rs * np.sin(t)
        ok = (us > 1) & (us < W - 2) & (vs > 1) & (vs < H - 2)
        if ok.sum() < 10:
            continue
        rs, us, vs = rs[ok], us[ok], vs[ok]
        prof = g[vs.round().astype(int), us.round().astype(int)]
        d = np.gradient(prof)
        k = np.argmin(d)          # strongest bright -> dark drop going outwards
        if d[k] > -4:
            continue
        pts.append((us[k], vs[k]))
    P = np.array(pts)
    for _ in range(3):
        c = fit_ellipse(P)
        e = ellipse_dist(c, P)
        keep = e < max(2.5 * np.median(e), 1.5)
        P = P[keep]
    print(json.dumps([[round(float(x), 1), round(float(y), 1)] for x, y in P]))
    if a.debug:
        img = Image.open(a.photo).convert("RGB")
        d = ImageDraw.Draw(img)
        for x, y in P:
            d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=(255, 0, 255), width=2)
        r = a.rmax * 1.3
        img.crop((int(a.u - r), int(a.v - r), int(a.u + r), int(a.v + r))).save(a.debug)


if __name__ == "__main__":
    main()
