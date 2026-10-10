# Prompt de continuación (pegar en una sesión nueva)

Estado actual: v0.2 (ver `docs/STATUS.md`). Herramientas clave añadidas en v0.2:
`tools/make_match.py` (calibración por contorno de llanta), `tools/triangulate.py --joint`,
`tools/silhouette.py --outlines --lines`, `tools/skin_preview.py`, `tools/panel_debug.py`,
`tools/publish.sh`. Puntos medidos en `reference/features.json` y `reference/side_points.txt`.

```text
Continúa el proyecto "Audi A3 Sportback 8V — Digital Twin" en el repositorio `audi`
(rama `main`). Es la réplica 3D procedural de MI coche: Audi A3 Sportback 8V pre-restyling
(MY2013–2016, tipo 8VA), 2.0 TDI 150 CV S tronic, tracción delantera, acabado S line, blanco,
interior de cuero negro, volante convencional de CUATRO radios, MMI con pantalla grande
emergente, climatizador automático bizona y llantas Audi exclusive 18" "5-arm rotor" negro
brillante diamantadas (8J×18 ET46, 225/40 R18). Volante a la izquierda (España).
El objetivo es una réplica extraordinariamente detallada y geométricamente fiel, al nivel de
un configurador premium o de un juego de conducción de alta fidelidad, exterior e interior.
La versión actual (v0.1) es una base correcta en proporciones generales pero tiene MUCHOS
errores y le falta mucho detalle: hay que mejorarla muchísimo.

1. PONTE EN CONTEXTO (antes de tocar nada)
- Lee README.md, docs/STATUS.md (errores conocidos, decisiones y preguntas abiertas),
  docs/CONVENTIONS.md y el código de src/a3/ y tools/.
- Entorno: `tools/setup_env.sh` instala Blender 5.2 como módulo de Python en /opt/bpyenv
  (pip `bpy`, ~400 MB). Usa siempre `/opt/bpyenv/bin/python`.
- Fotos de referencia (Wikimedia Commons): `tools/fetch_references.sh` → reference/photos/.
  La API de Commons está limitada por tasa; usa Special:FilePath (el script ya reintenta).
- Construcción: `python tools/run.py --views front34,rear34,side_r,cockpit --out out/renders`
  (`--parts` para subconjuntos, `--clay` para revisar superficies). La carrocería se cachea en
  out/cache (las booleanas tardan ~3–4 min si cambian sus fuentes).

2. CÓMO ESTÁ HECHO (resumen técnico)
- Coordenadas ISO 8855: +X adelante, +Y izquierda, +Z arriba, metros, origen en el suelo en el
  centro del eje delantero. Datos y fuentes en src/a3/spec.py (C/S/E = confirmado/secundario/
  estimado; mantén ese etiquetado).
- Carrocería (src/a3/body): piel por secciones transversales gobernadas por líneas
  características en tablas en mm (lines.py), entre dos planos de corte; morro y zaga con
  superficies "perfil lateral × planta" (surface.EndCap). Espesor + cortes por booleanas
  EXACTAS aplicadas de UNA en UNA (todas juntas agota la RAM; el solver FAST rompe la malla).
  Los cortadores deben ser prismas simples y no autointersectados. surftools.py: parches
  exactos de la piel (cristales, lentes), proyección de contornos y tiras sobre la superficie.
- Validación fotogramétrica: tools/camera_match.py calibra la cámara de una foto con puntos
  conocidos (ruedas, contacto con el suelo); tools/overlay.py superpone el render del modelo y
  sus líneas características sobre la foto; tools/backproject.py y tools/raycast_photo.py
  convierten píxeles en coordenadas del coche. Calibraciones en reference/match_*.json.
- Piezas: src/a3/exterior (frontal, faros, zaga, retrovisores, molduras, bajos),
  src/a3/wheels (llanta, neumático, frenos), src/a3/interior (habitáculo completo; layout.py
  centraliza las cotas y mide la carrocería por ray casting).
- Publicación: docs/ es GitHub Pages (main, /docs): docs/index.html = visor Three.js;
  docs/models/a3_sportback_8v.glb (exportado SIN compresión: el módulo Draco no está en este
  bpy) y docs/models/a3_sportback_8v.usdz (tools/export_usdz.py, Vista Rápida/AR en iPad).
- Para probar el visor sin GPU: Chromium headless de /opt/pw-browsers (usar el binario
  headless_shell con --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader) y
  playwright-core desde npm.

3. QUÉ HAY QUE HACER
A) Corregir los errores de docs/STATUS.md y subir MUCHO el nivel: proporciones y formas
   (superficies más tensas, línea tornado viva, nervios en V del capó, pasos de rueda con labio
   y aleta, frontal, faros, parrilla en relieve, portón, alerón, retrovisores, cristales y
   gomas, faldones, emblemas), más piezas (suspensión y bajos visibles, escape completo,
   vano motor con el 2.0 TDI si se puede, maletero, cinturones, rotulación de botones,
   gráficos de pantallas y cuadro…), y más detalle en el interior (salpicadero 8V real,
   asientos S line, paneles de puerta, guarnecidos). Cada cambio de forma se valida con renders
   y superposición sobre las fotos calibradas (calibra más fotos si hace falta); no des nada
   por bueno sin compararlo visualmente.
B) Materiales y texturas de verdad: crea texturas generadas por código y horneadas a imagen
   (cuero con grano y perforado, tejidos, plásticos texturados, metalizado, marcaje del
   neumático, rotulación, pantallas) para que viajen en el GLB; materiales PBR correctos en
   Blender y en el visor.
C) Visor web (docs/index.html), que debe funcionar bien en iPad (Safari, táctil) y escritorio:
   - Un HUD cuidado: nombre de la pieza al tocar/pasar por encima, ficha técnica, selector de
     cámaras, pintura, luces y estado de carga.
   - Vista despiezada: una barra deslizante que separe progresivamente las piezas (carrocería,
     puertas, capó, portón, paragolpes, cristales, ruedas, frenos, asientos, salpicadero,
     etc.) a lo largo de vectores definidos por grupo, de 0 (montado) a 1 (despiezado).
     Para ello organiza las piezas en grupos/jerarquía con metadatos de despiece (p. ej. extras
     glTF por nodo: grupo y dirección) y separa la carrocería en paneles reales (puertas, capó,
     portón, aletas, paragolpes) en vez de un único casco.
D) Publicar: exporta siempre a calidad completa. NUNCA simplifiques ni diezmes los modelos
   publicados; si un archivo supera 100 MB (límite de GitHub), usa compresión sin pérdida
   visible (meshopt/Draco con cuantización alta) o divide el modelo en varios archivos, pero
   sin bajar polígonos. Actualiza README, docs/STATUS.md y los renders de docs/renders/,
   haz commits frecuentes con mensajes claros y súbelo todo a `main` para que GitHub Pages lo
   publique.

4. FORMA DE TRABAJAR
- Háblame siempre en español. Prioriza calidad y precisión sobre velocidad; no inventes datos
  (si algo es estimado, márcalo E); busca la causa raíz de los problemas; verifica con renders.
- Si necesitas una decisión mía, pregúntamela al final con opciones claras. Siguen abiertas:
  la frase cortada de mi primer mensaje ("IMPORTANTE: el vehículo debe corres…"), el blanco
  exacto (Ibis sólido o Glaciar metalizado), marco de parrilla cromado o negro, molduras de
  ventanas negras o aluminio, cristales traseros oscurecidos, techo panorámico/barras y si te
  paso fotos de mi coche para calibrarlo a mi unidad.
- Al terminar, dame el enlace de GitHub Pages y un resumen de lo mejorado y lo pendiente.
```
