"""Index-tracking mesh builder shared by the wheel modules.

The wheel parts are assembled from rings (closed polylines), lofts between
rings and constrained-Delaunay fills of planar-parameterised regions (the
diamond-turned face with its windows, pocket floors, tread block tops...).
Working with explicit indices lets every patch share its boundary vertices
with its neighbours, so the result is welded by construction (no doubles,
no cracks) and normals can be oriented deterministically.

All coordinates handed to the builder are in METRES.
"""
from __future__ import annotations

import math

import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from ..core import mesh as cmesh
from ..core import scene as sc


class MB:
    def __init__(self):
        self.v = []          # list of (n,3) arrays
        self.nv = 0
        self.faces = []      # list of tuples
        self.fmat = []       # material slot per face
        self.sharp = []      # explicit sharp edges (pairs)

    # ---------------------------------------------------------------- verts
    def add(self, pts):
        pts = np.asarray(pts, float).reshape(-1, 3)
        i0 = self.nv
        self.v.append(pts)
        self.nv += len(pts)
        return np.arange(i0, i0 + len(pts))

    def face(self, idx, mat=0):
        self.faces.append(tuple(int(i) for i in idx))
        self.fmat.append(mat)

    # ---------------------------------------------------------------- lofts
    def loft(self, a, b, mat=0, closed=True, flip=False):
        """Quads between two index rings of equal length."""
        a = np.asarray(a)
        b = np.asarray(b)
        n = len(a)
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            q = (a[i], a[j], b[j], b[i])
            if flip:
                q = q[::-1]
            self.face(q, mat)

    def grid(self, rings, mat=0, closed=True, flip=False):
        for a, b in zip(rings[:-1], rings[1:]):
            self.loft(a, b, mat, closed, flip)

    def fan(self, ring, centre_pt, mat=0, flip=False):
        c = self.add([centre_pt])[0]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            t = (ring[i], ring[j], c)
            self.face(t[::-1] if flip else t, mat)
        return c

    def cap(self, ring, mat=0, flip=False):
        r = list(ring)
        self.face(r[::-1] if flip else r, mat)

    # ---------------------------------------------------------------- CDT
    def cdt_fill(self, loops2d, loop_idx, interior2d, lift, mat=0, flip=False,
                 min_dist=None):
        """Triangulate a 2D domain and lift it to 3D.

        loops2d   : list of (n,2) arrays; loops2d[0] outer boundary, others holes
                    (any orientation).  May be [None-outer] -> convex hull with holes.
        loop_idx  : matching list of index arrays (vertices already in the builder)
        interior2d: (m,2) extra points (filtered against boundary distance)
        lift      : f(pts2d (k,2)) -> (k,3) for NEW interior vertices
        Triangles are CCW in 2D; ``flip`` reverses them.
        """
        loops2d = [np.asarray(l, float) for l in loops2d]
        allb = np.vstack(loops2d)
        interior = np.asarray(interior2d, float).reshape(-1, 2)
        if len(interior):
            inside = point_in_domain(interior, loops2d)
            interior = interior[inside]
            if min_dist and len(interior):
                d = min_dist_to_polylines(interior, loops2d)
                interior = interior[d > min_dist]
        coords = [Vector((float(x), float(y))) for x, y in np.vstack([allb, interior])] \
            if len(interior) else [Vector((float(x), float(y))) for x, y in allb]
        edges = []
        o = 0
        for l in loops2d:
            n = len(l)
            edges += [(o + i, o + (i + 1) % n) for i in range(n)]
            o += n
        nb = o
        out = delaunay_2d_cdt(coords, edges, [], 0, 1e-9)
        ocoords, _, ofaces, oorig = out[0], out[1], out[2], out[3]
        bidx = np.concatenate([np.asarray(i) for i in loop_idx])
        new_int = self.add(lift(interior)) if len(interior) else np.zeros(0, int)
        # map output verts -> builder indices
        omap = np.empty(len(ocoords), int)
        extra = []
        for k, orig in enumerate(oorig):
            if orig:
                i = orig[0]
                omap[k] = bidx[i] if i < nb else new_int[i - nb]
            else:
                extra.append(k)
        if extra:
            p = np.array([[ocoords[k].x, ocoords[k].y] for k in extra])
            ids = self.add(lift(p))
            omap[extra] = ids
        tris = np.array(ofaces)
        oc = np.array([[c.x, c.y] for c in ocoords])
        cen = oc[tris].mean(axis=1)
        keep = point_in_domain(cen, loops2d)
        for t in tris[keep]:
            tt = omap[t]
            if len(set(tt)) < 3:
                continue
            self.face(tt[::-1] if flip else tt, mat)

    # ---------------------------------------------------------------- output
    def build(self, name, materials, collection, smooth_angle=35.0):
        verts = np.vstack(self.v) if self.v else np.zeros((0, 3))
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(verts))
        me.vertices.foreach_set("co", verts.ravel())
        nl = np.array([len(f) for f in self.faces])
        me.loops.add(int(nl.sum()))
        me.polygons.add(len(self.faces))
        me.loops.foreach_set("vertex_index", np.concatenate([np.asarray(f) for f in self.faces]))
        ls = np.concatenate([[0], np.cumsum(nl)[:-1]])
        me.polygons.foreach_set("loop_start", ls)
        me.update(calc_edges=True)
        me.validate(clean_customdata=False)
        for m in materials:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", np.asarray(self.fmat, int)[:len(me.polygons)])
        me.update()
        ob = bpy.data.objects.new(name, me)
        sc.link(ob, collection)
        cmesh.shade_smooth(ob, smooth_angle)
        return ob


