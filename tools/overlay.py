"""Render the model through a calibrated photo camera and overlay it on the photo.

Usage: python tools/overlay.py <solution.json> <photo.jpg> <out.png> [--parts body,...]
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
from mathutils import Matrix  # noqa
from PIL import Image, ImageChops, ImageFilter  # noqa

from a3 import build  # noqa
from a3.core import render  # noqa
from camera_match import rot  # noqa


LINE_COLORS = {"K3": (0, 160, 255), "K4": (0, 255, 120), "K5": (255, 255, 0),
               "K6": (255, 140, 0), "K7": (0, 255, 255)}


def draw_lines(img, sol, size, side=-1):
    """Project the body's characteristic lines (one side) onto the photo."""
    from PIL import ImageDraw
    from a3.body.surface import BodyLines
    from camera_match import project
    bl = BodyLines()
    xs = np.linspace(bl.x_front, bl.x_rear, 600)
    K = bl.keypoints(xs)
    d = ImageDraw.Draw(img)
    for k, col in LINE_COLORS.items():
        w, z = K[k]
        ok = w > 0.02
        P = np.stack([xs, side * w, z], 1)[ok]
        if len(P) < 2:
            continue
        uv = project(np.asarray(sol, float), P, size)
        d.line([tuple(p) for p in uv], fill=col + (255,), width=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("solution")
    ap.add_argument("photo")
    ap.add_argument("out")
    ap.add_argument("--parts", default="body")
    ap.add_argument("--samples", type=int, default=12)
    a = ap.parse_args()
    cfg = json.load(open(a.solution))
    x = cfg["solution"]
    W, H = cfg["size"]
    build.build([p for p in a.parts.split(",") if p])
    render.studio(floor=False)
    cam_data = bpy.data.cameras.new("MatchCam")
    cam = bpy.data.objects.new("MatchCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    R = rot(*x[3:6])
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = R[i, j]
        M[i][3] = x[i]
    cam.matrix_world = M
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.sensor_width = 36.0
    cam_data.lens = x[6] * 36.0 / W
    scn = bpy.context.scene
    scn.camera = cam
    scn.render.engine = "CYCLES"
    scn.cycles.samples = a.samples
    scn.cycles.device = "CPU"
    scn.render.film_transparent = True
    scn.render.resolution_x, scn.render.resolution_y = W, H
    scn.render.resolution_percentage = 100
    scn.view_settings.view_transform = "Standard"
    tmp = a.out + ".render.png"
    scn.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    photo = Image.open(a.photo).convert("RGBA").resize((W, H))
    ren = Image.open(tmp).convert("RGBA")
    alpha = ren.split()[3]
    # silhouette edge in magenta
    edge = alpha.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.FIND_EDGES)
    edge = edge.filter(ImageFilter.MaxFilter(3))
    tinted = Image.blend(photo, ren, 0.0)
    comp = photo.copy()
    half = ren.copy()
    half.putalpha(alpha.point(lambda v: int(v * 0.45)))
    comp.alpha_composite(half)
    mag = Image.new("RGBA", (W, H), (255, 0, 255, 255))
    comp.paste(mag, (0, 0), edge)
    if "body" in a.parts:
        draw_lines(comp, x, (W, H), side=1 if x[1] > 0 else -1)
    comp.convert("RGB").save(a.out)
    print("overlay", a.out)


if __name__ == "__main__":
    main()
