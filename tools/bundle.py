"""Bundle adjustment of all calibrated reference photos.

Unknowns
  * per photo: camera position (3), yaw/pitch/roll (3), focal length (1) and
    principal-point offset du, dv (2, weak prior: Commons photos are often
    cropped, so the optical centre is not always the image centre);
  * per photo: visible rim-lip radius ``rr`` (one per photo, the wheel model
    of each car differs);
  * per car (except the reference car WI-RQ 1209): body offset dz and pitch
    about the front axle (ride height differs between cars);
  * per feature of reference/features.json: 3D point (x, y, z), or (x, z)
    for features on the centre plane.

Observations
  * rim-lip contour points of every wheel (match_<photo>.json "circles"):
    distance to the projected circle of radius rr in the rim-lip plane
    (wheels are fixed to the ground, independent of the body pose);
  * point observations of features (left-side coordinates; mirrored for
    photos taken from the right; "<photo>!far" = far side);
  * extra fixed body points of a match file ("points") are ignored here.

Usage: python tools/bundle.py [--write] [--exclude photo,...]
  --write : store the refined cameras (solution + pp) in reference/match_*.json
            and the points in out/features_3d.json
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

REF_CAR = "wi_rq"
CAR_OF = {"sline_front": REF_CAR, "sline_rear": REF_CAR,
          "yellow": "yellow_car", "yellow_rear": "yellow_car",
          "side": "red_show", "rearq": "red_show", "front": "red_show"}
PP_SIGMA = 60.0       # px, prior on the principal point offset of cropped photos
PP_SIGMA_FULL = 3.0   # px, uncropped photos (3:2 frame): optical centre = image centre
POSE_SIGMA = (0.03, 0.015)


def load(exclude=()):
    feats = json.load(open(os.path.join(ROOT, "reference", "features.json")))
    photos = {}
    for fn in sorted(os.listdir(os.path.join(ROOT, "reference"))):
        if fn.startswith("match_") and fn.endswith(".json"):
            name = fn[6:-5]
            if name in exclude:
                continue
            c = json.load(open(os.path.join(ROOT, "reference", fn)))
            if "solution" in c and c.get("circles"):
                photos[name] = c
    return feats, photos


def main():
    write = "--write" in sys.argv
    exclude = ()
    for a in sys.argv[1:]:
        if a.startswith("--exclude"):
            exclude = tuple(a.split("=", 1)[1].split(","))
    feats, photos = load(exclude)
    pnames = sorted(photos)
    cars = sorted({CAR_OF.get(p, p) for p in pnames} - {REF_CAR})
    fnames, fobs, fcentre = [], [], []
    for k, obs in feats.items():
        if k.startswith("#"):
            continue
        items = []
        for o, uv in obs.items():
            if o.startswith("_"):
                continue
            far = o.endswith("!far")
            ph = o[:-4] if far else o
            if ph in photos:
                items.append((ph, far, np.asarray(uv, float)))
        if len(items) >= 2:
            fnames.append(k)
            fobs.append(items)
            fcentre.append(bool(obs.get("_centre", False)))
    # parameter vector layout
    idx = {}
    v0 = []
    for p in pnames:
        sol = photos[p]["solution"]
        pp = photos[p].get("pp")
        W, H = photos[p]["size"]
        du, dv = (pp[0] - W / 2, pp[1] - H / 2) if pp else (0.0, 0.0)
        idx[p] = len(v0)
        v0 += list(sol[:7]) + [du, dv, abs(sol[7]) if len(sol) > 7 else 0.24]
    for c in cars:
        idx["car:" + c] = len(v0)
        v0 += [0.0, 0.0]
    # initial feature points from the previous triangulation
    prev = {}
    pth = os.path.join(ROOT, "out", "features_3d.json")
    if os.path.exists(pth):
        prev = json.load(open(pth))
    for k, centre in zip(fnames, fcentre):
        idx["pt:" + k] = len(v0)
        p = np.asarray(prev.get(k, [-1000, 600, 800]), float) / 1000
        v0 += [p[0], p[2]] if centre else [p[0], abs(p[1]), p[2]]
    v0 = np.array(v0, float)
    th = np.linspace(0, 2 * np.pi, 360, endpoint=False)

    def cam(v, p):
        i = idx[p]
        W, H = photos[p]["size"]
        return v[i:i + 7], (W / 2 + v[i + 7], H / 2 + v[i + 8]), v[i + 9]

    def pose(v, p):
        c = CAR_OF.get(p, p)
        if c == REF_CAR:
            return 0.0, 0.0
        i = idx["car:" + c]
        return v[i], v[i + 1]

    def res(v):
        out = []
        for p in pnames:
            sol, pp, rr = cam(v, p)
            size = photos[p]["size"]
            for C in photos[p]["circles"]:
                cx, cy, cz = (float(c) if not isinstance(c, str) else 0.0 for c in C["centre"])
                ring = np.stack([cx + rr * np.cos(th), np.full_like(th, cy), cz + rr * np.sin(th)], 1)
                q = project(sol, ring, size, pp)
                obs = np.asarray(C["uv"], float)
                d = np.sqrt(((obs[:, None, :] - q[None]) ** 2).sum(-1)).min(1)
                out.append(d / np.sqrt(len(obs) / 20.0))   # each wheel ~ 20 points worth
            i = idx[p]
            W, H = photos[p]["size"]
            sg = PP_SIGMA_FULL if abs(W / H - 1.5) < 0.01 else PP_SIGMA
            out.append(np.array([v[i + 7] / sg, v[i + 8] / sg]))
        for c in cars:
            i = idx["car:" + c]
            out.append(np.array([v[i] / POSE_SIGMA[0], v[i + 1] / POSE_SIGMA[1]]))
        for k, items, centre in zip(fnames, fobs, fcentre):
            i = idx["pt:" + k]
            if centre:
                x, y, z = v[i], 0.0, v[i + 1]
            else:
                x, y, z = v[i:i + 3]
            for ph, far, uv in items:
                sol, pp, _ = cam(v, ph)
                s = (1.0 if sol[1] > 0 else -1.0) * (-1.0 if far else 1.0)
                dz, a = pose(v, ph)
                xx = x * np.cos(a) + z * np.sin(a)
                zz = -x * np.sin(a) + z * np.cos(a) + dz
                out.append(project(sol, np.array([[xx, s * y, zz]]), photos[ph]["size"], pp)[0] - uv)
        return np.concatenate(out)

    # sparsity of the Jacobian (same order as the residuals in res())
    from scipy.sparse import lil_matrix
    rows = []                      # list of (n_residuals, [param indices])
    for p in pnames:
        i = idx[p]
        for C in photos[p]["circles"]:
            rows.append((len(C["uv"]), list(range(i, i + 10))))
        rows.append((2, [i + 7, i + 8]))
    for c in cars:
        i = idx["car:" + c]
        rows.append((2, [i, i + 1]))
    for k, items, centre in zip(fnames, fobs, fcentre):
        i = idx["pt:" + k]
        pp_ = list(range(i, i + (2 if centre else 3)))
        for ph, far, uv in items:
            j = idx[ph]
            cols = list(range(j, j + 9)) + pp_
            c = CAR_OF.get(ph, ph)
            if c != REF_CAR:
                cols += [idx["car:" + c], idx["car:" + c] + 1]
            rows.append((2, cols))
    nres = sum(n for n, _ in rows)
    A = lil_matrix((nres, len(v0)), dtype=int)
    k = 0
    for n, cols in rows:
        for cc in cols:
            A[k:k + n, cc] = 1
        k += n
    r0 = res(v0)
    assert len(r0) == nres, (len(r0), nres)
    r = least_squares(res, v0, method="trf", x_scale="jac", loss="soft_l1", f_scale=3.0,
                      max_nfev=400, jac_sparsity=A)
    v = r.x
    print(f"rms before {np.sqrt((r0 ** 2).mean()):.2f}  after {np.sqrt((r.fun ** 2).mean()):.2f}")
    for p in pnames:
        sol, pp, rr = cam(v, p)
        W, H = photos[p]["size"]
        print(f"{p:12s} pos {np.round(sol[:3], 3)} f {sol[6]:7.0f}  pp-offset "
              f"({pp[0] - W / 2:+5.1f},{pp[1] - H / 2:+5.1f})  rr {rr:.3f}")
    for c in cars:
        dz, a = pose(v, "car:" + c) if False else v[idx["car:" + c]:idx["car:" + c] + 2]
        print(f"car {c:12s} dz {dz * 1000:6.1f} mm  pitch {np.degrees(a):5.2f} deg")
    out3d = {}
    for k, items, centre in zip(fnames, fobs, fcentre):
        i = idx["pt:" + k]
        P = (v[i], 0.0, v[i + 1]) if centre else tuple(v[i:i + 3])
        errs = []
        for ph, far, uv in items:
            sol, pp, _ = cam(v, ph)
            s = (1.0 if sol[1] > 0 else -1.0) * (-1.0 if far else 1.0)
            dz, a = pose(v, ph)
            xx = P[0] * np.cos(a) + P[2] * np.sin(a)
            zz = -P[0] * np.sin(a) + P[2] * np.cos(a) + dz
            e = project(sol, np.array([[xx, s * P[1], zz]]), photos[ph]["size"], pp)[0] - uv
            errs.append(f"{ph[:6]}{'*' if far else ''}:{np.hypot(*e):4.1f}")
        out3d[k] = [round(c * 1000) for c in P]
        print(f"{k:24s} {P[0] * 1000:7.0f} {P[1] * 1000:5.0f} {P[2] * 1000:5.0f}   {' '.join(errs)}")
    if write:
        for p in pnames:
            sol, pp, rr = cam(v, p)
            c = photos[p]
            old = c["solution"]
            c["solution"] = list(map(float, sol)) + [float(np.sign(old[7]) * rr if len(old) > 7 else rr)] \
                + [float(x) for x in old[8:]]
            c["pp"] = [float(pp[0]), float(pp[1])]
            c["bundle"] = "refined by tools/bundle.py (wheel contours + feature points)"
            json.dump(c, open(os.path.join(ROOT, "reference", f"match_{p}.json"), "w"), indent=1)
        json.dump(out3d, open(pth, "w"), indent=1)
        print("written")


if __name__ == "__main__":
    main()
