# Convenciones del proyecto

## Herramientas
- Blender 5.2 como módulo Python (`bpy`) en el venv `/opt/bpyenv` (instalar con `tools/setup_env.sh`).
- Todo el modelo se genera **por código** (reproducible): `python tools/run.py ...`.
- Render de verificación: Cycles CPU (`--views`), estudio procedural (`a3.core.render`).

## Sistema de coordenadas (ISO 8855)
- `+X` hacia delante, `+Y` hacia la **izquierda**, `+Z` hacia arriba. Metros.
- Origen: suelo, centrado lateralmente, **centro del eje delantero**.
- Eje trasero en `x = -2.636`. Paragolpes delantero `x = +0.869`, trasero `x = -3.441`.
- Vehículo con volante a la izquierda (España): conductor en `+Y`.
- Ruedas: centros en `a3.spec.wheel_centres()` (vía 1535/1506, z = radio estático 0.306).

## Estructura de una pieza (part)
```python
def build(ctx):            # ctx: a3.build.BuildContext
    col = "Exterior/Wheels"           # ruta de colección
    m = ctx.mat("wheel_black")        # materiales de a3.core.materials
    ob = mesh.revolve(...)            # helpers de a3.core.mesh
    ctx.register("wheel_FL", ob)
```
- Nombres de objeto en inglés, descriptivos (`Wheel_FL_Rim`, `Dash_Vent_C_L`).
- Materiales **solo** a través de `ctx.mat(clave)`; si falta uno, añadirlo en `core/materials.py`.
- Geometría con normales coherentes hacia fuera, sin caras degeneradas, shading suave con
  aristas vivas donde correspondan (`mesh.shade_smooth(ob, angle)`).
- El detalle de forma se modela con geometría. Las texturas están permitidas para lo que es
  textura de verdad (grano de cuero, perforado, tejidos, plásticos texturados, rotulación de
  botones, gráficos de pantallas, marcaje del neumático, escamas del metalizado): generadas por
  código (procedurales y horneadas a imagen en `assets/textures/`) para que viajen en el GLB.
- Cotas en el código en mm convertidas con `spec.m()` o escritas en metros con comentario.
- Cada cota relevante: comentario con su origen (C confirmado / S fuente secundaria / E estimada).

## Publicación
- `docs/` es la web de GitHub Pages (rama `main`, carpeta `/docs`): `docs/index.html` (visor
  Three.js), `docs/models/*.glb|*.usdz` (calidad completa, nunca simplificados), `docs/renders/`.
- Fotos de referencia: `tools/fetch_references.sh` → `reference/photos/` (no versionadas).

## Calidad
- Proporciones reales antes que detalle. Contrastar con fotos de referencia.
- No simplificar ni diezmar los modelos publicados. Límite práctico: cada archivo < 100 MB
  (límite de GitHub); si se supera, usar compresión sin pérdida visible (p. ej. meshopt o Draco
  con cuantización ≥ 16 bits), nunca reducir polígonos.
