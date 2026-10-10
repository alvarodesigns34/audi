"""On-disk cache of expensive generated objects (keyed by source hash).

Exact booleans on the ~0.5 M triangle body take minutes; when the body
sources have not changed the shell is re-used from a cached .blend file.
"""
from __future__ import annotations

import hashlib
import os

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CACHE_DIR = os.path.join(ROOT, "out", "cache")


def key(*files, extra=""):
    h = hashlib.sha1(extra.encode())
    for f in files:
        with open(f, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def path_for(name, k):
    return os.path.join(CACHE_DIR, f"{name}_{k}.blend")


def load(name, k, object_names, collection):
    p = path_for(name, k)
    if not os.path.exists(p):
        return None
    with bpy.data.libraries.load(p, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in object_names]
    out = {}
    for ob in dst.objects:
        if ob is None:
            return None
        col = collection(ob)
        col.objects.link(ob)
        out[ob.name] = ob
    return out


def save(name, k, objects):
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = path_for(name, k)
    bpy.data.libraries.write(p, set(objects), compress=True)
    return p
