"""Build a wheel-contour camera-matching config from approximate wheel centres.

Each wheel: (key, u, v, rmin, rmax[, skip]) with key FL/FR/RL/RR.  The rim lip
contour is detected automatically (tools/rim_edge.py) and fitted as a 3D circle
of unknown radius ``rr`` in the plane of the rim lip.
"""
import json
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# rim-lip plane |y|: track/2 + ~half rim width + flange (E)
Y_LIP = {"F": 0.87, "R": 0.855}
X_AX = {"F": 0.0, "R": -2.636}
Y_CONTACT = {"F": 0.7675, "R": 0.753}


def make(name, photo, size, init, wheels, image_desc, contacts=()):
    circles = []
    for w in wheels:
        key, u, v, r0, r1 = w[:5]
        skip = w[5] if len(w) > 5 else ""
        cmd = [sys.executable, os.path.join(HERE, "rim_edge.py"), photo, str(u), str(v), str(r0),
               str(r1), "--n", "90", "--debug", os.path.join(ROOT, "out", "z", f"rim_{name}_{key}.png")]
        if skip:
            cmd += ["--skip", skip]
        pts = json.loads(subprocess.check_output(cmd))
        side = 1 if key[1] == "L" else -1
        circles.append({"wheel": key, "centre": [X_AX[key[0]], side * Y_LIP[key[0]], 0.306],
                        "radius": "rr", "uv": pts})
    points = [{"uv": list(uv), "xyz": [X_AX[k[0]], (1 if k[1] == "L" else -1) * Y_CONTACT[k[0]], 0.0],
               "w": 0.5} for k, uv in contacts]
    cfg = {"image": image_desc, "size": size, "params": {"rr": 0.23}, "init": init,
           "points": points, "circles": circles}
    json.dump(cfg, open(os.path.join(ROOT, "reference", f"match_{name}.json"), "w"), indent=1)
    return cfg
