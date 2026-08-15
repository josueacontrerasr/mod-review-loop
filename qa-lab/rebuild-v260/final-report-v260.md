# Informe final — Laboratorio autónomo FNF Mobile V-Slice 0.8.6

## Resumen ejecutivo

Se ejecutó el entorno aprobado para auditar los 20 mods de Esperón con prioridad en sincronización, contratos V-Slice 0.8.6, carga de recursos, assets visuales, estructura Android simulada, empaquetado y regresión. La lista paralela procesó las 20 canciones; el laboratorio completó **20 rondas por 20 mods**, equivalentes a **400 revisiones**, sin errores ni cambios detectados en los mods de producción.

El entorno se mejoró con una configuración versionada que bloquea `FNF_VERSION = 0.8.6`, un análisis temporal paralelo seguro para los OGG finales, un loader headless que copia cada mod a la ruta Android simulada y resuelve manifests, charts, personajes, stages, note styles, carátulas, audio y HScript, además de una auditoría final de divergencia entre `main` y la rama estable `auto/vocal-sync-recheck-v5`.

> El resultado demuestra una validación estática y reproducible. No permite afirmar por sí solo una sincronía vocal perceptual perfecta dentro de la aplicación móvil, porque el sandbox no ejecuta el APK oficial ni el Audio Sync Test del Chart Editor.

## Resultados principales

| Área | Resultado |
|---|---:|
| Canciones procesadas en paralelo | 20/20 |
| Auditoría QA autónoma | 20 rondas × 20 mods = 400/400 PASS |
| Runtime V-Slice 0.8.6 | 20/20 PASS |
| Verificador visual moderno corregido | 20/20 PASS |
| Loader headless en ruta Android simulada | 20/20 PASS |
| Análisis temporal paralelo de OGG | 20/20 PASS |
| Candidatos de sincronía aislados | 20/20 PASS |
| ZIPs individuales V2.5.1 | 20/20 PASS |
| Colección V2.5.1 | PASS |
| Archivos no ZIP en `Mods .zip terminados/` | 0 |
| Cambios en `mods/` frente a f75a74f | 0 |
| Cambios en ZIPs frente a f75a74f | 0 |

## Cambios realizados en el entorno

Se añadió `config/fnf_target.json`, que fija la versión 0.8.6, los contratos de metadata/chart/note style, los lanes oficiales, la ruta Android simulada, la política de audio y la regla de no actualizar la versión sin una orden explícita del usuario.

Se incorporó `tools/run_audio_timing_wide_v260.py`. Ejecuta el analizador temporal de los 20 `Inst.ogg` con concurrencia limitada a dos trabajadores para evitar agotamiento de memoria por decodificación simultánea. Genera duración, silencio inicial, primer ataque, onsets y candidatos de BPM como evidencia; no modifica charts, offsets ni audio.

Se incorporó `tools/mobile_headless_loader_v260.py`. Despliega cada mod bajo `qa-lab/mobile-sim/storage/emulated/0/Android/data/com.funkin.fnf/files/mods/` y comprueba resolución estática de rutas runtime, audio OGG, JSON, XML, atlas, personajes, stages, note styles, niveles, carátulas y módulos HScript.

Se corrigió `tools/final_vslice_086_verify.py`. El verificador anterior trataba los `assetPath` relativos de personajes como si debieran resolverse siempre bajo `images/`, aunque los mods actuales y el validador runtime aprobado los resuelven bajo `shared/images`. Tras la corrección, el verificador pasó 20/20. El antiguo `validate_visual_v2.py` sigue siendo histórico y no debe utilizarse como gate de V-Slice 0.8.6: espera versiones visuales antiguas y contratos diferentes.

Se incorporó `tools/verify_branch_divergence_v260.py`, que consulta refs remotos, compara árboles, revisa el script HUD, comprueba el import de `Module` y detiene cualquier promoción automática ante diferencias no explicadas.

## Sincronización vocal y rítmica

La auditoría anterior de baseline ejecutó análisis paralelo sobre las 20 canciones y 60 dificultades. El análisis conjunto clasificó cada nota como vocal o rítmica y comparó cada familia contra su señal correspondiente.

| Dificultad | Notas totales | Notas vocales | Acentos rítmicos | Cobertura vocal ≤120 ms | Cobertura rítmica ≤120 ms | Notas no ancladas |
|---|---:|---:|---:|---:|---:|---:|
| Fácil | 7,399 | 7,056 | 343 | 100 % mínimo | 100 % mínimo | 0 % máximo |
| Normal | 10,089 | 9,177 | 912 | 100 % mínimo | 100 % mínimo | 0 % máximo |
| Difícil | 12,589 | 10,949 | 1,640 | 100 % mínimo | 100 % mínimo | 0 % máximo |

La medición nota→voz aislada produce P95 altos en algunas dificultades porque evalúa acentos instrumentales contra la voz. El análisis conjunto corrige ese falso positivo: una nota vocal se compara con la voz y una nota rítmica con `Inst.ogg`. La deriva por secciones se mantuvo por debajo de 10 ms/minuto en el baseline y no justificó recalcular BPM ni `timeChanges`.

En el ciclo nuevo, los manifiestos de audio se regeneraron antes de crear candidatos, evitando el fallo anterior causado por hashes stale. Se produjeron 20 manifests actuales, 20 charts candidatos aislados y 20 reportes con estado `MANUAL_REVIEW_REQUIRED`; la validación de aislamiento terminó en **20/20 PASS**.

