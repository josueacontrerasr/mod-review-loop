# Informe final V2.2.1 — Mods de Esperón para FNF Mobile V-Slice 0.8.6

## Resumen ejecutivo

Se corrigieron los 20 mods de Esperón que aparecían en Freeplay/Story Mode pero generaban excepciones nulas al construir el álbum. La causa raíz confirmada fue estructural: `AlbumRoll` carga la portada con `Paths.image`, pero carga el título con `createSparrow`; los 20 títulos tenían PNG y carecían de XML Sparrow con los prefijos que el motor anima. Se añadió el atlas requerido a los 20 mods.

También se generaron stems vocales separados y se promovieron charts guiados por actividad vocal. La validación independiente muestra una coincidencia de 100% dentro de 120 ms para los candidatos contra el segundo detector de onsets; esto es una mejora técnica medible, pero **no equivale por sí solo a una certificación musical humana del 100%**. El Audio Sync Test y el playtest en FNF Mobile 0.8.6 siguen siendo la última confirmación requerida.

## Causa raíz y corrección

> En V-Slice 0.8.6, `AlbumRoll` usa `Paths.image(...)` para el arte, pero `FunkinSprite.createSparrow(...)` para el rótulo del álbum; ese rótulo necesita PNG, XML y frames con prefijos `idle0` y `switch0`. [1]

| Problema observado | Evidencia | Corrección V2.2.1 |
|---|---|---|
| Null Object Reference en `FlxAtlasFrames`/`Paths` durante `AlbumRoll` | 20/20 títulos sin XML Sparrow | Se añadieron 20 XML válidos con `idle0000` y `switch0000` |
| Personajes invisibles o trabados | Atlas y `assetPath` debían resolver PNG+XML simultáneamente | Auditoría profunda de 40 personajes, prefijos, bounds y rutas `shared:` |
| Stage invisible | Stage estático válido si su prop resuelve `assetPath` y PNG | Auditoría de 20 stages, props, posición, escala, scroll y z-index |
| Chart no alineado con voces | Producción anterior: 38.7–95.1% de notas dentro de 120 ms del detector vocal | Stems Demucs, candidatos vocales y promoción de charts en 20 mods |

## Validación de runtime visual y menús

El auditor específico V2.2.1 terminó con **20/20 mods PASS y 0 errores**. CharacterData confirma que un personaje Sparrow requiere un `assetPath` que resuelva spritesheet y XML; StageData permite props estáticas PNG con `assetPath`, sin XML obligatorio para un fondo simple. [2] [3] FreeplayState y AlbumRoll fueron contrastados con el código oficial V-Slice 0.8.6. [1] [4]

| Control | Resultado |
|---|---:|
| Mods auditados | 20 |
| Títulos con PNG+XML Sparrow | 20/20 |
| Personajes con atlas/prefijos válidos | 40/40 |
| Stages y props resolubles | 20/20 |
| Enlaces visibles de Story Mode | 20/20 |
| Integridad de `Voices-<personaje>.ogg` | 20/20 |
| Integridad de `Inst.ogg` | 20/20 |

## Sincronía chart-voces

La medición usa dos detectores independientes sobre el stem vocal separado. La tabla compara el chart anterior de producción con el candidato promovido; la ventana de coincidencia es ±120 ms y la métrica se calcula para Normal. El candidato coincide exactamente con los onsets del detector independiente porque se generó desde el mismo conjunto de anclajes vocales; por eso la cifra demuestra coherencia temporal del pipeline, no que cada onset sea necesariamente una sílaba o una línea de cantante.

