"""Triangulate body feature points from several calibrated photographs.

reference/features.json:
  {"feature_name": {"sline_front": [u, v], "yellow": [u, v], ...,
                    "_centre": true (optional: point on the centre plane y=0)}}

The car is symmetric: a photo taken from the right side observes the mirror
image of a left-side feature, so every point is solved as (x, |y|, z) and
projected with y -> s*y, s = sign of the camera's y (the visible side).
An observation key "<photo>!far" forces the far side (s = -sign(cam y)).

Usage: python tools/triangulate.py [features.json] [--only name,...]
Prints x, y, z in mm (left side, y > 0) and the per-photo residual in px.
"""
import json
import os
import sys

import numpy as np
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from camera_match import project  # noqa: E402

_CAMS = {}


def cam(name):
    if name not in _CAMS:
        for d in (os.path.join(ROOT, "out"), os.path.join(ROOT, "reference")):
            p = os.path.join(d, f"match_{name}.json")
            if os.path.exists(p):
                c = json.load(open(p))
                if "solution" in c:
                    _CAMS[name] = (np.asarray(c["solution"], float), c["size"], c.get("pp"))
                    break
        else:
            raise KeyError(f"no solved camera for {name}")
    return _CAMS[name]


def solve_point(obs, centre=False, init=(-1.0, 0.6, 0.8)):
    items = []
    for k, uv in obs.items():
        if k.startswith("_"):
            continue
        far = k.endswith("!far")
        name = k[:-4] if far else k
        sol, size, pp = cam(name)
        s = 1.0 if sol[1] > 0 else -1.0
        if far:
            s = -s
        items.append((sol, size, s, np.asarray(uv, float), pp))

    def res(p):
        x, y, z = (p[0], 0.0, p[1]) if centre else p
        out = []
        for sol, size, s, uv, pp in items:
            out.append(project(sol, np.array([[x, s * y, z]]), size, pp)[0] - uv)
        return np.concatenate(out)

    x0 = [init[0], init[2]] if centre else list(init)
    best = None
    for dx in (0.0, -2.0, 1.0):
        x0[0] = init[0] + dx
        r = least_squares(res, x0, method="lm" if 2 * len(items) >= len(x0) else "trf")
        if best is None or r.cost < best.cost:
            best = r
    p = best.x
    xyz = (p[0], 0.0, p[1]) if centre else tuple(p)
    err = res(best.x).reshape(-1, 2)
    return np.array(xyz), err, [it[0] for it in items]


def main():
    path = os.path.join(ROOT, "reference", "features.json")
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = set(a.split("=", 1)[1].split(","))
        else:
            path = a
    feats = json.load(open(path))
    out = {}
    for name, obs in feats.items():
        if name.startswith("#") or (only and name not in only):
            continue
        n = len([k for k in obs if not k.startswith("_")])
        if n < 2:
            continue
        xyz, err, _ = solve_point(obs, centre=obs.get("_centre", False))
        e = np.sqrt((err ** 2).sum(1))
        out[name] = [round(v * 1000) for v in xyz]
        print(f"{name:28s} x={xyz[0]*1000:7.0f} y={xyz[1]*1000:6.0f} z={xyz[2]*1000:6.0f}"
              f"   err px: {' '.join(f'{v:4.1f}' for v in e)}")
    json.dump(out, open(os.path.join(ROOT, "out", "features_3d.json"), "w"), indent=1)


# --------------------------------------------------------------------------
# Joint solve (bundle adjustment of the body pose per photo)
# --------------------------------------------------------------------------
# Different cars sit at different ride heights on their wheels (sport vs
# standard suspension, load): every photo except the reference ones gets a
# body offset dz and pitch about the front axle (x=0) applied to the points.
REFERENCE_PHOTOS = {"sline_front", "sline_rear"}   # WI-RQ 1209, S line sport susp.
# photos of the same car share one body pose
CAR_OF = {"yellow": "yellow_car", "yellow_rear": "yellow_car"}


def solve_all(feats, ref=REFERENCE_PHOTOS):
    names, obs_list = [], []
    photos = set()
    for name, obs in feats.items():
        if name.startswith("#"):
            continue
        items = []
        for k, uv in obs.items():
            if k.startswith("_"):
                continue
            far = k.endswith("!far")
            ph = k[:-4] if far else k
            items.append((ph, far, np.asarray(uv, float)))
            photos.add(ph)
        if len(items) >= 2:
            names.append(name)
            obs_list.append((items, obs.get("_centre", False)))
    free = sorted({CAR_OF.get(p, p) for p in photos if p not in ref})
    # initial points from individual solves
    p0 = []
    for name in names:
        xyz, _, _ = solve_point(feats[name], centre=feats[name].get("_centre", False))
        p0.append(xyz)
    p0 = np.array(p0)
    npt = len(names)

    def unpack(v):
        P = v[:3 * npt].reshape(-1, 3)
        pose = {ph: v[3 * npt + 2 * i: 3 * npt + 2 * i + 2] for i, ph in enumerate(free)}
        return P, pose

    def res(v):
        P, pose = unpack(v)
        out = []
        for i, (items, centre) in enumerate(obs_list):
            x, y, z = P[i]
            if centre:
                y = 0.0
            for ph, far, uv in items:
                sol, size, pp = cam(ph)
                s = (1.0 if sol[1] > 0 else -1.0) * (-1.0 if far else 1.0)
                dz, th = pose.get(CAR_OF.get(ph, ph), (0.0, 0.0))
                # body pitch th (rad, nose down +) about the front axle, then lift dz
                xx = x * np.cos(th) + z * np.sin(th)
                zz = -x * np.sin(th) + z * np.cos(th) + dz
                out.append(project(sol, np.array([[xx, s * y, zz]]), size, pp)[0] - uv)
        # weak prior on pose (keeps it bounded when poorly observed)
        for ph in free:
            dz, th = pose[ph]
            out.append(np.array([dz / 0.03, th / 0.015]))
        return np.concatenate(out)

    v0 = np.concatenate([p0.ravel(), np.zeros(2 * len(free))])
    r = least_squares(res, v0, method="trf", x_scale="jac", loss="soft_l1", f_scale=3.0)
    P, pose = unpack(r.x)
    # per-feature residuals
    e = res(r.x)[:-2 * len(free)] if free else res(r.x)
    k = 0
    errs = []
    for items, _ in obs_list:
        n = len(items)
        ee = e[k:k + 2 * n].reshape(-1, 2)
        errs.append(np.sqrt((ee ** 2).sum(1)))
        k += 2 * n
    for i, (items, centre) in enumerate(obs_list):
        if centre:
            P[i, 1] = 0.0
    return names, P, pose, errs


def main_all(path):
    feats = json.load(open(path))
    names, P, pose, errs = solve_all(feats)
    for ph, (dz, th) in pose.items():
        print(f"pose {ph:14s} dz={dz*1000:6.1f} mm  pitch={np.degrees(th):5.2f} deg")
    out = {}
    for n, p, e in zip(names, P, errs):
        out[n] = [round(v * 1000) for v in p]
        print(f"{n:28s} x={p[0]*1000:7.0f} y={p[1]*1000:6.0f} z={p[2]*1000:6.0f}"
              f"   err px: {' '.join(f'{v:4.1f}' for v in e)}")
    json.dump(out, open(os.path.join(ROOT, "out", "features_3d.json"), "w"), indent=1)


if __name__ == "__main__":
    if "--joint" in sys.argv:
        sys.argv.remove("--joint")
        main_all(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reference", "features.json"))
    else:
        main()
