"""Draw observed (magenta) and re-projected (green) feature points on every
photo used in reference/features.json -> out/check_<photo>.png"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from camera_match import project  # noqa
from triangulate import cam, solve_point  # noqa

feats = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "reference", "features.json")))
imgs = {}
for name, obs in feats.items():
    if name.startswith("#"):
        continue
    keys = [k for k in obs if not k.startswith("_")]
    if len(keys) < 2:
        continue
    xyz, err, _ = solve_point(obs, centre=obs.get("_centre", False))
    for k in keys:
        far = k.endswith("!far")
        ph = k[:-4] if far else k
        sol, size, pp = cam(ph)
        if ph not in imgs:
            imgs[ph] = Image.open(os.path.join(ROOT, "reference", "photos", ph + ".jpg")).convert("RGB")
        d = ImageDraw.Draw(imgs[ph])
        s = (1 if sol[1] > 0 else -1) * (-1 if far else 1)
        q = project(sol, np.array([[xyz[0], s * xyz[1], xyz[2]]]), size, pp)[0]
        u, v = obs[k]
        d.ellipse([u - 4, v - 4, u + 4, v + 4], outline=(255, 0, 255), width=2)
        d.line([(q[0] - 5, q[1]), (q[0] + 5, q[1])], fill=(0, 255, 0), width=2)
        d.line([(q[0], q[1] - 5), (q[0], q[1] + 5)], fill=(0, 255, 0), width=2)
        d.line([(u, v), tuple(q)], fill=(255, 255, 0), width=1)
        d.text((u + 6, v - 12), name, fill=(255, 255, 0))
for ph, im in imgs.items():
    im.save(os.path.join(ROOT, "out", f"check_{ph}.png"))
    print("out/check_%s.png" % ph)
