"""Plot body-shell face centroids coloured by panel label (needs the cached
shell): out/panels_debug.png"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import bpy  # noqa
import numpy as np  # noqa
import matplotlib  # noqa
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa

from a3 import build  # noqa
from a3.body import panels  # noqa

build.build(["body"])
sh = bpy.data.objects["Body_Shell"]
me = sh.data
n = len(me.polygons)
C = np.zeros(n * 3); me.polygons.foreach_get("center", C); C = C.reshape(-1, 3)
N = np.zeros(n * 3); me.polygons.foreach_get("normal", N); N = N.reshape(-1, 3)
lab = panels.classify(C, N)
names = sorted(set(lab))
cmap = plt.get_cmap("tab20")
col = {k: cmap(i % 20) for i, k in enumerate(names)}
fig, ax = plt.subplots(2, 2, figsize=(22, 12))
views = [("side L (y>0)", C[:, 1] > 0.3, 0, 2), ("top", C[:, 2] > 0.6, 0, 1),
         ("front (x>0.2)", C[:, 0] > 0.2, 1, 2), ("rear (x<-2.9)", C[:, 0] < -2.9, 1, 2)]
for a, (t, m, i, j) in zip(ax.ravel(), views):
    for k in names:
        mm = m & (lab == k)
        a.scatter(C[mm, i], C[mm, j], s=0.3, color=col[k], label=k)
    a.set_title(t); a.set_aspect("equal")
ax[0, 0].legend(markerscale=20, fontsize=7, ncol=2)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "out", "panels_debug.png"), dpi=70)
print({k: int((lab == k).sum()) for k in names})
