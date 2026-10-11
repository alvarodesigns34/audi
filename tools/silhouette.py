"""Silhouette comparison: model skin (no booleans, fast) vs the colour-segmented
car in a calibrated photo.

Usage: python tools/silhouette.py <match name> [--color red|yellow] [--out out/sil_<name>.png]
           [--lines] [--extra wheels,glass,...]
Draws the photo car outline in cyan, the model outline in magenta and the
characteristic lines (K3..K7) of the model.  Prints the mean outline distance.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import numpy as np  # noqa
from PIL import Image, ImageDraw  # noqa
from scipy import ndimage  # noqa


def photo_mask(path, color):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    if color == "red":
        m = (R > 90) & (R > 1.7 * G) & (R > 1.7 * B)
    elif color == "yellow":
        m = (R > 110) & (G > 80) & (B < 0.55 * G) & (R > 1.05 * B + 60)
    else:
        raise ValueError(color)
    m = ndimage.binary_closing(m, iterations=3)
    m = ndimage.binary_fill_holes(m)
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (1 + int(np.argmax(sizes)))
    return m


def outline(mask):
    return mask & ~ndimage.binary_erosion(mask)


def render_mask(cfg, W, H):
    import bpy
    from mathutils import Matrix
    from camera_match import rot
    x = cfg["solution"]
    cam_data = bpy.data.cameras.new("SilCam")
    cam = bpy.data.objects.new("SilCam", cam_data)
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
    cam_data.clip_end = 200
    scn = bpy.context.scene
    scn.camera = cam
    scn.render.engine = "CYCLES"
    scn.cycles.samples = 1
    scn.cycles.use_denoising = False
    scn.cycles.max_bounces = 0
    scn.render.film_transparent = True
    scn.render.resolution_x, scn.render.resolution_y = W, H
    scn.render.resolution_percentage = 100
    tmp = os.path.join(ROOT, "out", "_sil_tmp.png")
    scn.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    a = np.asarray(Image.open(tmp).convert("RGBA"))[..., 3] > 128
    return a


def build_skin(extra):
    import bpy
    from a3.core import scene, materials
    from a3.body import shell
    scene.reset()
    materials.reset_cache()
    ob, bl, grid = shell.skin_object(spacing=0.01)
    if extra:
        from a3 import build
        # parts that need the body reference use the skin as stand-in
        ctx = build.BuildContext()
        ctx.register("skin_ref", ob)
        import importlib
        for key, mod in build.PARTS:
            if key in extra:
                importlib.import_module(mod).build(ctx)
    return ob


def draw_lines(img, sol, size, side):
    from a3.body.surface import BodyLines
    from camera_match import project
    colors = {"K3": (0, 160, 255), "K4": (0, 255, 120), "K5": (255, 255, 0),
              "K6": (255, 140, 0), "K7": (0, 255, 255)}
    bl = BodyLines()
    xs = np.linspace(bl.x_front, bl.x_rear, 800)
    K = bl.keypoints(xs)
    d = ImageDraw.Draw(img)
    for k, col in colors.items():
        w, z = K[k]
        ok = w > 0.02
        P = np.stack([xs, side * w, z], 1)[ok]
        if len(P) > 1:
            uv = project(np.asarray(sol, float), P, size)
            d.line([tuple(p) for p in uv], fill=col, width=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--color", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--lines", action="store_true")
    ap.add_argument("--outlines", action="store_true")
    ap.add_argument("--crop", nargs=4, type=int)
    ap.add_argument("--extra", default="")
    a = ap.parse_args()
    cfgp = os.path.join(ROOT, "out", f"match_{a.name}.json")
    cfg = json.load(open(cfgp))
    W, H = cfg["size"]
    photo = os.path.join(ROOT, "reference", "photos", f"{a.name}.jpg")
    color = a.color or {"side": "red", "yellow": "yellow", "yellow_rear": "yellow",
                        "front": "red", "rearq": "red", "rearsq": "red", "rearq2": "red", "fl_rear": "red"}.get(a.name)
    if color == "none":
        color = None
    skin = build_skin([e for e in a.extra.split(",") if e])
    mm = render_mask(cfg, W, H)
    img = Image.open(photo).convert("RGB").resize((W, H))
    arr = (np.asarray(img).astype(float) * 0.55).astype(np.uint8)
    arr = arr.copy()
    mo = outline(mm)
    if color:
        pm = photo_mask(photo, color)
        po = outline(pm)
        arr[ndimage.binary_dilation(po)] = (0, 255, 255)
        # mean distance between outlines (both directions)
        dt_p = ndimage.distance_transform_edt(~po)
        dt_m = ndimage.distance_transform_edt(~mo)
        d1 = dt_p[mo].mean()
        d2 = dt_m[po].mean()
        print(f"[sil] {a.name}: model->photo {d1:.1f}px  photo->model {d2:.1f}px")
        # tint areas: model only (magenta), photo only (cyan)
        only_m = mm & ~pm
        only_p = pm & ~mm
        arr[only_m] = (arr[only_m] * 0.5 + np.array([120, 0, 120])).astype(np.uint8)
        arr[only_p] = (arr[only_p] * 0.5 + np.array([0, 90, 90])).astype(np.uint8)
    arr[ndimage.binary_dilation(mo)] = (255, 0, 255)
    out = Image.fromarray(arr)
    if a.lines:
        draw_lines(out, cfg["solution"], (W, H), 1 if cfg["solution"][1] > 0 else -1)
    if a.outlines:
        draw_outlines(out, skin, cfg["solution"], (W, H))
    outp = a.out or os.path.join(ROOT, "out", f"sil_{a.name}.png")
    if a.crop:
        out = out.crop(tuple(a.crop))
    out.save(outp)
    print("[sil]", outp)




# --------------------------------------------------------------------------
# Opening outlines projected onto the skin, then into the photo
# --------------------------------------------------------------------------
def outline_curves(skin, cam_y):
    """3D polylines (list of (name, Nx3, rgb)) of the body openings, on the
    visible side of the car (cam_y sign)."""
    from a3.body import openings as op
    from a3.body import surftools as st
    from a3.core.curves import catmull_rom, resample
    surf = st.Surface(skin)
    s = 1.0 if cam_y > 0 else -1.0
    out = []

    def side_xz(name, pts, col, closed=True):
        p = resample(catmull_rom(np.asarray(pts, float) * 1e-3, 6, closed=closed), 300, closed=closed)
        P, N = surf.project(p, "XZ", side=int(s))
        P = np.array([q for q in P if q is not None])
        if len(P) > 2:
            out.append((name, P, col, closed))

    def front_yz(name, pts, col, closed=True, rear=False, mirror=True):
        p = np.asarray(pts, float) * 1e-3
        if mirror:
            p = p * [s, 1]
        p = resample(catmull_rom(p, 6, closed=closed), 300, closed=closed)
        P, N = surf.project(p, "YZ", side=-1 if rear else 1)
        P = np.array([q for q in P if q is not None])
        if len(P) > 2:
            out.append((name, P, col, closed))

    def top_xy(name, pts, col):
        p = resample(catmull_rom(np.asarray(pts, float) * 1e-3, 6, closed=True), 400, closed=True)
        P, N = surf.project(p, "XY", side=1)
        P = np.array([q for q in P if q is not None])
        if len(P) > 2:
            out.append((name, P, col, True))

    side_xz("dlo", op.DLO_SIDE, (255, 120, 0))
    side_xz("bpil", op.B_PILLAR, (255, 120, 0))
    side_xz("cpil", op.C_PILLAR, (255, 120, 0))
    for nm, line in (("fdf", op.FRONT_DOOR_FRONT), ("db", op.DOOR_BOTTOM), ("bg", op.B_GAP),
                     ("rdr", op.REAR_DOOR_REAR), ("fbs", op.FRONT_BUMPER_SPLIT),
                     ("rbs", op.REAR_BUMPER_SPLIT)):
        side_xz(nm, line, (255, 255, 255), closed=False)
    g = np.asarray(op.GRILLE, float)
    front_yz("grille", np.vstack([g, (g[::-1] * [-1, 1])[1:-1]]), (0, 255, 0), mirror=False)
    P = op.headlight_outline(surf, mirror=s < 0)
    if len(P) > 2:
        out.append(("headlight", P, (255, 255, 0), True))
    for xc, r in ((0.0, op.ARCH_R), (-2.636, op.ARCH_R_REAR)):
        th = np.linspace(-0.25, np.pi + 0.25, 120)
        arc = np.stack([xc + r * 1e-3 * np.cos(th), op.ARCH_CZ * 1e-3 + r * 1e-3 * np.sin(th)], 1)
        PP, NN = surf.project(arc, "XZ", side=int(s))
        PP = np.array([q for q in PP if q is not None])
        if len(PP) > 2:
            out.append(("arch", PP, (255, 0, 160), False))
    front_yz("intake", op.SIDE_INTAKE, (0, 200, 255))
    P, N, _ = op.taillight_outline(surf, mirror=s < 0)
    if len(P) > 2:
        out.append(("taillight", P, (255, 40, 40), True))
    top_xy("windscreen", op.mirror_outline(op.WINDSCREEN), (0, 255, 255))
    P, N = op.rear_glass_outline(surf)
    if len(P) > 2:
        out.append(("rear_window", P, (0, 255, 255), True))
    for nm, P, N, closed in op.tailgate_gap_curves(surf):
        out.append((nm, P, (255, 255, 255), closed))
    d = np.asarray(op.DIFFUSER, float)
    front_yz("diffuser", np.vstack([d[:-1], (d[::-1] * [-1, 1])[1:-1]]), (200, 0, 255), rear=True,
             mirror=False)
    return out


def draw_outlines(img, skin, sol, size):
    from camera_match import project
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(skin, bpy.context.evaluated_depsgraph_get())
    campos = np.asarray(sol[:3], float)
    d = ImageDraw.Draw(img)
    for name, P, col, closed in outline_curves(skin, sol[1]):
        # visibility: segment hidden when the skin blocks the view to it
        vis = []
        for p in P:
            v = campos - p
            dist = np.linalg.norm(v)
            hit = bvh.ray_cast(Vector(p + v / dist * 0.004), Vector(v / dist), dist)
            vis.append(hit[0] is None)
        uv = project(np.asarray(sol, float), P, size)
        n = len(P)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            if vis[i] and vis[j]:
                d.line([tuple(uv[i]), tuple(uv[j])], fill=col, width=2)


if __name__ == "__main__":
    main()
