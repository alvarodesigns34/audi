"""PBR material library.

All materials are plain Principled BSDF set-ups (plus a few procedural
textures that are baked into the node tree) so that they survive glTF export
(base colour / metallic / roughness / clearcoat / transmission / emission).

Colours are given in sRGB hex and converted to linear.
"""
from __future__ import annotations

import os

import bpy

_CACHE: dict[str, bpy.types.Material] = {}

# Exterior colour options (Audi 2013-2016 colour codes)
PAINTS = {
    # Ibisweiss (T9 / LS9R): solid white, non metallic
    "ibis_white": dict(color="#F2F2EE", metallic=0.0, roughness=0.32, coat=1.0, coat_rough=0.03),
    # Gletscherweiss metallic (2Y / LS9R?): white metallic with fine flake
    "glacier_white": dict(color="#E9EBEA", metallic=0.35, roughness=0.30, coat=1.0, coat_rough=0.03,
                          tex="flake"),
}


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(h: str, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


def principled(name, color="#808080", metallic=0.0, roughness=0.5, coat=0.0,
               coat_rough=0.03, transmission=0.0, ior=1.45, alpha=1.0,
               emission=None, emission_strength=0.0, specular=0.5, sheen=0.0,
               aniso=0.0, normal_noise=0.0, noise_scale=400.0, thin_film=0.0,
               aniso_axis=None, tex=None, emission_tex=None):
    if name in _CACHE and _CACHE[name].name in bpy.data.materials:
        return _CACHE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs[0])
    inp = bsdf.inputs
    inp["Base Color"].default_value = hex_rgba(color)
    inp["Metallic"].default_value = metallic
    inp["Roughness"].default_value = roughness
    inp["IOR"].default_value = ior
    if "Specular IOR Level" in inp:
        inp["Specular IOR Level"].default_value = specular
    if coat:
        inp["Coat Weight"].default_value = coat
        inp["Coat Roughness"].default_value = coat_rough
    if transmission:
        inp["Transmission Weight"].default_value = transmission
    if alpha < 1.0:
        inp["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except AttributeError:
            m.blend_method = "BLEND"
    if emission:
        inp["Emission Color"].default_value = hex_rgba(emission)
        inp["Emission Strength"].default_value = emission_strength
    if sheen:
        inp["Sheen Weight"].default_value = sheen
    if aniso and "Anisotropic" in inp:
        inp["Anisotropic"].default_value = aniso
        if aniso_axis and "Tangent" in inp:
            # circumferential tangent about the object's local axis (turned /
            # ground surfaces: diamond-cut wheel faces, brake discs)
            tg = nt.nodes.new("ShaderNodeTangent")
            tg.direction_type = "RADIAL"
            tg.axis = aniso_axis
            nt.links.new(tg.outputs["Tangent"], inp["Tangent"])
    if tex:
        _surface_texture(m, nt, bsdf, tex, color, roughness)
    elif normal_noise > 0:
        # fine surface structure (leather grain, textured plastics)
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = 6.0
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = normal_noise
        bump.inputs["Distance"].default_value = 0.0005
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], inp["Normal"])
    if emission_tex:
        _emission_texture(m, nt, bsdf, emission_tex, emission_strength)
    m.diffuse_color = hex_rgba(color)
    _CACHE[name] = m
    return m


