"""Back-project photo pixels onto the bare body skin (no booleans: fast) and
optionally re-project the hits into other calibrated photos as a check.

Usage: python tools/raycast_skin.py <photo> [--check photo2,photo3]  < points.txt
points.txt lines: name u v      (pixel coordinates in <photo>)
Prints x y z (mm) of the first hit and, for every check photo, the pixel
where that 3D point projects (left/right mirrored to the visible side).
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bpy  # noqa
import numpy as np  # noqa
from mathutils import Vector  # noqa
from mathutils.bvhtree import BVHTree  # noqa

from a3.body import shell  # noqa
from a3.core import materials, scene  # noqa
from backproject import ray  # noqa
from camera_match import project  # noqa


def cam(name):
    c = json.load(open(os.path.join(ROOT, "reference", f"match_{name}.json")))
    return np.asarray(c["solution"], float), c["size"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--check", default="")
    a = ap.parse_args()
    scene.reset()
    materials.reset_cache()
    ob, bl, grid = shell.skin_object(spacing=0.01)
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    sol, size = cam(a.photo)
    checks = [c for c in a.check.split(",") if c]
    for line in sys.stdin:
        if not line.strip() or line.startswith("#"):
            continue
        name, u, v = line.split()[:3]
        o, d = ray(sol, size, float(u), float(v))
        hit = bvh.ray_cast(Vector(o), Vector(d / np.linalg.norm(d)), 50)
        if hit[0] is None:
            print(f"{name:10s} MISS")
            continue
        p = np.array(hit[0][:])
        out = f"{name:10s} x={p[0] * 1000:7.0f} y={p[1] * 1000:6.0f} z={p[2] * 1000:6.0f}"
        for c in checks:
            s2, sz2 = cam(c)
            q = p.copy()
            q[1] = abs(q[1]) * (1 if s2[1] > 0 else -1)
            uv = project(s2, q[None], sz2)[0]
            out += f"   {c}:({uv[0]:6.1f},{uv[1]:6.1f})"
        print(out)


if __name__ == "__main__":
    main()
