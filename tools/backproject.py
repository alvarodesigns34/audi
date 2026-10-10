"""Back-project photo pixels onto a vehicle plane y = const (calibrated camera)."""
import json
import sys

import numpy as np

from camera_match import rot


def ray(sol, size, u, v):
    cx, cy, cz, yaw, pitch, roll, f = sol[:7]
    R = rot(yaw, pitch, roll)
    d_cam = np.array([(u - size[0] / 2) / f, -(v - size[1] / 2) / f, -1.0])
    return np.array([cx, cy, cz]), R @ d_cam


def to_plane_y(sol, size, u, v, y):
    o, d = ray(sol, size, u, v)
    t = (y - o[1]) / d[1]
    p = o + t * d
    return p


if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    sol, size = cfg["solution"], cfg["size"]
    for line in sys.stdin:
        if not line.strip() or line.startswith("#"):
            print(line.rstrip())
            continue
        name, u, v, y = line.split()
        p = to_plane_y(sol, size, float(u), float(v), float(y))
        print(f"{name:12s} x={p[0]*1000:8.0f}  z={p[2]*1000:6.0f}")
