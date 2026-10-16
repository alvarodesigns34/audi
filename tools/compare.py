"""Render the full model through the calibrated cameras of reference photos and
compose photo / render comparisons (the main visual validation tool).

Usage:
    python tools/compare.py sline_rear,yellow_rear [--parts body,glass,...]
        [--scale 0.6] [--samples 16] [--crop name:x0,y0,x1,y1] [--out out/cmp]
        [--hide REGEX]

For every match ``reference/match_<name>.json`` it writes
    <out>/<name>_render.png   render with transparent background
    <out>/<name>_blend.png    photo with the render at 50 % and its silhouette edge
    <out>/<name>_pair.png     photo above / render (on the photo) below, cropped
Crops are in photo pixels (before scaling).
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bpy  # noqa
from mathutils import Matrix  # noqa
from PIL import Image, ImageFilter  # noqa

from a3 import build  # noqa
from a3.core import render  # noqa
from camera_match import rot  # noqa


def set_camera(cfg, scale):
    x = cfg["solution"]
    W, H = cfg["size"]
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
    cam_data.clip_start = 0.05
    cam_data.clip_end = 300
    pp = cfg.get("pp")
    if pp:
        cam_data.shift_x = -(pp[0] - W / 2) / W
        cam_data.shift_y = (pp[1] - H / 2) / W
    scn = bpy.context.scene
    scn.camera = cam
    scn.render.resolution_x, scn.render.resolution_y = int(W * scale), int(H * scale)
    scn.render.resolution_percentage = 100
    return cam


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names")
    ap.add_argument("--parts", default="")
    ap.add_argument("--scale", type=float, default=0.6)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--crop", action="append", default=[])
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "cmp"))
    ap.add_argument("--hide", default="")
    ap.add_argument("--clay", action="store_true")
    a = ap.parse_args()
    parts = [p for p in a.parts.split(",") if p] or None
    build.build(parts)
    if a.clay:
        m = bpy.data.materials.get("Paint_Body")
        if m:
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Base Color"].default_value = (0.12, 0.12, 0.125, 1)
    if a.hide:
        for ob in bpy.data.objects:
            if re.search(a.hide, ob.name):
                ob.hide_render = True
    render.studio(floor=False)
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    render.set_device(scn)
    scn.cycles.samples = a.samples
    scn.cycles.use_denoising = True
    scn.render.film_transparent = True
    scn.view_settings.view_transform = "AgX"
    crops = {}
    for c in a.crop:
        n, box = c.split(":")
        crops[n] = tuple(int(v) for v in box.split(","))
    os.makedirs(a.out, exist_ok=True)
    for name in a.names.split(","):
        cfg = json.load(open(os.path.join(ROOT, "reference", f"match_{name}.json")))
        W, H = cfg["size"]
        cam = set_camera(cfg, a.scale)
        p = os.path.join(a.out, f"{name}_render.png")
        scn.render.filepath = p
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        w, h = int(W * a.scale), int(H * a.scale)
        photo = Image.open(os.path.join(ROOT, "reference", "photos", f"{name}.jpg")) \
            .convert("RGBA").resize((w, h), Image.LANCZOS)
        ren = Image.open(p).convert("RGBA")
        alpha = ren.split()[3]
        edge = alpha.point(lambda v: 255 if v > 128 else 0).filter(ImageFilter.FIND_EDGES)
        blend = photo.copy()
        half = ren.copy()
        half.putalpha(alpha.point(lambda v: int(v * 0.5)))
        blend.alpha_composite(half)
        blend.paste(Image.new("RGBA", (w, h), (255, 0, 255, 255)), (0, 0), edge)
        blend.convert("RGB").save(os.path.join(a.out, f"{name}_blend.png"))
        on_photo = photo.copy()
        on_photo.alpha_composite(ren)
        box = crops.get(name)
        if box:
            box = tuple(int(v * a.scale) for v in box)
            ph, rn = photo.crop(box), on_photo.crop(box)
        else:
            ph, rn = photo, on_photo
        pair = Image.new("RGB", (ph.width, ph.height * 2))
        pair.paste(ph.convert("RGB"), (0, 0))
        pair.paste(rn.convert("RGB"), (0, ph.height))
        pair.save(os.path.join(a.out, f"{name}_pair.png"))
        print("[compare]", name)


if __name__ == "__main__":
    main()
