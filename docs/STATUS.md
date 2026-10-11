# Estado del gemelo digital

Última actualización: 2026-10-11 (**v0.3**).
Publicado: `docs/models/a3_sportback_8v.glb` (calidad completa, sin compresión ni
simplificación, con texturas y metadatos de despiece) y `docs/models/a3_sportback_8v.usdz`
(iPhone/iPad). Visor: `docs/index.html`.

## Qué cambió en v0.3

**Medición (nueva base)**
* **Ajuste conjunto de todas las fotos** (`tools/bundle.py`): cámaras (posición, orientación,
  focal y punto principal con *prior*), radio de llanta por foto, altura/cabeceo de cada coche y
  todos los puntos característicos a la vez, con jacobiano disperso (24 s). rms 1,8 px.
* **Dos fotos nuevas calibradas** del mismo coche rojo de salón que `side.jpg`: `rearq`
  (3/4 trasera derecha, 1,3 px) y `rearsq` (lateral trasera, 0,9 px), con `tools/calib.py`
  (rejilla de arranques + puntos de contacto del neumático para fijar arriba/abajo).
  `fetch_references.sh` baja 13 fotos más de Commons (vista trasera pura, 3/4 delantera, etc.).
* Herramientas nuevas: `tools/compare.py` (render completo por la cámara calibrada, foto
  arriba / render abajo), `tools/raycast_skin.py` (píxel → punto 3D en la piel y reproyección en
  otras fotos), `tools/skin_dist.py` (distancia de puntos triangulados a la piel),
  `tools/lines_plot.py` (planta y alzado de las líneas características con los puntos).

**Carrocería (errores de forma corregidos)**
* **Estrechamiento en planta** medido: las puertas quedan por dentro de los pasos de rueda
  (junta del pilar B en el umbral y = 0,849; borde trasero de la puerta trasera 0,825); el
  invernadero trasero es ~80 mm más estrecho (esquina de la custodia y = 0,725). En v0.2 el
  lateral era una "caja" de anchura constante.
* **Luneta envolvente**: el borde lateral de la luneta (= junta del portón) baja desde el
  extremo del alerón (x −2,76, y 0,57, z 1,27) hasta la esquina inferior (x −3,095, y 0,64,
  z 1,025); en v0.2 estaba 250–370 mm más atrás. Se corta en una carta radial (x, θ) de la zaga,
  no por proyección desde un punto de vista (que rozaba los pilares D).
* Sección del techo/alerón detrás del pilar C con la tangente levantada (`K7_LIFT`), pilar D y
  cara del portón convexos (`K6` como punto de construcción), custodia re-medida.
* **Defecto de malla corregido**: los anillos de cierre de morro y zaga se densificaban hacia el
  polo en vez de hacia la sección de empalme: los últimos ~100 mm del techo/alerón y del borde
  del capó eran una sola faceta plana.
* Línea **tornado** con muestreo concentrado a ambos lados de la arista (radio real 3–5 mm).
* **Booleanas verificadas** (`body/shell.py: guarded_cut`): cada corte se comprueba (no se
  pierden caras fuera de la caja del cortador, no quedan paredes sueltas, no queda chapa dentro
  del cortador) y se reintenta con perturbaciones; las juntas se cortan antes que las aberturas y
  se recortan en los pasos de rueda. En v0.2 algunas booleanas fallaban en silencio.
* Cara interior de la chapa en gris cataforesis (no blanca) — se ve desde dentro y por las juntas.

**Zaga**: pilotos en 3D medidos (dos unidades partidas por la junta del portón, barra LED superior,
guías de luz en "U", marcha atrás), juntas del portón en 3D, labio del alerón S line con cara
inferior negra y tercera luz de freno, antena de aleta corta medida (x −2,54), limpialuneta con
brazo, escobilla y tapa, difusor re-medido, salidas de escape trianguladas, 4 sensores de
aparcamiento, tapa del anclaje de remolque, paragolpes trasero con la junta real.

