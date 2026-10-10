"""Export the full-quality car to USDZ (Apple Quick Look / AR on iPhone/iPad).

Usage: python tools/export_usdz.py docs/models/a3_sportback_8v.usdz
No simplification: geometry is exported exactly as built."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import bpy
from a3 import build
build.build(None)
for col in list(bpy.data.collections):
    if col.name.startswith("_"):
        for ob in list(col.objects): bpy.data.objects.remove(ob, do_unlink=True)
out=sys.argv[1]
bpy.ops.wm.usd_export(filepath=out, selected_objects_only=False,
    export_materials=True, generate_preview_surface=True,
    export_uvmaps=True, rename_uvmaps=True, export_textures_mode="NEW", overwrite_textures=True,
    usdz_downscale_size="KEEP", export_lights=False, export_cameras=False, export_normals=True, export_animation=False, export_shapekeys=False,
    convert_orientation=True, export_global_forward_selection="NEGATIVE_Z", export_global_up_selection="Y")
print("LOOPS", sum(len(o.data.loops) for o in bpy.data.objects if o.type=="MESH"))
print("SIZE", os.path.getsize(out)/1e6, "MB")
