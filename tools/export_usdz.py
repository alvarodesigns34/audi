"""Export the car to USDZ (Apple Quick Look / AR). Usage: python tools/export_usdz.py out.usdz [ratio]
ratio < 1 simplifies dense meshes (body 0.65) to fit mobile size limits."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import bpy
from a3 import build
build.build(None)
for col in list(bpy.data.collections):
    if col.name.startswith("_"):
        for ob in list(col.objects): bpy.data.objects.remove(ob, do_unlink=True)
out=sys.argv[1]
ratio=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
if ratio<1.0:
    from a3.core import mesh as _m
    done={}
    for ob in list(bpy.data.objects):
        if ob.type!="MESH" or len(ob.data.polygons)<=2500: continue
        if any(k in ob.name for k in ("Glass","Frit","Lens","Seal","Trim","Badge","Plate","Headlight","Taillight")): continue
        key=ob.data.name
        if key in done:
            ob.data=done[key]; continue
        users=[o for o in bpy.data.objects if o.type=="MESH" and o.data is ob.data]
        m=ob.modifiers.new("dec","DECIMATE")
        m.ratio=0.65 if ob.name.startswith("Body_Shell") else ratio
        _m.apply_modifiers(ob)
        done[key]=ob.data
        for o in users:
            if o is not ob: o.data=ob.data
bpy.ops.wm.usd_export(filepath=out, selected_objects_only=False,
    export_materials=True, generate_preview_surface=True,
    export_uvmaps=False, export_lights=False, export_cameras=False, export_normals=True, export_animation=False, export_shapekeys=False,
    convert_orientation=True, export_global_forward_selection="NEGATIVE_Z", export_global_up_selection="Y")
print("LOOPS", sum(len(o.data.loops) for o in bpy.data.objects if o.type=="MESH"))
print("SIZE", os.path.getsize(out)/1e6, "MB")
