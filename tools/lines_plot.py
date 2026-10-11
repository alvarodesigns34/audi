"""Plot the characteristic lines (plan and side views) with triangulated
feature points (out/features_3d.json) for reasoning about shape changes.

Usage: python tools/lines_plot.py out.png [--x0 -3.5 --x1 -2.0] [--pts a,b,...]
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import numpy as np  # noqa
from PIL import Image, ImageDraw  # noqa

from a3.body.surface import BodyLines  # noqa

COL = {"K1": (120, 120, 120), "K2": (160, 160, 160), "K3": (0, 160, 255), "K4": (0, 200, 100),
       "K5": (230, 200, 0), "K6": (255, 140, 0), "K7": (0, 220, 220), "K8": (255, 255, 255)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--x0", type=float, default=-3.5)
    ap.add_argument("--x1", type=float, default=-2.0)
    ap.add_argument("--pts", default="")
    ap.add_argument("--scale", type=float, default=900.0, help="px per metre")
    a = ap.parse_args()
    bl = BodyLines()
    xs = np.linspace(max(a.x0, bl.x_rear), min(a.x1, bl.x_front), 600)
    K = bl.keypoints(xs)
    s = a.scale
    W = int((a.x1 - a.x0) * s) + 80
    Hp, Hs = int(1.0 * s) + 40, int(1.5 * s) + 40
    img = Image.new("RGB", (W, Hp + Hs), (20, 20, 24))
    d = ImageDraw.Draw(img)

    def plan(x, y):
        return (40 + (x - a.x0) * s, Hp - 20 - y * s)

    def side(x, z):
        return (40 + (x - a.x0) * s, Hp + Hs - 20 - z * s)

    # grid every 0.1 m
    for gx in np.arange(np.ceil(a.x0 * 10) / 10, a.x1 + 1e-6, 0.1):
        c = (60, 60, 70) if round(gx * 10) % 5 else (90, 90, 110)
        d.line([plan(gx, 0), plan(gx, 1.0)], fill=c)
        d.line([side(gx, 0), side(gx, 1.5)], fill=c)
        if round(gx * 10) % 5 == 0:
            d.text(side(gx, 0.02), f"{gx:.1f}", fill=(200, 200, 200))
    for gy in np.arange(0, 1.01, 0.1):
        d.line([plan(a.x0, gy), plan(a.x1, gy)], fill=(60, 60, 70))
        d.text(plan(a.x0, gy), f"{gy:.1f}", fill=(200, 200, 200))
    for gz in np.arange(0, 1.51, 0.1):
        d.line([side(a.x0, gz), side(a.x1, gz)], fill=(60, 60, 70))
        d.text(side(a.x0, gz), f"{gz:.1f}", fill=(200, 200, 200))
    for k, c in COL.items():
        w, z = K[k]
        ok = (w > 1e-4) | (k == "K8")
        d.line([plan(x, y) for x, y in zip(xs[ok], w[ok])], fill=c, width=2)
        d.line([side(x, zz) for x, zz in zip(xs[ok], z[ok])], fill=c, width=2)
        d.text(plan(xs[ok][0], w[ok][0]), k, fill=c)
    pth = os.path.join(ROOT, "out", "features_3d.json")
    if os.path.exists(pth):
        pts = json.load(open(pth))
        sel = set(a.pts.split(",")) if a.pts else None
        for n, (x, y, z) in pts.items():
            x, y, z = x / 1000, abs(y) / 1000, z / 1000
            if (sel and n not in sel) or not (a.x0 <= x <= a.x1):
                continue
            for P in (plan(x, y), side(x, z)):
                d.ellipse([P[0] - 4, P[1] - 4, P[0] + 4, P[1] + 4], outline=(255, 0, 255), width=2)
                d.text((P[0] + 6, P[1] - 6), n, fill=(255, 120, 255))
    img.save(a.out)
    print(a.out)


if __name__ == "__main__":
    main()
