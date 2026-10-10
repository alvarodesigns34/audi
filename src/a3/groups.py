"""Final assembly step: real body panels, exploded-view groups and labels.

* The cut body shell is split into its panels (body/panels.py) and the side
  glass into front-door / rear-door / quarter lights.
* Every object is assigned to an assembly group.  Each group becomes an empty
  ("G_<id>") that parents its objects, carrying glTF extras:
      group, label (Spanish), explode = [x, y, z] in glTF axes (Y up), metres
  so the web viewer can separate the parts progressively (0 = assembled,
  1 = exploded) along a per-group vector.
* Every mesh gets a Spanish "label" for the HUD.
"""
from __future__ import annotations

import re

import bmesh
import bpy
import numpy as np

from .core import scene
from .body import openings as op

# group id -> (Spanish label, explode vector in VEHICLE axes (x fwd, y left, z up), m)
GROUPS = {
    "carroceria": ("Carrocería (casco: techo, laterales, pilares)", (0.0, 0.0, 0.55)),
    "capo": ("Capó", (0.30, 0.0, 0.80)),
    "rejilla_parabrisas": ("Rejilla del parabrisas y limpiaparabrisas", (0.10, 0.0, 0.62)),
    "parabrisas": ("Parabrisas", (0.30, 0.0, 1.00)),
    "paragolpes_del": ("Paragolpes delantero S line", (0.90, 0.0, 0.0)),
    "faro_izq": ("Faro izquierdo (xenón plus)", (0.60, 0.32, 0.12)),
    "faro_der": ("Faro derecho (xenón plus)", (0.60, -0.32, 0.12)),
    "aleta_izq": ("Aleta delantera izquierda", (0.18, 0.60, 0.05)),
    "aleta_der": ("Aleta delantera derecha", (0.18, -0.60, 0.05)),
    "puerta_di": ("Puerta delantera izquierda", (0.0, 0.90, 0.0)),
    "puerta_dd": ("Puerta delantera derecha", (0.0, -0.90, 0.0)),
    "puerta_ti": ("Puerta trasera izquierda", (-0.10, 0.90, 0.0)),
    "puerta_td": ("Puerta trasera derecha", (-0.10, -0.90, 0.0)),
    "faldon_izq": ("Faldón lateral S line izquierdo", (0.0, 0.62, -0.15)),
    "faldon_der": ("Faldón lateral S line derecho", (0.0, -0.62, -0.15)),
    "custodia_izq": ("Luna de custodia izquierda", (-0.25, 0.65, 0.35)),
    "custodia_der": ("Luna de custodia derecha", (-0.25, -0.65, 0.35)),
    "porton": ("Portón trasero con luneta y alerón", (-0.80, 0.0, 0.60)),
    "paragolpes_tras": ("Paragolpes trasero con difusor S line", (-0.95, 0.0, 0.0)),
    "piloto_izq": ("Piloto trasero izquierdo (LED)", (-0.62, 0.35, 0.10)),
    "piloto_der": ("Piloto trasero derecho (LED)", (-0.62, -0.35, 0.10)),
    "rueda_di": ("Rueda delantera izquierda", (0.0, 0.75, 0.0)),
    "rueda_dd": ("Rueda delantera derecha", (0.0, -0.75, 0.0)),
    "rueda_ti": ("Rueda trasera izquierda", (0.0, 0.75, 0.0)),
    "rueda_td": ("Rueda trasera derecha", (0.0, -0.75, 0.0)),
    "freno_di": ("Freno delantero izquierdo", (0.0, 0.42, 0.0)),
    "freno_dd": ("Freno delantero derecho", (0.0, -0.42, 0.0)),
    "freno_ti": ("Freno trasero izquierdo", (0.0, 0.42, 0.0)),
    "freno_td": ("Freno trasero derecho", (0.0, -0.42, 0.0)),
    "suspension": ("Suspensión y dirección", (0.0, 0.0, -0.30)),
    "bajos": ("Bajos, pasos de rueda y protecciones", (0.0, 0.0, -0.45)),
    "escape": ("Sistema de escape", (-0.20, 0.0, -0.55)),
    "motor": ("Motor 2.0 TDI y vano motor", (0.25, 0.0, 0.25)),
    "maletero": ("Maletero", (-0.30, 0.0, 0.25)),
    "salpicadero": ("Salpicadero, cuadro, MMI y climatizador", (0.40, 0.0, 0.32)),
    "volante": ("Volante y columna", (-0.30, 0.0, 0.30)),
    "consola": ("Consola central y palanca S tronic", (0.0, 0.0, 0.22)),
    "asiento_di": ("Asiento delantero izquierdo (S line)", (-0.10, 0.18, 0.62)),
    "asiento_dd": ("Asiento delantero derecho (S line)", (-0.10, -0.18, 0.62)),
    "asiento_tras": ("Asiento trasero", (-0.35, 0.0, 0.70)),
    "techo_interior": ("Techo interior, parasoles y retrovisor", (0.0, 0.0, 0.66)),
    "guarnecidos": ("Guarnecidos de pilares", (0.0, 0.0, 0.50)),
    "cinturones": ("Cinturones de seguridad", (-0.05, 0.0, 0.40)),
    "suelo": ("Moqueta, alfombrillas y umbrales", (0.0, 0.0, 0.0)),
    "pedales": ("Pedalier", (0.15, 0.0, 0.10)),
}

