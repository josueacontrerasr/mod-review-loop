# Esperón V-Slice 0.8.6 — V2.6.4

## Resumen

V2.6.4 corrige los tres fallos reportados en los 21 mods de Esperón para FNF Mobile V-Slice 0.8.6. Los charts vocales ahora usan exclusivamente la strumline del jugador, las cuatro direcciones del jugador se distribuyen en `d=4..7`, el selector Freeplay conserva el arte real mediante el contrato oficial de álbum y la alineación vocal incorpora extensión RMS para palabras cortas con vocal sostenida.

## Cambios técnicos

La asignación de notas se ajustó al contrato oficial de V-Slice: `d=0..3` corresponde a la strumline del oponente y `d=4..7` a la strumline del jugador. Se regeneraron los 21 charts desde las transcripciones Whisper cacheadas y la envolvente RMS del stem vocal, sin volver a analizar el instrumental como fuente de notas.

Los holds se calculan desde el intervalo vocal medido, con umbral interno de 200 ms y sin un tope artificial de 900 ms. El final vocal se extiende solo cuando la energía RMS permanece activa y siempre se recorta antes de la siguiente sílaba alineada. Easy reduce la densidad usando los mismos ataques; Normal conserva las sílabas alineadas; Hard añade subdivisiones únicamente dentro de vocales sostenidas.

El contrato Freeplay queda normalizado en `data/ui/freeplay/albums/<playData.album>.json`, con `albumArtAsset` bajo `freeplay/albumRoll/<album>-art` y `albumTitleAsset` bajo `freeplay/albumRoll/<album>-title`. Se verifican el PNG del arte, el PNG/XML del título y los prefijos Sparrow `idle0` y `switch0`.

## Validación ejecutada

| Gate | Resultado |
|---|---:|
| Resolución PlayState | 63/63 PASS |
| Charts vocales de producción | 21/21 PASS; 0 notas fuera de intervalo; 0 notas no alineadas; 0 holds fuera del límite vocal |
| Contratos y assets V-Slice | 21/21 PASS |
| Freeplay y Story Mode | 21/21 PASS |
| Loader headless tipo Android | 21/21 PASS |
| ZIPs individuales | 21/21 PASS |
| `Esperon-Completo.zip` | PASS; 21 raíces; 945 archivos runtime; 0 archivos prohibidos |
| Revisión QA archivo por archivo | 20 rondas × 21 mods = 420/420 PASS |

## Distribución

La carpeta `Mods .zip terminados/` contiene únicamente 22 ZIPs runtime: `Esperon-Completo.zip` y los 21 ZIPs individuales con sufijo `V2.6.4`. Los ZIPs excluyen reportes, archivos TXT, Markdown, logs, CSV, HTML y respaldos de laboratorio.

## Alcance de la evidencia

Los resultados anteriores son gates estáticos reproducibles y un loader headless; no ejecutan el APK nativo ni sustituyen el Audio Sync Test y el playtest táctil en el dispositivo Android/iOS. La afirmación respaldada por esta versión es que los datos, rutas, lanes, spans vocales, holds, assets y paquetes cumplen los contratos automatizados definidos para V-Slice 0.8.6.

## Referencias

[1] [FunkinCrew — documentación oficial de modding](https://funkincrew.github.io/funkin-modding-docs/)

[2] [FunkinCrew — `AlbumData.hx` en v0.8.6](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/freeplay/album/AlbumData.hx)

[3] [FunkinCrew — `AlbumRegistry.hx` en v0.8.6](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/freeplay/album/AlbumRegistry.hx)

[4] [FunkinCrew — documentación oficial de charting](https://funkincrew-funkin-59.mintlify.app/systems/charting)

[5] [FunkinCrew — release FNF v0.8.6](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)
