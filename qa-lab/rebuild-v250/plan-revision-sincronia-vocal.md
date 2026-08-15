# Plan de revisión y corrección de sincronía vocal — FNF Mobile V-Slice 0.8.6

## Objetivo

Revisar nuevamente las voces y los charts de los 20 mods de Esperón porque la sincronización percibida todavía no es satisfactoria. El trabajo se realizará mediante procesamiento paralelo —Wide Research— para analizar cada canción de forma independiente y consolidar después los resultados con reglas deterministas. El objetivo no será declarar una sincronía perfecta por una métrica aislada, sino localizar si el desfase proviene de un offset constante, de un BPM/timeChanges incorrecto, de una deriva temporal, de la selección del stem vocal o de la forma en que se colocan las notas.

La versión de referencia será **V2.5.0**, el objetivo del motor seguirá siendo **FNF Mobile V-Slice 0.8.6**, y no se modificará producción durante la fase de diagnóstico. Solo se generarán candidatos aislados hasta que todos los gates de audio, chart, runtime y regresión sean satisfactorios.

## Alcance fijo

Se analizarán estas 20 canciones, cada una en sus tres dificultades: `arcoloria`, `cortamos-y-volvemos`, `dano`, `dias-magicos`, `eclipsis`, `fango`, `luma`, `maraton-de-peliculas`, `me-voy-a-morir-si-no-me-besas-ahora-mismo`, `meteora`, `mi-hogar`, `nubia`, `nuestro-amor-no-es-normal`, `peligrosa`, `rompecabezas`, `solare`, `tristella`, `tu-dealer-de-nostalgia`, `un-poco-bien-un-poco-mal` y `volver-a-vernos`.

La fuente primaria de sincronización será el archivo vocal distribuido `Voices-<player>.ogg` de cada mod, no una detección realizada únicamente sobre la mezcla completa. El instrumental se utilizará como referencia secundaria para ataques rítmicos, pero no podrá desplazar la prioridad de la voz. Los archivos OGG, sus hashes, el BPM base y los `timeChanges` se congelarán antes de cualquier reconstrucción.

## Fases de trabajo

### Fase 1 — Congelación y reproducción del problema

Se creará una rama de trabajo nueva desde la V2.5.0 estable, presumiblemente `auto/vslice-sync-ui-v5`, dejando intacta la rama y el Release anterior como rollback. Se calcularán SHA-256, duración, frecuencia de muestreo, canales y encabezados de `Inst.ogg` y de todas las voces. También se registrarán hashes de los 60 charts actuales y de sus metadatos.

Se ejecutará una reproducción estática del desfase para cada canción y dificultad. La salida distinguirá cuatro situaciones: error de offset constante, deriva progresiva, eventos correctos pero notas asociadas al lado equivocado, y onsets vocales detectados correctamente pero notas colocadas en momentos musicales deliberadamente no vocales. Esta clasificación evitará aplicar un desplazamiento global cuando el problema real sea un mapa de tempo.

### Fase 2 — Wide Research paralelo sobre los 20 mods

Se lanzarán trabajadores independientes —idealmente uno por canción, con concurrencia limitada por CPU y memoria— y cada trabajador producirá evidencia sin tocar producción. Todos usarán la misma configuración determinista y devolverán resultados con el mismo esquema JSON.

| Línea paralela | Análisis | Resultado esperado |
|---|---|---|
| Audio vocal | VAD CPU calibrado por ruido, RMS por ventanas de 20 ms, hangover para consonantes y consenso de onsets espectrales | Segmentos vocales, ataques candidatos y confianza temporal |
| Audio instrumental | Onsets de percusión, bajo y energía armónica, separados de la voz | Referencia rítmica secundaria y clasificación de acentos |
| Timing global | BPM, downbeat, duración, `timeChanges`, primer ataque y deriva entre compases | Diagnóstico de offset, escala temporal o warping por secciones |
| Chart actual | Tiempos `t`, lanes `d`, duplicados, holds, densidad y distancia a onsets vocales | Distribución de errores por dificultad y sección |
| Contrato V-Slice | `chart.version`, `metadata.version`, unidades en milisegundos, orden, lanes 0–3 y duración | Confirmación de que el error no es de formato o resolución de strumline |
| Evidencia visual | Línea de tiempo de waveform, segmentos vocales, onsets y notas superpuestos | Gráfico por canción para revisión de intro, verso, coro, puente y final |