Los candidatos frescos se ejecutan en modo `FULL_MIX_PROXY`, porque no existen stems vocales distribuidos y verificados por personaje/strumline. Por ello, son útiles para estudiar onsets y coherencia temporal, pero no se promocionaron automáticamente a producción. La prioridad vocal queda preservada, aunque la certificación final requiere stems identificados, Audio Sync Test y playtest real en FNF Mobile V-Slice 0.8.6.

## Auditoría general y visual

Los 20 mods pasaron los contratos de manifests, metadata `2.2.4`, charts `2.0.0`, lanes `0–3`, stages, personajes, note styles, carátulas `freeplay/albumRoll/`, PNG/XML, audios OGG y dificultades crecientes. La auditoría visual histórica cubrió **60/60 assets** principales; no se encontraron PNG vacíos, transparencias totales, frames fuera de lienzo ni fallos que justificaran regeneración.

La corrección del verificador moderno no fue una modificación de assets. Fue una corrección del diagnóstico: los personajes y stages existentes se resuelven bajo `shared/images` cuando el contrato runtime del mod lo requiere. El loader headless confirmó que esa estructura carga estáticamente en los 20 mods.

## Divergencia entre `main` y la rama estable

La consulta remota confirmó que `main` sigue en `2cd67f950b40d05f9f5e157f5ebed7510bc2ed36`, con fecha del 14 de agosto. En `main`, `mods/esperon-dano-solare/scripts/` no existe y tampoco existe `shared/` dentro del árbol de Solare.

La rama `auto/vocal-sync-recheck-v5` apunta al hash completo `f75a74fdde0eb17931707b1a88397d6baacf0246`. En ella sí existen `scripts/EsperonSolareHudV2.hxc`, `shared/`, `data/`, `images/` y `songs/`. El script tiene el import `funkin.modding.module.Module` y declara `extends Module`; el blob del archivo es `b1ba63ee33fe6e8b523a6b9b8c1dadb5a9d6628b`.

La diferencia de `main` frente a f75a74f incluye 40 rutas de audio: `Inst.ogg` y la voz distribuida de cada una de las 20 canciones. Esto confirma que `main` es una base anterior. La rama de laboratorio `auto/fnf-vslice-lab-v260` coincide con f75a74f en todos los archivos de `mods/` y en todos los OGG; no se modificó el contenido musical ni visual de producción.

## GitHub Actions y entrega

La validación de código, entorno y evidencia terminó en el commit `02b7c9887f5ab9c3ac71d1c18fd755710a251dcf`; el commit posterior `8f41717` solo añadió este informe. El workflow remoto `Laboratorio QA V-Slice` terminó correctamente en el run `31895710415`, ejecutando las 20 rondas QA, el reempaquetado V2.5.1, la validación paralela 20×20 y la publicación de artifacts.

`Mods .zip terminados/` conserva 21 ZIPs: 20 paquetes individuales V2.5.1 y una colección. No se generó una nueva versión ni un nuevo Release porque el laboratorio no encontró una mejora funcional que justificara modificar los mods o crear un incremento artificial.

## Evidencias principales

| Evidencia | Resultado |
|---|---|
| `qa-lab/rebuild-v260/audio-sync-v260.json` | 20/20 análisis temporales PASS |
| `qa-lab/rebuild-v260/mobile-loader-v260.json` | 20/20 cargas estáticas PASS |
| `qa-lab/rebuild-v260/qa-20x20-lab-v260.json` | 400 revisiones, plateau estable |
| `qa-lab/rebuild-v260/sync-candidate-validation-v260.json` | 20/20 candidatos aislados PASS |
| `qa-lab/rebuild-v260/branch-divergence-main-vs-f75a74f.json` | main antiguo; f75a74f y laboratorio completos |
| `qa-lab/session-30min/final-vslice-086-static.json` | 20/20 PASS tras corregir resolución shared/images |
| `qa-lab/rebuild-v250/runtime-contract-v251.json` | 20/20 runtime V2.5.1 PASS |
| `qa-lab/rebuild-v250/zip-validation-v251.json` | 20 ZIPs y colección PASS |
| `qa-lab/rebuild-v250/qa-20x20-v260.json` | 400 revisiones V2.5.1 PASS |

## Decisión final

La fuente correcta para continuar el trabajo es la rama estable `auto/vocal-sync-recheck-v5` en f75a74f, no `main`. La rama de laboratorio contiene únicamente el entorno, validadores y evidencias, y coincide con la rama estable en los mods. No se ejecutó merge hacia `main`, no se modificó producción y no se publicó un Release artificial.

La siguiente mejora musical real requeriría stems vocales identificados por personaje/strumline o una sesión documentada del Audio Sync Test y un playtest móvil. Mientras no exista esa evidencia, los charts V2.5.1 se conservan como producción estable y los candidatos permanecen aislados.

## Límite de certificación móvil

La evidencia demuestra contratos, assets, hashes, sincronía matemática y estructura. No sustituye el Audio Sync Test dentro del Chart Editor ni un playtest perceptual en FNF Mobile 0.8.6. La reproducción en Android/iOS puede añadir latencia, caché o diferencias de audio que no existen en los timestamps.

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release oficial V-Slice 0.8.6"

[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — documentación oficial de modding"

[3]: https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html "FunkinCrew — Creating a Note Style"

[4]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
