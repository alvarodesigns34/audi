"""Compare triangulated feature points (out/features_3d.json, from
tools/triangulate.py) with the model skin: signed distance along the skin
normal (+ = point outside the model skin) and the model half-width at the
point's (x, z) cast from the side.

Usage: python tools/skin_dist.py [--only a,b,...]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import bpy  # noqa
import numpy as np  # noqa
from mathutils import Vector  # noqa
from mathutils.bvhtree import BVHTree  # noqa

from a3.body import shell  # noqa
from a3.core import materials, scene  # noqa


def main():
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = set(a.split("=", 1)[1].split(","))
    pts = json.load(open(os.path.join(ROOT, "out", "features_3d.json")))
    scene.reset()
    materials.reset_cache()
    ob, bl, grid = shell.skin_object(spacing=0.01)
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    print(f"{'feature':26s} {'x':>6s} {'y':>5s} {'z':>5s}  {'d_norm':>7s}  {'y_model':>7s}  {'dy':>5s}")
    for name, (x, y, z) in pts.items():
        if only and name not in only:
            continue
        p = Vector((x / 1000, abs(y) / 1000, z / 1000))
        loc, nrm, idx, dist = bvh.find_nearest(p)
        d = (p - loc).dot(nrm) * 1000
        hit = bvh.ray_cast(Vector((p.x, 3.0, p.z)), Vector((0, -1, 0)), 3.0)
        ym = hit[0].y * 1000 if hit[0] is not None else float("nan")
        print(f"{name:26s} {x:6.0f} {abs(y):5.0f} {z:5.0f}  {d:7.1f}  {ym:7.0f}  {abs(y) - ym:5.0f}")


if __name__ == "__main__":
    main()
