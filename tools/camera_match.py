"""Pinhole camera calibration from 2D/3D correspondences (photo matching).

Used to place a Blender camera exactly where a reference photograph was taken,
so that renders of the model can be overlaid on the photo to check the
silhouette and feature lines.  Pure numpy/scipy (runs without bpy).

Input JSON:
  {"image": "path.jpg", "size": [W, H],
   "points": [{"uv": [u, v], "xyz": [x, y, z]} | {"uv":..., "xyz_param": "..."}]}
Unknowns: camera position (3), yaw/pitch/roll (3), focal length in px (1)
plus optional named scalar parameters (e.g. visible rim radius).
"""
import json
import sys

import numpy as np
from scipy.optimize import least_squares


def rot(yaw, pitch, roll):
    # camera looks along its local -Z (Blender convention); build world->cam
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rr = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    # base: camera initially looking along +Y world? we use Euler of Blender
    return Rz @ Rx @ Rr  # cam->world for a camera with rotation_euler (pitch,0,yaw)


def project(params, pts, size):
    cx, cy, cz, yaw, pitch, roll, f = params[:7]
    R = rot(yaw, pitch, roll)            # cam -> world
    d = pts - np.array([cx, cy, cz])
    pc = d @ R                            # world -> cam coords
    # camera looks along -Z_cam, +X right, +Y up
    u = size[0] / 2 + f * (pc[:, 0] / -pc[:, 2])
    v = size[1] / 2 - f * (pc[:, 1] / -pc[:, 2])
    return np.stack([u, v], 1)


def solve(cfg):
    size = cfg["size"]
    names = cfg.get("params", {})
    pnames = list(names)

    def pts3d(p):
        out = []
        for P in cfg["points"]:
            xyz = []
            for c in P["xyz"]:
                if isinstance(c, str):
                    xyz.append(eval(c, {}, {n: p[7 + i] for i, n in enumerate(pnames)}))
                else:
                    xyz.append(c)
            out.append(xyz)
        return np.array(out, float)

    uv = np.array([P["uv"] for P in cfg["points"]], float)
    w = np.array([P.get("w", 1.0) for P in cfg["points"]])
    x0 = np.array(cfg.get("init", [-1.3, -8, 1.0, 0.0, np.pi / 2, 0.0, 1500.0])
                  + [names[n] for n in pnames], float)

    def res(p):
        return ((project(p, pts3d(p), size) - uv) * w[:, None]).ravel()

    r = least_squares(res, x0, method="lm", max_nfev=20000)
    err = res(r.x).reshape(-1, 2)
    return r.x, err, pnames


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    x, err, pn = solve(cfg)
    print("camera pos", x[:3], "yaw/pitch/roll(deg)", np.degrees(x[3:6]), "f(px)", x[6])
    for n, v in zip(pn, x[7:]):
        print("param", n, v)
    print("rms px", np.sqrt((err ** 2).sum(1).mean()), "max", np.abs(err).max())
    out = dict(cfg, solution=list(map(float, x)))
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1], "w"), indent=1)