Cada trabajador guardará tanto la evidencia detallada como un resumen. Después se ejecutará un reductor central que no volverá a analizar audio: solo comprobará que las 20 respuestas tienen el mismo esquema, comparará métricas y ordenará los casos por severidad.

### Fase 3 — Medición rigurosa de sincronía

Para cada nota candidata se buscará el onset vocal más cercano dentro de una ventana configurable. Se reportarán mediana, media, desviación absoluta mediana, percentiles P90/P95, porcentaje dentro de 40 ms, 80 ms, 120 ms y 160 ms, además del error firmado para detectar un desplazamiento sistemático. Los eventos instrumentales se medirán por separado y nunca se mezclarán silenciosamente con los vocales.

Se evaluará la sincronía en tres niveles: canción completa, secciones musicales y cada dificultad. Cuando las tres dificultades compartan el mismo mapa temporal, se comprobará que el cambio de dificultad solo modifique densidad, holds permitidos y velocidad, no la alineación de los ataques heredados.

Los gates candidatos serán: mediana de error absoluto de hasta 45 ms; P95 de hasta 140 ms; al menos 90 % de las notas vocales dentro de 120 ms en fácil, 88 % en normal y 85 % en difícil; error firmado sin deriva consistente superior a 40 ms entre el primer y último tercio de la canción; y mejora medible frente a V2.5.0. Si una canción no alcanza esos límites por la naturaleza de su mezcla, se marcará `MANUAL_REVIEW_REQUIRED` en vez de forzar una aprobación.

### Fase 4 — Reconstrucción voice-first en candidatos aislados

Según el diagnóstico de cada canción se elegirá únicamente una corrección compatible con la evidencia. Un offset constante se corregirá desplazando los eventos necesarios. Una deriva lineal se corregirá mediante una transformación temporal validada contra anclajes vocales. Una deriva por secciones requerirá actualizar `timeChanges` solo cuando exista evidencia suficiente de cambios de tempo; no se inventarán BPM nuevos a partir de un detector automático.

Se reconstruirán primero los ataques vocales, manteniendo las notas del jugador en lanes `0–3`. Después se añadirán acentos instrumentales limitados, con porcentajes máximos de 15 % en fácil, 25 % en normal y 35 % en difícil respecto de las notas adicionales. Los acentos no podrán desplazar ni reemplazar una nota vocal coincidente. Se conservarán audio, voces, `timeChanges` y contratos de V-Slice salvo que el diagnóstico documente una corrección temporal necesaria.

Cada candidato incluirá hashes del audio de entrada, configuración del análisis, anclajes utilizados, errores antes/después, cobertura vocal y razón de cada transformación. Ningún candidato se promocionará por superar solamente un umbral de onset.

### Fase 5 — Validación paralela y regresión

Se ejecutarán en paralelo los gates estructurales y de sincronía para los 20 mods. Cada dificultad deberá tener notas no vacías, tiempos absolutos ordenados, sin duplicados exactos, lanes dentro de `0–3`, notas dentro de la duración del audio y densidad creciente `easy < normal < hard`. También se comprobará que el chart no pierda personajes, stages, note styles, carátulas `albumRoll`, voces ni audio.

Se repetirá el análisis de hashes para demostrar que `Inst.ogg`, `Voices-*.ogg` y los `timeChanges` no cambian accidentalmente. Se generarán comparaciones antes/después para verificar que el error vocal disminuye en las 20 canciones. Cualquier canción que empeore, pierda cobertura o muestre una deriva nueva bloqueará la promoción global y quedará en un candidato separado.

Se realizará un ciclo de **20 rondas × 20 mods**, donde cada ronda recorrerá cada archivo fuente y volverá a ejecutar el contrato runtime, parseo JSON/XML, comprobación de atlas, OGG, charts y CRC. Además habrá un gate específico de sincronía para las 60 dificultades.

