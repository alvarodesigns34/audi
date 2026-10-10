# Audi A3 Sportback 8V · 2.0 TDI 150 CV S tronic S line — Digital Twin

Réplica 3D procedural de un **Audi A3 Sportback 8V pre-restyling (MY2013–2016, tipo 8VA)**,
2.0 TDI 110 kW S tronic, tracción delantera, acabado **S line**, blanco, interior de cuero
negro, volante de cuatro radios, MMI con pantalla emergente, climatizador bizona y llantas
Audi exclusive 18" *5-arm rotor* negro brillante diamantadas.

Todo el modelo se **genera por código** con Blender 5.2 usado como módulo de Python (`bpy`):
no hay mallas hechas a mano ni texturas de imagen. Cada cota relevante está en el código con
su origen (C = confirmada, S = fuente secundaria, E = estimada).

![Frontal 3/4](docs/renders/front34.png)

## Uso rápido

```bash
tools/setup_env.sh                                   # crea /opt/bpyenv con bpy 5.2
PY=/opt/bpyenv/bin/python

# coche completo + renders de verificación
$PY tools/run.py --views front34,rear34,side_r,cockpit --out out/renders

# guardar .blend y exportar glTF binario (Draco) para el visor web
$PY tools/run.py --save out/a3_sportback_8v.blend --glb viewer/a3_sportback_8v.glb

# visor web (Three.js)
cd viewer && python3 -m http.server 8000   # abrir http://localhost:8000
```

`--parts body,glass,...` construye solo un subconjunto; `--clay` pinta la carrocería en gris
para revisar superficies. La carrocería (booleanas exactas, ~3 min) se cachea en
`out/cache/` y se reutiliza mientras no cambien sus fuentes.

## Cómo se ha construido (y validado)

1. **Datos** — `src/a3/spec.py`: longitud 4310, anchura 1785 (1966 con retrovisores), altura
   1425 − 15 (suspensión deportiva S line), batalla 2636, vías 1535/1506, voladizos 869/805,
   neumático 225/40 R18, llanta 8J×18 ET46, frenos 312×25 / 272×10.
2. **Carrocería** — `src/a3/body/`:
   * Superficie por secciones transversales entre dos planos de corte, gobernada por líneas
     características (perfil superior/inferior, línea *tornado*, cintura, borde del techo,
     etc.) en tablas en mm (`lines.py`), con tangencia y aristas vivas controladas.
   * Morro y zaga cerrados con superficies "perfil lateral × planta" (`surface.EndCap`), que
     no pueden plegarse y empalman con la sección de corte.
   * Espesor de chapa, pasos de rueda, huecos de lunas, juntas de puertas/capó/portón/
     paragolpes, tapa de combustible (lado derecho), parrilla, faros, tomas, pilotos y
     difusor cortados con **booleanas exactas** sobre la piel (`openings.py`).
3. **Validación fotogramétrica** — `tools/camera_match.py` calibra la cámara de fotografías
   reales (Wikimedia Commons, ver `reference/`) a partir de puntos conocidos (ruedas, contacto
   con el suelo); `tools/overlay.py` superpone el render del modelo y sus líneas
   características sobre la foto; `tools/backproject.py` y `tools/raycast_photo.py`
   retroproyectan píxeles a coordenadas del vehículo para posicionar puertas, pilares,
   tiradores, parrilla, faros, pilotos, salidas de escape, etc.
4. **Piezas** — `src/a3/exterior/` (frontal, faros, zaga, retrovisores, molduras, bajos),
   `src/a3/wheels/` (llanta, neumático con dibujo y marcaje, frenos, buje) e
   `src/a3/interior/` (salpicadero, salidas de aire, cuadro, MMI, climatizador, volante de
   4 radios, consola S tronic, asientos S line, paneles de puerta, guarnecidos, pedales…).

## Sistema de coordenadas

ISO 8855: +X adelante, +Y izquierda, +Z arriba, metros; origen en el suelo, en el centro del
eje delantero. Volante a la izquierda. Ver `docs/CONVENTIONS.md`.

## Estado y limitaciones conocidas

Ver `docs/STATUS.md` (precisión estimada por zona, decisiones pendientes y siguientes pasos).
