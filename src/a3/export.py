"""glTF 2.0 binary export (for the web viewer)."""
import bpy


def glb(path, include_studio=False, draco=True):
    # hide helper collections (names starting with "_") from export
    hidden = []
    for col in bpy.data.collections:
        if col.name.startswith("_") and not include_studio:
            for ob in col.objects:
                if ob.visible_get():
                    ob.hide_set(True)
                    hidden.append(ob)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_visible=True,
        export_apply=True,
        export_yup=True,
        export_draco_mesh_compression_enable=draco,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_materials="EXPORT",
        export_extras=False,
        export_cameras=False,
        export_lights=False,
    )
    for ob in hidden:
        ob.hide_set(False)
    return path