# (regex on object name, group).  First match wins.  {s} = side suffix.
RULES = [
    (r"^Body_Shell$|^Trim_DLO_Surround|^Roof_Antenna|^Body_Skin", "carroceria"),
    (r"^Body_Hood$", "capo"),
    (r"^Body_Cowl$|^Wiper_", "rejilla_parabrisas"),
    (r"^Glass_Windscreen|^Seal_Windscreen", "parabrisas"),
    (r"^Body_Bumper_F$|^Grille_|^Badge_Rings$|^Badge_Rings_\d$|^Plate$|^Plate_(EU_Band|Holder|Text)$"
     r"|^Intake_|^Fog_|^Front_Lip|^Washer_|^Sensor_F", "paragolpes_del"),
    (r"^Headlight_.*\.L$", "faro_izq"), (r"^Headlight_.*\.R$", "faro_der"),
    (r"^Body_Fender\.L$|^Badge_SLine\.L", "aleta_izq"),
    (r"^Body_Fender\.R$|^Badge_SLine\.R", "aleta_der"),
    (r"^Body_Door_FL$|^Door_FL_|^Door_Handle_F\.L$|^Mirror_(Head|Foot|Glass|Indicator)\.L$"
     r"|^Glass_Front\.L$|^Trim_BPillar\.L$|^Trim_MirrorSail\.L$", "puerta_di"),
    (r"^Body_Door_FR$|^Door_FR_|^Door_Handle_F\.R$|^Mirror_(Head|Foot|Glass|Indicator)\.R$"
     r"|^Glass_Front\.R$|^Trim_BPillar\.R$|^Trim_MirrorSail\.R$", "puerta_dd"),
    (r"^Body_Door_RL$|^Door_RL_|^Door_Handle_R\.L$|^Glass_Rear\.L$|^Trim_CPillar\.L$", "puerta_ti"),
    (r"^Body_Door_RR$|^Door_RR_|^Door_Handle_R\.R$|^Glass_Rear\.R$|^Trim_CPillar\.R$", "puerta_td"),
    (r"^Body_Skirt\.L$", "faldon_izq"), (r"^Body_Skirt\.R$", "faldon_der"),
    (r"^Glass_Quarter\.L$", "custodia_izq"), (r"^Glass_Quarter\.R$", "custodia_der"),
    (r"^Body_Tailgate$|^Glass_RearWindow|^Seal_RearWindow|^Roof_Spoiler|^Brake_Light_High"
     r"|^Rear_Wiper|^Badge_Rings_Rear|^Plate_Rear|^Badge_Tailgate", "porton"),
    (r"^Body_Bumper_R$|^Diffuser_|^Sensor_R|^Exhaust_(Tip|Inner)", "paragolpes_tras"),
    (r"^Taillight_.*\.L$", "piloto_izq"), (r"^Taillight_.*\.R$", "piloto_der"),
    (r"^Wheel_FL", "rueda_di"), (r"^Wheel_FR", "rueda_dd"),
    (r"^Wheel_RL", "rueda_ti"), (r"^Wheel_RR", "rueda_td"),
    (r"^Brake_FL", "freno_di"), (r"^Brake_FR", "freno_dd"),
    (r"^Brake_RL", "freno_ti"), (r"^Brake_RR", "freno_td"),
    (r"^Susp_|^Steer_|^Subframe|^Driveshaft", "suspension"),
    (r"^Arch_Liner|^Underbody|^Fuel_Tank|^Heat_Shield", "bajos"),
    (r"^Exhaust_(?!Tip|Inner)|^DPF", "escape"),
    (r"^Bay_|^Radiator|^Engine_|^Battery|^Intercooler|^Gearbox|^Turbo|^Airbox|^Coolant"
     r"|^Brake_Fluid|^Washer_Filler|^Strut_Tower", "motor"),
    (r"^Boot_|^Trim_ParcelShelf", "maletero"),
    (r"^Dash_|^Vent_|^Cluster_|^MMI_|^Climate_|^Trim_APillar", "salpicadero"),
    (r"^Steering_", "volante"),
    (r"^Console_", "consola"),
    (r"^Seat_FL_", "asiento_di"), (r"^Seat_FR_", "asiento_dd"),
    (r"^Rear_(Backrest|Cushion|Headrest|Stitching)", "asiento_tras"),
    (r"^Trim_Headliner|^Trim_RoofConsole|^Trim_RearDomeLight|^Visor_|^Grab_Handle"
     r"|^Mirror_(Frame|Glass|Housing|SensorCover|Stem)$", "techo_interior"),
    (r"^Trim_(BPillar|CPillar|DPillar|Quarter)_", "guarnecidos"),
    (r"^Belt_", "cinturones"),
    (r"^Trim_(Carpet|Sill|ScuffPlate)|^Mat_", "suelo"),
    (r"^Pedal_", "pedales"),
]

