"""Calibrate a photo camera from wheel rim-lip contours with a grid of initial
guesses (robust start for tools/camera_match.py).

Usage:
  python tools/calib.py <name> <photo> --wheel KEY,u,v,rmin,rmax[,skip] [--wheel ...]
        [--side left|right] [--rear] [--manual KEY:u,v;u,v;...]
Writes reference/match_<name>.json (circles + solution).  Wheel keys FL/FR/RL/RR.
--manual replaces the automatic contour of a wheel with hand-digitised points.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import camera_match as cm  # noqa: E402
from make_match import X_AX, Y_CONTACT, Y_LIP  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("photo")
    ap.add_argument("--wheel", action="append", default=[])
    ap.add_argument("--manual", action="append", default=[])
    ap.add_argument("--desc", default="")
    ap.add_argument("--contact", action="append", default=[],
                    help="KEY,u,v tyre contact patch (bottom of the tyre) - removes the up/down ambiguity")
    a = ap.parse_args()
    from PIL import Image
    W, H = Image.open(a.photo).size
    manual = {}
    for m in a.manual:
        k, pts = m.split(":")
        manual[k] = [list(map(float, p.split(","))) for p in pts.split(";") if p]
    circles = []
    for w in a.wheel:
        f = w.split(",")
        key = f[0]
        if key in manual:
            pts = manual[key]
        else:
            u, v, r0, r1 = f[1:5]
            cmd = [sys.executable, os.path.join(HERE, "rim_edge.py"), a.photo, u, v, r0, r1, "--n", "90",
                   "--debug", os.path.join(ROOT, "out", "z", f"rim_{a.name}_{key}.png")]
            if len(f) > 5:
                cmd += ["--skip", f[5]]
            pts = json.loads(subprocess.check_output(cmd))
        side = 1 if key[1] == "L" else -1
        circles.append({"wheel": key, "centre": [X_AX[key[0]], side * Y_LIP[key[0]], 0.306],
                        "radius": "rr", "uv": pts})
    points = []
    for c in a.contact:
        k, u, v = c.split(",")
        points.append({"uv": [float(u), float(v)], "w": 0.5,
                       "xyz": [X_AX[k[0]], (1 if k[1] == "L" else -1) * Y_CONTACT[k[0]], 0.0]})
    cfg = {"image": a.desc or os.path.basename(a.photo), "size": [W, H], "params": {"rr": 0.24},
           "points": points, "circles": circles}
    # camera side from the wheels seen
    ys = [c["centre"][1] for c in circles]
    s = 1.0 if np.mean(ys) > 0 else -1.0
    best = None
    for az in range(0, 360, 20):
        for dist in (6.0, 8.0, 11.0):
            for f in (2000.0, 3000.0, 4500.0):
                t = np.radians(az)
                cx, cy = -1.3 + dist * np.cos(t), dist * np.sin(t)
                if cy * s < 0.5:
                    continue
                # yaw so that the camera looks at the car centre (Blender: looks along -Z,
                # rotation_euler (pitch, 0, yaw) -> view direction (sin(yaw)*sp, -cos(yaw)*sp, -cp))
                yaw = np.arctan2(-(-1.3 - cx), (0 - cy)) if False else np.arctan2(cx + 1.3, -cy) + 0.0
                cfg["init"] = [cx, cy, 1.3, yaw, np.radians(86), 0.0, f]
                try:
                    import scipy.optimize as so
                    old = so.least_squares

                    def ls(*args, **kw):
                        kw["max_nfev"] = 300
                        return old(*args, **kw)
                    cm.least_squares = ls
                    x, err, pn, pp = cm.solve(cfg)
                finally:
                    cm.least_squares = old
                r = np.sqrt((err ** 2).mean())
                up = cm.rot(*x[3:6])[2, 1]          # camera up vector . world z
                if (x[6] > 0 and 0.15 < abs(x[7]) < 0.35 and x[2] > 0.3 and up > 0.8
                        and (best is None or r < best[0])):
                    best = (r, x.copy())
    print("best rms", best[0])
    cfg["init"] = list(map(float, best[1][:7]))
    x, err, pn, pp = cm.solve(cfg)
    print("camera pos", x[:3], "yaw/pitch/roll(deg)", np.degrees(x[3:6]), "f(px)", x[6], "rr", x[7])
    print("rms px", np.sqrt((err ** 2).mean()), "max", np.abs(err).max())
    cfg["solution"] = list(map(float, x))
    json.dump(cfg, open(os.path.join(ROOT, "reference", f"match_{a.name}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