# ------------------------------------------------------------------ 2D utils

def point_in_poly(pts, poly):
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    px, py = poly[:, 0][None], poly[:, 1][None]
    qx, qy = np.roll(poly[:, 0], -1)[None], np.roll(poly[:, 1], -1)[None]
    cond = (py > y) != (qy > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = px + (y - py) * (qx - px) / (qy - py)
    return (np.sum(cond & (x < xi), axis=1) % 2) == 1


def point_in_domain(pts, loops):
    ins = point_in_poly(pts, loops[0])
    for h in loops[1:]:
        ins &= ~point_in_poly(pts, h)
    return ins


def min_dist_to_polylines(pts, loops):
    best = np.full(len(pts), np.inf)
    for l in loops:
        a = l
        b = np.roll(l, -1, axis=0)
        ab = b - a
        L2 = (ab ** 2).sum(1) + 1e-30
        for s in range(0, len(a), 256):
            aa, bb_, ll = a[s:s + 256], ab[s:s + 256], L2[s:s + 256]
            ap = pts[:, None, :] - aa[None]
            t = np.clip((ap * bb_[None]).sum(-1) / ll[None], 0, 1)
            d = np.linalg.norm(ap - t[..., None] * bb_[None], axis=-1).min(1)
            best = np.minimum(best, d)
    return best


def resample_closed(pts, n):
    """Uniform arc-length resampling of a closed 2D/3D polyline."""
    p = np.asarray(pts, float)
    q = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(q, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, q[:, k]) for k in range(p.shape[1])], 1)


def resample_open(pts, n):
    p = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, p[:, k]) for k in range(p.shape[1])], 1)


def catmull_closed(P, n_per=12):
    P = np.asarray(P, float)
    N = len(P)
    out = []
    for i in range(N):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % N], P[(i + 2) % N]
        t01 = np.linalg.norm(p1 - p0) ** 0.5 + 1e-9
        t12 = np.linalg.norm(p2 - p1) ** 0.5 + 1e-9
        t23 = np.linalg.norm(p3 - p2) ** 0.5 + 1e-9
        m1 = (p2 - p1 + t12 * ((p1 - p0) / t01 - (p2 - p0) / (t01 + t12)))
        m2 = (p2 - p1 + t12 * ((p3 - p2) / t23 - (p3 - p1) / (t12 + t23)))
        for k in range(n_per):
            t = k / n_per
            h00 = 2 * t ** 3 - 3 * t ** 2 + 1
            h10 = t ** 3 - 2 * t ** 2 + t
            h01 = -2 * t ** 3 + 3 * t ** 2
            h11 = t ** 3 - t ** 2
            out.append(h00 * p1 + h10 * m1 + h01 * p2 + h11 * m2)
    return np.array(out)


def offset_closed(pts, d):
    """Offset a CCW closed 2D polyline by d along its outward normal
    (positive d grows a CCW polygon)."""
    p = np.asarray(pts, float)
    t = np.roll(p, -1, 0) - np.roll(p, 1, 0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    n = np.stack([t[:, 1], -t[:, 0]], 1)   # right normal = outward for CCW
    return p + n * np.asarray(d).reshape(-1, 1) if np.ndim(d) else p + n * d


def ccw(pts):
    p = np.asarray(pts)
    a = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if a > 0 else p[::-1].copy()


def circle(r, n, c=(0.0, 0.0), start=0.0):
    t = start + np.arange(n) * 2 * math.pi / n
    return np.stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)], 1)


def polar_grid(r0, r1, step, n_min=24, jitter=0.0, seed=0):
    """Roughly uniform point cloud over an annulus (for CDT interiors)."""
    pts = []
    rs = np.arange(r0 + step * 0.5, r1, step)
    for k, r in enumerate(rs):
        n = max(n_min, int(2 * math.pi * r / step))
        t = (np.arange(n) + 0.5 * (k % 2)) * 2 * math.pi / n
        pts.append(np.stack([r * np.cos(t), r * np.sin(t)], 1))
    return np.vstack(pts) if pts else np.zeros((0, 2))


def rect_grid(x0, x1, y0, y1, step):
    xs = np.arange(x0 + step * 0.5, x1, step)
    ys = np.arange(y0 + step * 0.5, y1, step)
    X, Y = np.meshgrid(xs, ys)
    return np.stack([X.ravel(), Y.ravel()], 1)