def _image(nt, path, non_color=True):
    img = bpy.data.images.load(path, check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = img
    n.interpolation = "Linear"
    return n


def _surface_texture(m, nt, bsdf, key, color, roughness):
    """Baked tileable maps (core/textures.py).  Node layouts chosen so the
    glTF exporter writes them: Image -> Normal Map -> BSDF.Normal, and
    Image -> Separate Color (G) -> BSDF.Roughness."""
    from . import textures
    t = textures.surface(key)
    m["uv_tile"] = t["tile"]
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = t["strength"]
    img = _image(nt, t["normal"])
    nt.links.new(img.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if "rough" in t:
        # rescale the stored roughness so its mean matches the material value
        import numpy as np
        from PIL import Image
        arr = np.asarray(Image.open(t["rough"]), float) / 255.0
        arr = np.clip(arr * (roughness / max(arr.mean(), 1e-3)), 0.02, 1.0)
        rp = t["rough"].replace(".png", f"_{int(roughness * 100):02d}.png")
        if not os.path.exists(rp):
            Image.fromarray((arr * 255).astype("uint8")).save(rp)
        ri = _image(nt, rp)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(ri.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    albedo = t.get("ao") or t.get("albedo_var")
    if albedo:
        # colour the grey mask with the material colour into an sRGB base map
        import numpy as np
        from PIL import Image
        lin = np.array(hex_rgba(color)[:3])
        srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
        mask = np.asarray(Image.open(albedo).convert("L"), float)[..., None] / 255.0
        ap = albedo.replace(".png", f"_{color.lstrip('#')}.png")
        if not os.path.exists(ap):
            Image.fromarray((np.clip(mask * srgb, 0, 1) * 255).astype("uint8")).save(ap)
        bi = _image(nt, ap, non_color=False)
        nt.links.new(bi.outputs["Color"], bsdf.inputs["Base Color"])


def _emission_texture(m, nt, bsdf, key, strength):
    from . import textures
    p = textures.content(key)
    img = _image(nt, p, non_color=False)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Emission Strength"].default_value = strength
    m["uv_content"] = key


def get(key: str, paint="ibis_white"):
    """Material by semantic key."""
    lib = {
        # ---- body ----
        "paint": lambda: principled("Paint_Body", **PAINTS[paint]),
        "gap": lambda: principled("Panel_Gap_Dark", "#0A0A0A", roughness=0.8),
        "black_gloss": lambda: principled("Black_HighGloss", "#050505", roughness=0.08, coat=1.0, coat_rough=0.02),
        "black_satin": lambda: principled("Black_Satin_Plastic", "#0C0C0C", roughness=0.45),
        "black_textured": lambda: principled("Black_Textured_Plastic", "#101010", roughness=0.75, tex="grain_plastic"),
        "chrome": lambda: principled("Chrome", "#E8E8E8", metallic=1.0, roughness=0.04),
        "aluminium_matt": lambda: principled("Aluminium_Matt", "#B9BBBD", metallic=1.0, roughness=0.35),
        "aluminium_brushed": lambda: principled("Aluminium_Brushed", "#C3C5C7", metallic=1.0, roughness=0.22, aniso=0.6, tex="brushed"),
        "titanium_grey": lambda: principled("Titanium_Grey_Paint", "#3B3D3F", metallic=0.6, roughness=0.3, coat=1.0),
        "rubber_seal": lambda: principled("Rubber_Seal", "#0B0B0B", roughness=0.85),
        # ---- glazing ----
        "glass_clear": lambda: principled("Glass_Clear", "#EAF2EE", roughness=0.0, transmission=1.0, ior=1.52, alpha=0.18),
        "glass_tinted": lambda: principled("Glass_Privacy", "#202624", roughness=0.0, transmission=0.6, ior=1.52, alpha=0.55),
        "glass_ceramic_frit": lambda: principled("Glass_Frit_Black", "#050505", roughness=0.15),
        "lens_clear": lambda: principled("Lamp_Lens_Clear", "#F4F7F8", roughness=0.0, transmission=1.0, ior=1.49, alpha=0.12),
        "lens_red": lambda: principled("Lamp_Lens_Red", "#7A0008", roughness=0.02, transmission=0.85, ior=1.49, alpha=0.85),
        "lens_red_dark": lambda: principled("Lamp_Lens_Red_Dark", "#3A0004", roughness=0.05, transmission=0.6, ior=1.49, alpha=0.9),
        "lens_amber": lambda: principled("Lamp_Lens_Amber", "#FF8A00", roughness=0.05, transmission=0.7, ior=1.49, alpha=0.6),
        "reflector": lambda: principled("Lamp_Reflector", "#D8D8D8", metallic=1.0, roughness=0.08),
        "lamp_housing": lambda: principled("Lamp_Housing_Black", "#141414", roughness=0.55),
        "led_white": lambda: principled("LED_White", "#FFFFFF", emission="#F2F6FF", emission_strength=0.0, roughness=0.2),
        "led_red": lambda: principled("LED_Red", "#B0000A", emission="#FF0010", emission_strength=0.0, roughness=0.3),
        "led_amber": lambda: principled("LED_Amber", "#C46800", emission="#FF8C00", emission_strength=0.0, roughness=0.3),
        # ---- wheels ----
        "wheel_black": lambda: principled("Wheel_Black_Gloss", "#0B0B0C", metallic=0.2, roughness=0.18, coat=1.0, coat_rough=0.04),
        "wheel_diamond_cut": lambda: principled("Wheel_Diamond_Cut", "#D4D6D8", metallic=1.0, roughness=0.30, aniso=0.85, coat=1.0, coat_rough=0.03, aniso_axis="Y"),
        "wheel_cap": lambda: principled("Wheel_Cap_Grey", "#2A2C2F", metallic=0.6, roughness=0.25, coat=1.0, coat_rough=0.03),
        "wheel_bolt": lambda: principled("Wheel_Bolt_Zinc", "#8E9093", metallic=1.0, roughness=0.32),
        "brake_pad": lambda: principled("Brake_Pad_Lining", "#2E2B29", roughness=0.9, tex="carpet"),
        "tyre": lambda: principled("Tyre_Rubber", "#141414", roughness=0.88, tex="rubber"),
        "tyre_text": lambda: principled("Tyre_Sidewall_Text", "#1C1C1C", roughness=0.7),
        "brake_disc": lambda: principled("Brake_Disc_Cast_Iron", "#6E6C69", metallic=1.0, roughness=0.42, aniso=0.5, aniso_axis="Y", tex="disc"),
        "brake_disc_hat": lambda: principled("Brake_Disc_Hat", "#3D3A36", metallic=0.8, roughness=0.6),
        "caliper": lambda: principled("Brake_Caliper_Black", "#1A1A1A", metallic=0.3, roughness=0.5),
        "steel_dark": lambda: principled("Steel_Dark", "#2A2A2A", metallic=1.0, roughness=0.5),
        "underbody": lambda: principled("Underbody_PVC", "#1C1C1C", roughness=0.9),
        # ---- lights placeholders / badges ----
        "badge_chrome": lambda: principled("Badge_Chrome", "#F0F0F0", metallic=1.0, roughness=0.03),
        "badge_red": lambda: principled("Badge_S_Red", "#C3002F", roughness=0.25, coat=1.0),
        "plate_white": lambda: principled("Plate_White", "#F4F4F4", roughness=0.4),
        "plate_blue": lambda: principled("Plate_EU_Blue", "#003399", roughness=0.4),
        "plate_text": lambda: principled("Plate_Text", "#111111", roughness=0.4),
        # ---- interior ----
        "leather_black": lambda: principled("Leather_Black", "#121212", roughness=0.55, sheen=0.2, tex="leather"),
        "leather_perforated": lambda: principled("Leather_Black_Perforated", "#151515", roughness=0.6, tex="leather_perf"),
        "alcantara": lambda: principled("Alcantara_Black", "#141414", roughness=0.95, sheen=0.6, tex="fabric"),
        "stitch_grey": lambda: principled("Stitching_Rock_Grey", "#7A7A7A", roughness=0.8),
        "soft_touch": lambda: principled("Dash_Soft_Touch", "#161616", roughness=0.7, tex="grain_plastic"),
        "hard_plastic": lambda: principled("Interior_Hard_Plastic", "#141414", roughness=0.6, tex="soft_touch"),
        "piano_black": lambda: principled("Piano_Black", "#030303", roughness=0.05, coat=1.0, coat_rough=0.01),
        "inlay_alu": lambda: principled("Inlay_Aluminium_Trigon", "#A8AAAD", metallic=1.0, roughness=0.3, aniso=0.4, tex="brushed"),
        "headliner": lambda: principled("Headliner_Black", "#1A1A1A", roughness=0.95, sheen=0.5, tex="fabric"),
        "carpet": lambda: principled("Carpet_Black", "#141414", roughness=1.0, tex="carpet"),
        "screen_mmi": lambda: principled("Screen_MMI_Nav", "#000000", roughness=0.05,
                                         emission="#FFFFFF", emission_strength=1.4,
                                         emission_tex="mmi_screen"),
        "screen_fis": lambda: principled("Screen_FIS", "#000000", roughness=0.05,
                                         emission="#FFFFFF", emission_strength=1.2,
                                         emission_tex="fis_screen"),
        "screen": lambda: principled("Screen_MMI", "#04070A", roughness=0.04, emission="#0A1A2A", emission_strength=0.3),
        "gauge_face": lambda: principled("Gauge_Face", "#0A0A0A", roughness=0.4),
        "gauge_marks": lambda: principled("Gauge_Marks", "#EDEDED", roughness=0.4, emission="#FFFFFF", emission_strength=0.6),
        "needle_red": lambda: principled("Gauge_Needle_Red", "#E01010", roughness=0.3, emission="#FF2010", emission_strength=1.0),
        "seatbelt": lambda: principled("Seatbelt_Webbing", "#1A1A1A", roughness=0.85, tex="webbing"),
        "mirror": lambda: principled("Mirror_Glass", "#D0D4D8", metallic=1.0, roughness=0.02),
        # ---- interior (added by the interior package) ----
        "screen_ui": lambda: principled("Screen_UI_White", "#DDE6F0", roughness=0.3, emission="#E8F0FF", emission_strength=1.6),
        "screen_ui_red": lambda: principled("Screen_UI_Audi_Red", "#B0101A", roughness=0.3, emission="#E0202A", emission_strength=1.4),
        "screen_ui_dim": lambda: principled("Screen_UI_Grey", "#4A5560", roughness=0.3, emission="#6A7888", emission_strength=0.7),
        "cluster_glass": lambda: principled("Cluster_Cover_Glass", "#F4F6F8", roughness=0.0, transmission=1.0, ior=1.49, alpha=0.06),
        "rubber_pad": lambda: principled("Rubber_Pad", "#151515", roughness=0.8, tex="rubber"),
        "grille_black": lambda: principled("Speaker_Grille_Black", "#0E0E0E", metallic=0.6, roughness=0.45),
        "headliner_grey": lambda: principled("Headliner_Moon_Silver", "#8E8E8C", roughness=0.95, sheen=0.5, tex="fabric"),
        "mat_edge": lambda: principled("Floor_Mat_Edging", "#1A1A1A", roughness=0.7),
        "knurl_alu": lambda: principled("Aluminium_Knurled", "#C0C2C4", metallic=1.0, roughness=0.28, normal_noise=0.4, noise_scale=6000),
    }
    if key not in lib:
        raise KeyError(f"unknown material {key}")
    return lib[key]()


def reset_cache():
    _CACHE.clear()
