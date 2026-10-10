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


def project(params, pts, size, pp=None):
    """pp: principal point (u, v) in px; default image centre."""
    cx, cy, cz, yaw, pitch, roll, f = params[:7]
    R = rot(yaw, pitch, roll)            # cam -> world
    d = pts - np.array([cx, cy, cz])
    pc = d @ R                            # world -> cam coords
    # camera looks along -Z_cam, +X right, +Y up
    pu, pv = pp if pp is not None else (size[0] / 2, size[1] / 2)
    u = pu + f * (pc[:, 0] / -pc[:, 2])
    v = pv - f * (pc[:, 1] / -pc[:, 2])
    return np.stack([u, v], 1)


def solve(cfg):
    size = cfg["size"]
    names = cfg.get("params", {})
    pnames = list(names)

    def pts3d(p):
        out = []
        for P in cfg.get("points", []):
            xyz = []
            for c in P["xyz"]:
                if isinstance(c, str):
                    xyz.append(eval(c, {}, {n: p[7 + i] for i, n in enumerate(pnames)}))
                else:
                    xyz.append(c)
            out.append(xyz)
        return np.array(out, float).reshape(-1, 3)

    uv = np.array([P["uv"] for P in cfg.get("points", [])], float).reshape(-1, 2)
    w = np.array([P.get("w", 1.0) for P in cfg.get("points", [])])
    x0 = np.array(cfg.get("init", [-1.3, -8, 1.0, 0.0, np.pi / 2, 0.0, 1500.0])
                  + [names[n] for n in pnames], float)

    def pp_of(p):
        env = {n: p[7 + i] for i, n in enumerate(pnames)}
        return (size[0] / 2 + env.get("du", 0.0), size[1] / 2 + env.get("dv", 0.0))

    circles = cfg.get("circles", [])
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)

    def ev(c, p):
        env = {n: p[7 + i] for i, n in enumerate(pnames)}
        return float(eval(c, {}, env)) if isinstance(c, str) else float(c)

    def circle_res(p):
        out = []
        for C in circles:
            cx, cy, cz = (ev(c, p) for c in C["centre"])
            r = ev(C["radius"], p)
            ring = np.stack([cx + r * np.cos(th), np.full_like(th, cy), cz + r * np.sin(th)], 1)
            q = project(p, ring, size, pp_of(p))
            obs = np.asarray(C["uv"], float)
            d = np.sqrt(((obs[:, None, :] - q[None]) ** 2).sum(-1)).min(1)
            out.append(d * C.get("w", 1.0))
        return np.concatenate(out) if out else np.zeros(0)

    def res(p):
        a = ((project(p, pts3d(p), size, pp_of(p)) - uv) * w[:, None]).ravel() if len(uv) else np.zeros(0)
        return np.concatenate([a, circle_res(p)])

    r = least_squares(res, x0, method="trf", max_nfev=20000, x_scale="jac")
    err = res(r.x)
    return r.x, err, pnames, pp_of(r.x)


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    x, err, pn, pp = solve(cfg)
    print("camera pos", x[:3], "yaw/pitch/roll(deg)", np.degrees(x[3:6]), "f(px)", x[6])
    for n, v in zip(pn, x[7:]):
        print("param", n, v)
    print("rms px", np.sqrt((err ** 2).mean()), "max", np.abs(err).max())
    print("principal point", pp)
    out = dict(cfg, solution=list(map(float, x)), pp=[float(pp[0]), float(pp[1])])
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1], "w"), indent=1)