# Spanish part labels (regex -> label); first match wins.
LABELS = [
    (r"^Body_Shell$", "Carrocería (techo, laterales y pilares)"),
    (r"^Body_Hood$", "Capó con nervios en V"),
    (r"^Body_Cowl$", "Rejilla del parabrisas"),
    (r"^Body_Bumper_F$", "Paragolpes delantero S line"),
    (r"^Body_Bumper_R$", "Paragolpes trasero S line"),
    (r"^Body_Fender\.(L|R)$", "Aleta delantera"),
    (r"^Body_Door_F", "Puerta delantera"), (r"^Body_Door_R", "Puerta trasera"),
    (r"^Body_Skirt", "Faldón lateral S line"),
    (r"^Body_Tailgate$", "Portón trasero"),
    (r"^Glass_Windscreen$", "Parabrisas laminado (4,5 mm)"),
    (r"^Glass_Windscreen_Frit", "Serigrafía cerámica del parabrisas"),
    (r"^Glass_RearWindow$", "Luneta térmica"),
    (r"^Glass_RearWindow_Frit", "Serigrafía cerámica de la luneta"),
    (r"^Glass_Front", "Luna de puerta delantera"), (r"^Glass_Rear", "Luna de puerta trasera"),
    (r"^Glass_Quarter", "Luna de custodia"),
    (r"^Seal_", "Junta de la luna"),
    (r"^Trim_DLO_Surround", "Moldura de ventanillas"),
    (r"^Trim_BPillar\.", "Embellecedor negro del pilar B"),
    (r"^Trim_CPillar\.", "Embellecedor del pilar C"),
    (r"^Trim_MirrorSail", "Triángulo del retrovisor"),
    (r"^Grille_Frame", "Marco de la parrilla Singleframe"),
    (r"^Grille_Slat", "Lamas de la parrilla (negro brillo)"),
    (r"^Grille_Rib", "Nervios verticales de la parrilla"),
    (r"^Grille_Back", "Fondo de la parrilla"),
    (r"^Badge_Rings$|^Badge_Rings_\d$", "Aros de Audi (delanteros)"),
    (r"^Badge_Rings_Rear", "Aros de Audi (portón)"),
    (r"^Badge_SLine", "Emblema S line"),
    (r"^Plate_Rear", "Matrícula trasera"), (r"^Plate", "Matrícula delantera"),
    (r"^Intake_Honeycomb", "Rejilla panal de la toma lateral"),
    (r"^Intake_Blade", "Lama de la toma lateral S line"),
    (r"^Intake_Back", "Fondo de la toma lateral"),
    (r"^Fog_", "Faro antiniebla"),
    (r"^Front_Lip", "Labio inferior del paragolpes"),
    (r"^Headlight_Lens", "Cristal del faro"),
    (r"^Headlight_DRL", "Guía de luz diurna LED"),
    (r"^Headlight_Indicator", "Intermitente LED"),
    (r"^Headlight_Projector", "Proyector bi-xenón"),
    (r"^Headlight_Reflector", "Reflector de luz larga"),
    (r"^Headlight_Bezel", "Embellecedor interior del faro"),
    (r"^Headlight_Brow", "Ceja cromada del faro"),
    (r"^Headlight_", "Carcasa del faro"),
    (r"^Taillight_Lens", "Cristal del piloto trasero"),
    (r"^Taillight_LED", "Guía de luz LED del piloto"),
    (r"^Taillight_Reverse", "Luz de marcha atrás"),
    (r"^Taillight_", "Carcasa del piloto trasero"),
    (r"^Brake_Light_High", "Tercera luz de freno"),
    (r"^Roof_Spoiler", "Alerón de techo S line"),
    (r"^Roof_Antenna", "Antena de aleta de tiburón"),
    (r"^Rear_Wiper", "Limpialuneta"),
    (r"^Wiper_", "Limpiaparabrisas"),
    (r"^Diffuser_", "Difusor trasero S line"),
    (r"^Exhaust_Tip", "Salida de escape cromada"),
    (r"^Exhaust_CentreSilencer", "Silenciador central"),
    (r"^Exhaust_RearSilencer", "Silenciador trasero"),
    (r"^Exhaust_Flex", "Junta flexible del escape"),
    (r"^Exhaust_Hanger", "Silentblock del escape"),
    (r"^Exhaust_", "Tubo de escape"),
    (r"^DPF_", "Catalizador de oxidación y filtro de partículas (FAP)"),
    (r"^Heat_Shield", "Pantalla térmica"),
    (r"^Fuel_Tank", "Depósito de combustible (50 l)"),
    (r"^Susp_F._Strut", "Amortiguador McPherson"),
    (r"^Susp_F._Spring|^Susp_R._Spring", "Muelle helicoidal"),
    (r"^Susp_F._TopMount", "Copela de amortiguador"),
    (r"^Susp_F._Wishbone", "Trapecio inferior"),
    (r"^Susp_F._DropLink", "Bieleta de estabilizadora"),
    (r"^Susp_._AntiRollBar", "Barra estabilizadora"),
    (r"^Susp_R._TrailingArm", "Brazo longitudinal (multibrazo trasero)"),
    (r"^Susp_R._SpringLink", "Brazo transversal inferior (soporte de muelle)"),
    (r"^Susp_R._UpperLink", "Brazo transversal superior"),
    (r"^Susp_R._ToeLink", "Bieleta de convergencia"),
    (r"^Susp_R._Damper", "Amortiguador trasero"),
    (r"^Susp_", "Suspensión"),
    (r"^Steer_Rack", "Cremallera de dirección (asistencia eléctrica)"),
    (r"^Steer_TieRod", "Bieleta de dirección"),
    (r"^Steer_", "Dirección"),
    (r"^Driveshaft", "Palier"),
    (r"^Subframe_CrashBeam|^Subframe_CrashBox", "Travesaño de impacto"),
    (r"^Subframe", "Subchasis"),
    (r"^Engine_Cover", "Tapa del motor TDI"),
    (r"^Engine_Block", "Bloque motor 2.0 TDI EA288 (fundición)"),
    (r"^Engine_Head", "Culata de 16 válvulas"),
    (r"^Engine_Sump", "Cárter de aceite"),
    (r"^Engine_Timing", "Tapa de la correa de distribución"),
    (r"^Engine_Alternator", "Alternador"),
    (r"^Engine_ACCompressor", "Compresor del aire acondicionado"),
    (r"^Engine_IntakeManifold|^Intercooler", "Colector de admisión con intercooler por agua"),
    (r"^Engine_EGR", "Enfriador EGR"),
    (r"^Engine_Injector", "Inyector common-rail"),
    (r"^Turbo_", "Turbocompresor de geometría variable"),
    (r"^Engine_", "Motor 2.0 TDI"),
    (r"^Gearbox", "Cambio S tronic DQ250 (6 vel., doble embrague)"),
    (r"^Battery", "Batería"),
    (r"^Airbox", "Filtro de aire"),
    (r"^Coolant", "Depósito de expansión del refrigerante"),
    (r"^Brake_Fluid", "Depósito del líquido de frenos"),
    (r"^Washer_Filler", "Llenado del lavaparabrisas"),
    (r"^Radiator_Fan", "Electroventilador"),
    (r"^Radiator", "Radiador"),
    (r"^Strut_Tower", "Torreta de amortiguador"),
    (r"^Boot_", "Maletero"),
    (r"^Mirror_Head", "Carcasa del retrovisor exterior"),
    (r"^Mirror_Foot", "Pie del retrovisor"),
    (r"^Mirror_Indicator", "Intermitente LED del retrovisor"),
    (r"^Mirror_Glass\.", "Espejo del retrovisor"),
    (r"^Door_Handle", "Tirador de puerta"),
    (r"^Wheel_.._Rim", "Llanta Audi exclusive 18\" 5-arm rotor (8J ET46)"),
    (r"^Wheel_.._Tyre", "Neumático 225/40 R18"),
    (r"^Wheel_.._Hardware", "Tornillos y tapacubos"),
    (r"^Brake_F._Disc", "Disco de freno ventilado 312 × 25 mm"),
    (r"^Brake_R._Disc", "Disco de freno macizo 272 × 10 mm"),
    (r"^Brake_.._Caliper", "Pinza de freno"),
    (r"^Brake_.._Hub", "Buje"),
    (r"^Arch_Liner", "Paso de rueda (pase interior)"),
    (r"^Underbody", "Protección de bajos"),
    (r"^Bay_|^Radiator", "Vano motor"),
    (r"^Seat_.._Headrest", "Reposacabezas delantero"),
    (r"^Seat_.._Backrest", "Respaldo deportivo S line"),
    (r"^Seat_.._Cushion", "Banqueta deportiva S line"),
    (r"^Seat_", "Asiento delantero"),
    (r"^Rear_", "Asiento trasero"),
    (r"^Steering_Rim", "Aro del volante de 4 radios (cuero)"),
    (r"^Steering_Airbag", "Airbag del volante"),
    (r"^Steering_MF", "Mandos multifunción del volante"),
    (r"^Steering_Stalk", "Palanca de la columna"),
    (r"^Steering_", "Volante"),
    (r"^Dash_Upper", "Salpicadero superior"),
    (r"^Dash_Inlay", "Moldura decorativa de aluminio"),
    (r"^Dash_Glovebox", "Guantera"),
    (r"^Dash_LightSwitch", "Mando de luces"),
    (r"^Dash_", "Salpicadero"),
    (r"^Vent_", "Aireador redondo"),
    (r"^Cluster_", "Cuadro de instrumentos"),
    (r"^MMI_", "Pantalla MMI emergente"),
    (r"^Climate_", "Climatizador automático bizona"),
    (r"^Console_Selector", "Palanca S tronic"),
    (r"^Console_MMI", "Mando MMI"),
    (r"^Console_", "Consola central"),
    (r"^Door_.._", "Panel interior de puerta"),
    (r"^Trim_Headliner", "Techo interior"),
    (r"^Visor_", "Parasol"),
    (r"^Grab_Handle", "Asidero"),
    (r"^Mirror_(Frame|Glass|Housing|SensorCover|Stem)$", "Retrovisor interior"),
    (r"^Belt_", "Cinturón de seguridad"),
    (r"^Mat_", "Alfombrilla"),
    (r"^Trim_Carpet", "Moqueta"),
    (r"^Trim_(Sill|ScuffPlate)", "Umbral de puerta"),
    (r"^Trim_", "Guarnecido"),
    (r"^Pedal_", "Pedal"),
]


