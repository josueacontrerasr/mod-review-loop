# Informe final V2.6.0 — Auditoría general y mejora vocal de los 20 mods

## Resultado ejecutivo

Se ejecutó el plan Wide Research sobre los 20 mods de Esperón tomando V2.5.1 como baseline. La revisión vocal fresca y la auditoría general no encontraron una corrección musical o estructural que mejorara objetivamente los mods sin introducir riesgo. Por esa razón **no se creó un Release V2.6.0 artificial** y no se modificaron charts, voces, instrumentales, `timeChanges`, personajes, stages, carátulas ni note styles.

La decisión es conservar V2.5.1 como versión de distribución: sus charts voice-priority pasan la auditoría conjunta de voz e instrumental, sus contratos V-Slice 0.8.6 pasan el runtime estático y sus ZIPs ya estaban publicados con 21 assets.

## Evidencia del adjunto TODO.zip

El archivo `/home/ubuntu/upload/TODO.zip` se inspeccionó de forma pasiva. Tiene 1,409 entradas, 220 JSON y 107 archivos que parecen scripts o binarios. Ningún script, instalador, ejecutable o recurso de terceros se ejecutó ni se copió automáticamente. La comparación encontró 272 rutas de claves JSON presentes solo en el material de referencia y 6 claves presentes solo en los mods actuales; esas diferencias no constituyen por sí mismas un requisito de compatibilidad.

El contenido del adjunto se utilizó como referencia estructural y no como fuente automática de código, audio o assets redistribuibles. La comparación completa está en `todo-zip-comparison.json`.

## Sincronización vocal y rítmica

La auditoría ejecutó análisis paralelo de las 20 canciones y 60 dificultades. Primero se midieron VAD CPU, onsets y error firmado nota→voz/voz→nota. Después se ejecutó un análisis conjunto que clasificó cada nota como vocal o rítmica y comparó cada familia contra su señal correspondiente.

| Dificultad | Notas totales | Notas vocales | Acentos rítmicos | Cobertura vocal ≤120 ms | Cobertura rítmica ≤120 ms | Notas no ancladas |
|---|---:|---:|---:|---:|---:|---:|
| Fácil | 7,399 | 7,056 | 343 | 100 % mínimo | 100 % mínimo | 0 % máximo |
| Normal | 10,089 | 9,177 | 912 | 100 % mínimo | 100 % mínimo | 0 % máximo |
| Difícil | 12,589 | 10,949 | 1,640 | 100 % mínimo | 100 % mínimo | 0 % máximo |

La medición nota→voz aislada produce P95 altos en algunas dificultades porque evalúa acentos instrumentales contra la voz. El análisis conjunto corrige ese falso positivo: una nota vocal se compara con la voz y una nota rítmica con `Inst.ogg`. La deriva por secciones se mantuvo por debajo de 10 ms/minuto en el baseline y no justificó recalcular BPM ni `timeChanges`.

## Auditoría general y visual

Los 20 mods pasaron el auditor general de contratos, rutas y assets. Se validaron manifests, metadata `2.2.4`, chart `2.0.0`, lanes `0–3`, stages, personajes, note styles, carátulas `freeplay/albumRoll/`, PNG/XML, audios OGG y dificultad creciente. Se inspeccionaron visualmente 60 assets principales mediante una hoja de contacto y un atlas de personaje representativo; no se encontraron PNG vacíos, transparencias totales, frames fuera de lienzo ni fallos que justificaran regeneración.

| Gate | Resultado |
|---|---:|
| Mods auditados | 20/20 PASS |
| Assets visuales | 60/60 PASS |
| QA profundo | 20 rondas × 20 mods = 400 PASS |
| Archivos examinados por ronda | 900 |
| Regresión contra V2.5.1 | 0 cambios no intencionales |
| Correcciones aplicadas | 0; no había BLOCKER ni WARNING de alto impacto |

## Decisión de distribución

La auditoría terminó con `NO_VERSION_BUMP_REQUIRED`. V2.5.1 sigue siendo la versión recomendada y está disponible en [Esperón FNF Mobile V-Slice 0.8.6 V2.5.1](https://github.com/josueacontrerasr/mod-review-loop/releases/tag/esperon-vslice-086-v2.5.1). El branch de auditoría `auto/vocal-sync-v260` contiene la evidencia reproducible, pero no reemplaza la Release estable porque no hubo una mejora real que justificara un nuevo paquete.

## Límite de certificación móvil

La evidencia demuestra contratos, assets, hashes, sincronía matemática y estructura. No sustituye el Audio Sync Test dentro del Chart Editor ni un playtest perceptual en FNF Mobile 0.8.6. La reproducción en Android/iOS puede añadir latencia, caché o diferencias de audio que no existen en los timestamps. Si V2.5.1 todavía se percibe desfasado en un dispositivo concreto, el dato diagnóstico necesario es un video del gameplay y el modelo del teléfono.

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release oficial V-Slice 0.8.6"

[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — documentación oficial de modding"

[3]: https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html "FunkinCrew — Creating a Note Style"

[4]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
