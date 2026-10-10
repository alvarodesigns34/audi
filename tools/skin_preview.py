"""Fast clay preview of the body skin only (no booleans) for surface review.
Usage: python tools/skin_preview.py out_dir view1,view2 [--res 1200x675] [--samples 16]
Custom views: hood (high over the bonnet), tailgate (behind, low), side_l, top."""
import argparse
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import bpy  # noqa

from a3.core import materials, render, scene  # noqa
from a3.body import shell  # noqa

EXTRA = {
    "hood": dict(loc=(2.6, 1.4, 1.9), target=(0.2, 0.0, 0.75), lens=40),
    "tailgate": dict(loc=(-6.2, 1.6, 1.15), target=(-3.3, 0.0, 0.85), lens=60),
    "front_low": dict(loc=(4.0, 2.2, 0.75), target=(0.5, 0.0, 0.55), lens=45),
    "shoulder": dict(loc=(-1.2, 4.0, 1.25), target=(-1.2, 0.8, 0.80), lens=35),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("views")
    ap.add_argument("--res", default="1200x675")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args()
    scene.reset()
    materials.reset_cache()
    m = materials.principled("Clay", "#2B2D31", roughness=0.25, coat=1.0, coat_rough=0.03)
    ob, bl, grid = shell.skin_object(spacing=0.008, material=m)
    render.studio()
    w, h = (int(v) for v in a.res.split("x"))
    for v in a.views.split(","):
        view = EXTRA.get(v, v)
        p = os.path.join(a.out, f"skin_{v}.png")
        render.render(p, view, res=(w, h), samples=a.samples)
        print("[skin]", p)


if __name__ == "__main__":
    main()