**Frontal**: faro xenón plus nuevo (marco negro, canal blanco de la luz diurna LED, aro cromado,
embellecedor, proyector bi-xenón, lama cromada, intermitente), tomas S line re-medidas (lama
negra con punta, antiniebla), entrada de aire lateral S line, tapas de lavafaros, sensores
delanteros, parrilla con lamas a paso real (sin nervios verticales).

**Lateral**: manetas en su posición triangulada (estaban 55–60 mm adelantadas) con hueco
embutido en la chapa y tapa del bombín.

**Mecánica**: vano motor detallado (`exterior/engine_bay.py`): cubierta del motor esculpida,
tapón de aceite y varilla, copelas de amortiguador, servofreno, bomba, grupo ABS/ESC y tuberías,
caja de fusibles y borne positivo, travesaño frontal con cierre y varilla del capó, estructura
interior y aislante del capó con bisagras, rejilla de la caja de aguas, mazos de cables y manguitos.

**Interior**: volante con el radio inferior ancho único y el embellecedor de aluminio de la foto.

## Precisión por zona

| Zona | Base | Precisión estimada |
|---|---|---|
| Dimensiones globales | Ficha oficial / fuentes secundarias | ±5 mm (C/S) |
| Cámaras de las fotos | Contorno de llanta + ajuste conjunto, 6 fotos | 0,9–1,8 px |
| Frontal (parrilla, faros, tomas) | Triangulación 2 fotos + ray casting | ±10–20 mm |
| Laterales (puertas, cintura, manetas) | 3–4 fotos (side, rearq, rearsq, sline_rear) | ±5–15 mm |
| Zaga (luneta, pilotos, portón, escape) | 3–5 fotos | ±10–20 mm |
| Superficies entre líneas | Estimadas, revisadas en arcilla | E |
| Llanta 5-arm rotor / neumático | Foto rectificada / ETRTO | S/E / C |
| Mecánica | Disposición MQB típica | E (orientativa) |
| Interior | Fotos 8V + envolvente medida | E |

## Errores y carencias conocidos (por prioridad)

1. **Interior**: salpicadero y asientos siguen siendo aproximados (forma del "ala" del
   salpicadero, laterales de los asientos S line, paneles de puerta).
2. Extremos del alerón sobre las esquinas superiores de la luneta: forma aproximada (E).
3. Retrovisores: forma general correcta; la punta podría estar ~20 mm desplazada (dato de anchura
   con retrovisores S, sin foto frontal calibrada fiable).
4. Mecánica estimada (no hay fotos de bajos ni del vano del 8V 2.0 TDI en las referencias).
5. Foto frontal del coche rojo (`front.jpg`): la calibración no es fiable (suelo brillante, llantas
   parcialmente ocultas); no se usa.
6. Sin emblemas traseros de modelo (las unidades de referencia no los llevan).

## Decisiones tomadas (revisables con el propietario)

* **Color**: Blanco Ibis (sólido). Alternativa: Blanco Glaciar metalizado (`--paint glacier_white`).
* **Parrilla S line**: marco cromado. **Molduras de ventanas**: negras. **Lunas** sin oscurecer.
  **Techo** de chapa, sin barras ni panorámico.
* **Escape**: doble salida a la izquierda (2.0 TDI S line). **Matrícula** genérica `1234 ABC`.
* **Suspensión trasera**: multibrazo (versiones de 110 kW, S/E).
* **Antena**: aleta corta (como en las unidades fotografiadas).

## Preguntas abiertas al propietario

1. ¿Blanco Ibis (sólido) o Glaciar metalizado?
2. ¿Marco de parrilla cromado o negro? ¿Molduras de ventanas negras o aluminio?
3. ¿Lunas traseras oscurecidas? ¿Techo panorámico o barras?
4. Fotos de tu coche (4 ortogonales + 2 a 3/4 + interior, ruedas completas en cuadro) para
   calibrarlas con `tools/calib.py` y ajustar el modelo a tu unidad.