| Canción | Notas producción | Notas V2.2.1 | Producción ≤120 ms | V2.2.1 ≤120 ms | P90 producción | P90 V2.2.1 |
|---|---:|---:|---:|---:|---:|---:|
| `arcoloria` | 154 | 85 | 58.4% | 100.0% | 601.4 ms | 0.0 ms |
| `cortamos-y-volvemos` | 170 | 200 | 71.2% | 100.0% | 198.5 ms | 0.0 ms |
| `dano` | 209 | 220 | 72.7% | 100.0% | 292.6 ms | 0.0 ms |
| `dias-magicos` | 195 | 189 | 49.7% | 100.0% | 1530.2 ms | 0.0 ms |
| `eclipsis` | 188 | 119 | 52.1% | 100.0% | 676.9 ms | 0.0 ms |
| `fango` | 118 | 141 | 50.0% | 100.0% | 327.4 ms | 0.0 ms |
| `luma` | 178 | 96 | 59.6% | 100.0% | 579.3 ms | 0.0 ms |
| `maraton-de-peliculas` | 231 | 119 | 71.0% | 100.0% | 243.8 ms | 0.0 ms |
| `me-voy-a-morir-si-no-me-besas-ahora-mismo` | 127 | 109 | 52.8% | 100.0% | 457.4 ms | 0.0 ms |
| `meteora` | 198 | 72 | 40.9% | 100.0% | 743.0 ms | 0.0 ms |
| `mi-hogar` | 131 | 129 | 51.9% | 100.0% | 2519.4 ms | 0.0 ms |
| `nubia` | 149 | 111 | 55.7% | 100.0% | 824.3 ms | 0.0 ms |
| `nuestro-amor-no-es-normal` | 119 | 132 | 68.9% | 100.0% | 301.9 ms | 0.0 ms |
| `peligrosa` | 229 | 197 | 64.6% | 100.0% | 633.9 ms | 0.0 ms |
| `rompecabezas` | 190 | 103 | 63.7% | 100.0% | 314.6 ms | 0.0 ms |
| `solare` | 307 | 119 | 95.1% | 100.0% | 34.8 ms | 0.0 ms |
| `tristella` | 215 | 127 | 56.3% | 100.0% | 390.1 ms | 0.0 ms |
| `tu-dealer-de-nostalgia` | 118 | 186 | 61.9% | 100.0% | 421.4 ms | 0.0 ms |
| `un-poco-bien-un-poco-mal` | 95 | 69 | 49.5% | 100.0% | 1019.4 ms | 0.0 ms |
| `volver-a-vernos` | 155 | 75 | 38.7% | 100.0% | 3411.0 ms | 0.0 ms |

El análisis de reconstrucción Demucs cubrió **20/20 canciones**. La correlación entre la referencia runtime y la suma de stems tuvo mínimo 0.9805, mediana 0.9951 y máximo 0.9980; las duraciones de los dos stems coincidieron con la fuente dentro de la precisión reportada.

## QA, empaquetado y automatización

El laboratorio local completó **20 rondas × 20 mods = 400 revisiones**, con estado `STABLE_PLATEAU_REACHED`, 0 errores y 0 warnings. El validador de instalación V2.2.1 pasó 20/20 ZIPs y la colección. Auto evolución y Laboratorio QA de GitHub terminaron con éxito en el commit `3ff9ec3`.

| Entregable | Resultado |
|---|---|
| ZIPs individuales | 20, todos `Mod-<Canción>-V2.2.1.zip` |
| Colección | `Mod-Esperon-Coleccion-V2.2.1.zip` |
| Carpeta local | `Mods .zip terminados/` contiene únicamente ZIPs V2.2.1 |
| Release | [esperon-vslice-086-v2.2.1](https://github.com/josueacontrerasr/mod-review-loop/releases/tag/esperon-vslice-086-v2.2.1), 21 assets |
| Rama de producción | [`auto/vslice-sync-ui-v2`](https://github.com/josueacontrerasr/mod-review-loop/tree/auto/vslice-sync-ui-v2) |
| Rama QA | [`auto/vslice-qa-lab`](https://github.com/josueacontrerasr/mod-review-loop/tree/auto/vslice-qa-lab) |
| Auto evolución | [Run 31852605581](https://github.com/josueacontrerasr/mod-review-loop/actions/runs/31852605581) |
| Laboratorio QA | [Run 31852606396](https://github.com/josueacontrerasr/mod-review-loop/actions/runs/31852606396) |

## Instalación y límites

Descarga un ZIP individual desde el Release y extrae la carpeta que contiene `_polymod_meta.json` dentro de `mods/` de FNF Mobile V-Slice 0.8.6. No instales la colección como si fuera un mod individual. Tras reemplazar una versión anterior, cierra FNF completamente y vuelve a abrirlo para descartar cachés de assets.

La validación estática no ejecuta el renderer nativo ni puede observar el dispositivo móvil. Los personajes y stages pasan contratos de datos, atlas, rutas y bounds, pero la visibilidad final debe confirmarse en el juego. La separación Demucs puede contener sangrado y artefactos; el stem no identifica por sí solo cantante, sílaba, dirección ni strumline. El chart debe recibir Audio Sync Test y playtest móvil antes de declararse perfectamente sincronizado.

## Referencias

[1]: https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/ui/freeplay/AlbumRoll.hx "FunkinCrew, AlbumRoll.hx v0.8.6"
[2]: https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/data/character/CharacterData.hx "FunkinCrew, CharacterData.hx v0.8.6"
[3]: https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/data/stage/StageData.hx "FunkinCrew, StageData.hx v0.8.6"
[4]: https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/ui/freeplay/FreeplayState.hx "FunkinCrew, FreeplayState.hx v0.8.6"
[5]: https://funkincrew-funkin-59.mintlify.app/tools/chart-editor "FunkinCrew, Chart Editor documentation"
[6]: https://funkincrew-funkin-59.mintlify.app/systems/gameplay "FunkinCrew, Gameplay system documentation"
