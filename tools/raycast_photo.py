"""Back-project photo pixels onto the model's reference skin (first hit).

Usage: python tools/raycast_photo.py <solution.json>  < points.txt
points.txt lines: name u v
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bpy  # noqa
from mathutils import Vector  # noqa
from mathutils.bvhtree import BVHTree  # noqa

from a3 import build  # noqa
from backproject import ray  # noqa

cfg = json.load(open(sys.argv[1]))
lines = [l.split() for l in sys.stdin if l.strip() and not l.startswith("#")]
ctx = build.build(["body"])
ref = ctx.objects["skin_ref"]
bvh = BVHTree.FromObject(ref, bpy.context.evaluated_depsgraph_get())
for name, u, v in lines:
    o, d = ray(cfg["solution"], cfg["size"], float(u), float(v))
    hit, nrm, idx, dist = bvh.ray_cast(Vector(o), Vector(d), 50)
    if hit is None:
        print(f"{name:8s} MISS")
    else:
        print(f"{name:8s} x={hit.x*1000:7.0f} y={hit.y*1000:6.0f} z={hit.z*1000:6.0f}")
