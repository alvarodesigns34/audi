"""Draw the epipolar curve of a pixel of photo A (mirrored to the visible
side of photo B) on photo B.  Usage:
  python tools/epipolar.py A u v B out.png [--far] [--box x0 y0 x1 y1]"""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from backproject import ray  # noqa
from camera_match import project  # noqa
from triangulate import cam  # noqa

ap = argparse.ArgumentParser()
ap.add_argument("A")
ap.add_argument("u", type=float)
ap.add_argument("v", type=float)
ap.add_argument("B")
ap.add_argument("out")
ap.add_argument("--far", action="store_true")
ap.add_argument("--box", nargs=4, type=int)
a = ap.parse_args()
sa, za, _ = cam(a.A)
sb, zb, ppb = cam(a.B)
o, d = ray(sa, za, a.u, a.v)
ts = np.linspace(2, 14, 400)
P = o[None] + ts[:, None] * d[None]
# mirror into B's visible side if the sides differ
if np.sign(sa[1]) != np.sign(sb[1]) and not a.far:
    P[:, 1] *= -1
q = project(sb, P, zb, ppb)
im = Image.open(os.path.join(ROOT, "reference", "photos", a.B + ".jpg")).convert("RGB")
dr = ImageDraw.Draw(im)
dr.line([tuple(p) for p in q], fill=(255, 0, 255), width=2)
for t, p in zip(ts[::40], q[::40]):
    dr.text(tuple(p + [4, 4]), f"{t:.1f}", fill=(255, 255, 0))
if a.box:
    im = im.crop(tuple(a.box))
im.save(a.out)
