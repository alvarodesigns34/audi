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
- Sin texturas de imagen: el detalle se modela con geometría (los únicos “mapas” permitidos
  son el ruido procedural de grano de cuero/plástico definido en la librería de materiales).
- Cotas en el código en mm convertidas con `spec.m()` o escritas en metros con comentario.
- Cada cota relevante: comentario con su origen (C confirmado / S fuente secundaria / E estimada).

## Calidad
- Proporciones reales antes que detalle. Contrastar con fotos de referencia.
- Presupuesto orientativo: carrocería 300–600 k tris, cada rueda 60–120 k, interior 0.5–1 M.