def _to_gltf(v):
    x, y, z = v
    return [float(x), float(z), float(-y)]


def label_for(name):
    base = re.sub(r"\.\d{3}$", "", name)
    for rx, lab in LABELS:
        if re.search(rx, base):
            side = ""
            if re.search(r"(\.L|_L|FL|RL)$|_FL_|_RL_|^Door_(FL|RL)_|^Seat_FL|Wheel_[FR]L|Brake_[FR]L", base):
                side = " izquierdo"
            elif re.search(r"(\.R|_R|FR|RR)$|_FR_|_RR_|^Door_(FR|RR)_|^Seat_FR|Wheel_[FR]R|Brake_[FR]R", base):
                side = " derecho"
            return lab + side if side and not lab.endswith(("izquierdo", "derecho")) else lab
    return base.replace("_", " ")


def group_for(name):
    base = re.sub(r"\.\d{3}$", "", name)
    for rx, g in RULES:
        if re.search(rx, base):
            return g
    return None


def _split_side_glass(ob):
    """Glass_Side.(L|R) -> Glass_Front, Glass_Rear, Glass_Quarter (by pillars)."""
    sfx = ob.name[-2:]
    me = ob.data
    n = len(me.polygons)
    C = np.zeros(n * 3)
    me.polygons.foreach_get("center", C)
    C = C.reshape(-1, 3)
    bp = np.asarray(op.B_PILLAR, float) * 1e-3
    cp = np.asarray(op.C_PILLAR, float) * 1e-3
    xb = np.interp(C[:, 2], [bp[0, 1], bp[2, 1]], [(bp[0, 0] + bp[1, 0]) / 2,
                                                    (bp[2, 0] + bp[3, 0]) / 2])
    xc = np.interp(C[:, 2], [cp[0, 1], cp[2, 1]], [(cp[0, 0] + cp[1, 0]) / 2,
                                                    (cp[2, 0] + cp[3, 0]) / 2])
    lab = np.where(C[:, 0] > xb, "Front", np.where(C[:, 0] > xc, "Rear", "Quarter"))
    for part in ("Front", "Rear", "Quarter"):
        keep = set(np.nonzero(lab == part)[0].tolist())
        if not keep:
            continue
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[f for i, f in enumerate(bm.faces) if i not in keep],
                         context="FACES")
        m2 = bpy.data.meshes.new(f"Glass_{part}{sfx}")
        bm.to_mesh(m2)
        bm.free()
        for mat in me.materials:
            m2.materials.append(mat)
        o2 = bpy.data.objects.new(f"Glass_{part}{sfx}", m2)
        for c in ob.users_collection:
            c.objects.link(o2)
        m2.shade_smooth()
    scene.delete(ob)


