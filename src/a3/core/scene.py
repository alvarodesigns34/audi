"""Scene / collection management."""
from __future__ import annotations

import bpy

_ROOT = "A3_Sportback_8V"


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.unit_settings.system = "METRIC"
    scn.unit_settings.scale_length = 1.0
    root = bpy.data.collections.new(_ROOT)
    scn.collection.children.link(root)
    return root


def root():
    return bpy.data.collections.get(_ROOT) or bpy.context.scene.collection


def collection(path: str):
    """Get/create nested collection "Exterior/Body"."""
    parent = root()
    for part in path.split("/"):
        name = part
        col = bpy.data.collections.get(name)
        if col is None:
            col = bpy.data.collections.new(name)
            parent.children.link(col)
        parent = col
    return parent


def link(ob, col=None):
    if isinstance(col, str):
        col = collection(col)
    (col or root()).objects.link(ob)
    return ob


def delete(ob):
    me = ob.data if ob.type == "MESH" else None
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def temp_collection(name="_tmp_cutters"):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col
