"""CLI: build (a subset of) the car, optionally render views / save / export.

Usage (with the bpy venv python):
    python tools/run.py --parts body,wheels --views front34,side --out out/renders
    python tools/run.py --save out/a3.blend --glb out/a3.glb
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import bpy  # noqa: E402

from a3 import build  # noqa: E402
from a3.core import render  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="")
    ap.add_argument("--paint", default="ibis_white")
    ap.add_argument("--views", default="")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "renders"))
    ap.add_argument("--res", default="1600x900")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--save", default="")
    ap.add_argument("--glb", default="")
    ap.add_argument("--no-draco", action="store_true", help="uncompressed GLB (exact geometry)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--clay", action="store_true", help="grey clay paint for shape review")
    a = ap.parse_args()
    parts = [p for p in a.parts.split(",") if p] or None
    ctx = build.build(parts, paint=a.paint, strict=a.strict)
    if a.clay:
        m = bpy.data.materials.get("Paint_Body")
        if m:
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (0.12, 0.12, 0.125, 1)
            b.inputs["Coat Weight"].default_value = 0.3
    if a.save:
        os.makedirs(os.path.dirname(os.path.abspath(a.save)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save), compress=True)
    if a.glb:
        from a3 import export
        export.glb(os.path.abspath(a.glb), draco=not a.no_draco)
    if a.views:
        render.studio()
        w, h = (int(v) for v in a.res.split("x"))
        for v in a.views.split(","):
            p = os.path.join(a.out, f"{a.tag}{v}.png")
            render.render(p, v, res=(w, h), samples=a.samples)
            print("[render]", p)
    stats(ctx)


def stats(ctx):
    tris = 0
    n = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH" and not ob.users_collection[0].name.startswith("_"):
            n += 1
            tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print(f"[stats] mesh objects: {n}, triangles: {tris:,}")


if __name__ == "__main__":
    main()
