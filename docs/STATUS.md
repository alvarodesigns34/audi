# Estado del gemelo digital

Última actualización: 2026-10-10 (**v0.2**).
Publicado: `docs/models/a3_sportback_8v.glb` (calidad completa, sin compresión ni
simplificación, con texturas y metadatos de despiece) y `docs/models/a3_sportback_8v.usdz`
(iPhone/iPad). Visor: `docs/index.html`.

## Qué cambió en v0.2

**Validación fotogramétrica (nueva base de medida)**
* Calibración de cámara por **contorno completo de la llanta** detectado automáticamente
  (`tools/rim_edge.py`, `tools/make_match.py`): error medio < 1 px en las 5 fotos (antes 4–7 px).
  Dos fotos nuevas calibradas (`yellow`, `yellow_rear`: S line amarillo, delantera y trasera).
* **Triangulación multi-foto** de puntos característicos (`tools/triangulate.py`), con ajuste
  conjunto de la altura de carrocería de cada coche (`--joint`) y comprobación epipolar
  (`tools/epipolar.py`) y de reproyección (`tools/reproj_check.py`).
* `tools/silhouette.py`: silueta y contornos de aperturas del modelo proyectados sobre cada foto;
  `tools/skin_preview.py`: arcilla oscura brillante para revisar superficies.

**Carrocería**
* Frontal re-medido: todo el frontal estaba ~40 mm bajo. Parrilla, tomas S line, antiniebla,
  lavafaros, aros y matrícula recolocados; **faro envolvente** definido en 3D (envuelve la esquina
  desde el chaflán de la parrilla hasta la aleta) y cortado en dirección oblicua.
* Línea de cintura 25–30 mm más baja, pilar A más tumbado, ventanillas, pilar B/C, triángulo del
  retrovisor y líneas de puertas re-digitalizados en la foto lateral (cruzados con la trasera ±3 px).
* Pasos de rueda circulares centrados en la rueda (R 362/352 mm medidos en la máscara de la foto).
* **Portón**: la cara del portón estaba 60–90 mm demasiado atrás (triangulado: aros, portamatrícula,
  borde inferior); ahora el paragolpes forma el escalón real bajo el portón. Luneta mucho más ancha
  (esquinas inferiores a |y| 0,69 m), pilotos 20–30 mm más bajos, salidas de escape en el extremo
  exterior del difusor (antes demasiado hacia el centro).
* Nervios en V del capó, ligera aleta sobre las ruedas, banda horizontal del portón
  (`body/features.py`), superficie bajo la línea tornado ligeramente cóncava y hombro menos abombado.
* Juntas que faltaban (aleta–pilar A, borde trasero del capó, techo–portón, faldón) y junta del portón
  con anchura constante medida sobre la superficie.
* **Paneles reales**: el casco se divide en capó, rejilla del parabrisas, paragolpes, aletas, 4 puertas,
  faldones, portón y casco; lunas laterales divididas en puertas y custodias.
* Alerón S line más fino, con extremos caídos y cara inferior negra.

**Piezas nuevas**: suspensión McPherson delantera y multibrazo trasera, dirección, palieres,
subchasis, travesaño de impacto; escape completo (FAP, flexible, silenciadores, soportes, pantallas
térmicas); depósito y protecciones de bajos; **motor 2.0 TDI EA288** con cambio DQ250, radiadores y
electroventiladores, batería, filtro de aire, depósitos; maletero.

**Materiales**: texturas generadas por código y horneadas a imagen (cuero con grano, cuero perforado,
plásticos granulados, moqueta, tejido de techo, cinta de cinturón, aluminio cepillado, caucho, disco,
escamas del metalizado) con UV en metros; pantalla MMI con navegación y FIS como imágenes.

**Visor**: HUD (nombre de pieza al pasar/tocar, ficha de la pieza, encuadrar, aislar grupo), regla de
**vista despiezada** (45 grupos con vector por grupo en los extras glTF), lista de grupos con
visibilidad, ficha técnica con fuentes C/S/E, cámaras, 6 pinturas, luces, noche, lunas oscurecidas,
renderizado bajo demanda (batería del iPad), disposición táctil/vertical.

## Precisión por zona

| Zona | Base | Precisión estimada |
|---|---|---|
| Dimensiones globales | Ficha oficial / fuentes secundarias | ±5 mm (C/S) |
| Cámaras de las fotos | Contorno de llanta, 5 fotos | < 1 px rms |
| Frontal (parrilla, faros, tomas) | Triangulación 2 fotos + ray casting | ±10–20 mm |
| Laterales (ventanillas, puertas, pilares) | Foto lateral + 3/4 trasera | ±10–20 mm |
| Zaga (portón, pilotos, matrícula, escape) | Triangulación 2 fotos | ±15–25 mm |
| Superficies entre líneas (abombados) | Estimadas, revisadas en arcilla | E |
| Llanta 5-arm rotor / neumático | Foto rectificada / ETRTO | S/E / C |
| Mecánica (suspensión, motor, escape) | Disposición MQB típica | E (orientativa) |
| Interior | Fotos 8V + envolvente medida | E |

## Errores y carencias conocidos (por prioridad)

1. **Línea tornado**: tiene la rotura de tangente correcta, pero el sombreado suave la redondea más
   que el radio real (~3–5 mm); falta concentrar la malla junto a la línea.
2. **Interior**: salpicadero y asientos siguen siendo aproximados (forma "ala" del salpicadero 8V,
   costuras y laterales de asientos S line, paneles de puerta).
3. Puntos de la zaga con la foto amarilla discrepan en los sensores de aparcamiento (posible
   correspondencia errónea); el resto del portón es coherente entre fotos.
4. Retrovisores: forma general correcta en la superposición; faltan detalles (junta tapa/base, cámara).
5. Faros/pilotos: estructura interna aún esquemática (firma LED del piloto simplificada).
6. Mecánica estimada (no hay fotos de bajos/vano del 8V en el material de referencia).
7. Sin emblemas traseros de modelo (las dos unidades de referencia no los llevan).

## Decisiones tomadas (revisables con el propietario)

* **Color**: Blanco Ibis (sólido). Alternativa: Blanco Glaciar metalizado (`--paint glacier_white`,
  con escamas). En el visor se puede cambiar.
* **Parrilla S line**: marco cromado. **Molduras de ventanas**: negras. **Lunas** sin oscurecer
  (el visor permite oscurecer las traseras). **Techo** de chapa, sin barras ni panorámico.
* **Escape**: doble salida a la izquierda (2.0 TDI S line). **Matrícula** genérica `1234 ABC`.
* **Suspensión trasera**: multibrazo (versiones de 110 kW, S/E).

## Preguntas abiertas al propietario

1. El primer mensaje se cortó en "IMPORTANTE: el vehículo debe corres…".
2. ¿Blanco Ibis (sólido) o Glaciar metalizado?
3. ¿Marco de parrilla cromado o negro? ¿Molduras de ventanas negras o aluminio?
4. ¿Lunas traseras oscurecidas? ¿Techo panorámico o barras?
5. Fotos de tu coche (4 ortogonales + 2 a 3/4 + interior, ruedas completas en cuadro) para
   calibrarlas con `tools/make_match.py` y ajustar el modelo a tu unidad.