def build(ctx):
    from .body import panels
    from .core import uv
    uv.apply_all()
    shell = bpy.data.objects.get("Body_Shell")
    if shell is not None:
        out = panels.split(shell, materials={"cowl": ctx.mat("black_textured")})
        for k, ob in out.items():
            ctx.register("panel_" + k, ob)
    for sfx in (".L", ".R"):
        g = bpy.data.objects.get("Glass_Side" + sfx)
        if g is not None:
            _split_side_glass(g)
    # group empties
    root = scene.collection("Assembly")
    empties = {}
    unassigned = []
    for ob in list(bpy.data.objects):
        if ob.type not in {"MESH", "CURVE", "FONT", "EMPTY"} or ob.name.startswith("G_"):
            continue
        col = ob.users_collection[0].name if ob.users_collection else ""
        if col.startswith("_") or "Construction" in col or "Studio" in col:
            continue
        if ob.type != "EMPTY":
            ob["label"] = label_for(ob.name)
        g = group_for(ob.name)
        if g is None:
            if ob.type != "EMPTY":
                unassigned.append(ob.name)
            continue
        ob["group"] = g
        if g not in empties:
            lab, vec = GROUPS[g]
            e = bpy.data.objects.new("G_" + g, None)
            e.empty_display_size = 0.1
            root.objects.link(e)
            e["group"] = g
            e["label"] = lab
            e["explode"] = _to_gltf(vec)
            empties[g] = e
        # keep an existing hierarchy when the parent belongs to the same group
        # (e.g. wheel pivot -> rim/tyre), otherwise hang it from the group
        if ob.parent is not None and group_for(ob.parent.name) == g:
            continue
        mw = ob.matrix_world.copy()
        ob.parent = empties[g]
        ob.matrix_world = mw
    if unassigned:
        print(f"[groups] {len(unassigned)} objects without group:", ", ".join(unassigned[:40]))
    print(f"[groups] {len(empties)} groups")