La validación estática será complementada, cuando sea posible, con un render o reproducción de referencia de inicio, verso, coro, puente y final. El Chart Editor oficial y su Audio Sync Test seguirán siendo la prueba normativa del motor; un overlay de waveform no puede sustituir por sí solo un playtest dentro del juego.

### Fase 6 — Promoción, empaquetado y publicación condicionada

Solo si las 20 canciones pasan los gates se respaldarán los charts V2.5.0, se promoverán los candidatos y se actualizarán manifests a una nueva versión. Se mantendrá el empaquetado determinista para que el workflow cada 10 minutos no produzca commits artificiales. La carpeta `Mods .zip terminados/` conservará únicamente los ZIPs finales de la nueva versión y la colección quedará fuera del historial de blobs grandes si el `.gitignore` lo exige, pero se publicará como asset de Release y artifact de Actions.

Antes de publicar se ejecutarán el workflow de QA y la revisión automática en la rama nueva. El Release solo se creará si ambos terminan en `success`, los 20 ZIPs y la colección pasan CRC y el informe de sincronía no contiene `MANUAL_REVIEW_REQUIRED`. Si no hay una mejora real o alguna canción requiere revisión humana, no se creará una versión artificial; se entregará el diagnóstico y los candidatos aislados.

## Artefactos previstos

| Archivo | Propósito |
|---|---|
| `qa-lab/rebuild-v250/vocal-recheck-baseline.json` | Métricas de V2.5.0 antes de corregir |
| `qa-lab/rebuild-v250/vocal-recheck-parallel.json` | Resultados por canción de los trabajadores paralelos |
| `qa-lab/rebuild-v250/vocal-alignment-before-after.json` | Comparación de error y cobertura antes/después |
| `qa-lab/rebuild-v250/vocal-alignment-plots/` | Overlays de waveform, voz, onsets y notas |
| `qa-lab/rebuild-v250/voice-first-candidates/` | Charts candidatos aislados por canción y dificultad |
| `qa-lab/rebuild-v250/vocal-sync-gate-v250.json` | Gate consolidado de las 60 dificultades |
| `qa-lab/rebuild-v250/qa-20x20-v250.json` | Evidencia de las 400 revisiones estructurales |
| `qa-lab/rebuild-v250/release-notes-v250.md` | Notas de Release y limitaciones conocidas |

Si se confirma una nueva versión, los nombres se actualizarán coherentemente a `rebuild-v251` o a la versión que corresponda al siguiente cambio real; no se reutilizarán nombres de evidencia de una promoción anterior.

## Riesgos y límites abiertos

El riesgo principal es que el desfase observado en el teléfono sea un problema de reproducción, caché, latencia táctil o configuración del dispositivo y no un error de timestamps. Por ello se compararán hashes y timings antes de tocar charts. Otro riesgo es que la voz contenga reverb, dobles, ad-libs o silencios intencionales; el algoritmo tratará los onsets como anclajes con confianza y no como una transcripción perfecta de cada sílaba.

La sincronía absoluta en Android o iOS no puede certificarse completamente desde un entorno estático. El plan dejará explícitamente pendiente el Audio Sync Test y el playtest perceptual en FNF Mobile 0.8.6 si no existe una captura o ejecución real del motor. No se afirmará que una voz está «100 % sincronizada» solo porque una comparación matemática pase un umbral.

## Criterio de terminación

El trabajo se considerará terminado cuando exista una de estas dos salidas. La primera es una nueva versión publicada con 20/20 mods, 60/60 dificultades, gates de sincronía PASS, audio preservado, ZIPs limpios, QA remoto exitoso y documentación de límites móviles. La segunda, si algún caso no puede certificarse honestamente, es un informe reproducible con los desfases exactos, candidatos aislados, gráficos antes/después y una lista clara de canciones que requieren Audio Sync Test o revisión manual.

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release v0.8.6"

[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — Modding Documentation"

[3]: https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html "FunkinCrew — Creating a Note Style"

[4]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
