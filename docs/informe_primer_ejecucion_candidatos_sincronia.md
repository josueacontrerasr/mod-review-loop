# Primera ejecución — Candidatos de sincronía vocal

## Resultado

El flujo `audio_sync_candidates.py` se ejecutó sobre las **20 canciones** usando el OGG final de cada mod. Los 20 candidatos se generaron fuera de `mods/` y el validador de aislamiento confirmó que los hashes de los 20 charts de producción no cambiaron.

| Control | Resultado |
|---|---:|
| Manifiestos de entrada OGG | 20 / 20 |
| Charts candidatos aislados | 20 / 20 |
| Reportes de sincronía candidatos | 20 / 20 |
| Charts de producción conservados | 20 / 20 |
| Promociones automáticas a producción | 0 |

## Interpretación correcta

Todos los resultados tienen el estado **`MANUAL_REVIEW_REQUIRED`**. La primera ejecución usa `FULL_MIX_PROXY`: sus onsets proceden de la mezcla completa, por lo que pueden representar voz, percusión, efectos o instrumentos. No son evidencia suficiente para afirmar sincronía vocal ni para sustituir el chart distribuido.

Cada carpeta de `sync-candidates/results/<song>/` contiene lo siguiente:

| Archivo | Propósito |
|---|---|
| `candidate-chart.json` | Chart V-Slice candidato; no se copia a producción. |
| `candidate-anchors.json` | Anclajes candidatos derivados de onsets de mezcla completa. |
| `sync-candidate-report.json` | Hash del OGG, parámetros de análisis, BPM candidato, métricas y bloqueos de promoción. |

## Próximo gate de aprobación

Para promover una canción deben existir stems vocales verificados por strumline o una revisión humana de anclajes. Después se debe abrir el Chart Editor, ejecutar **Audio Sync Test** sobre el OGG distribuido y documentar inicio, centro, final, cambios de BPM, un hold largo y una sección densa. Finalmente, se debe repetir el playtest en FNF Mobile V-Slice 0.8.6 sin introducir la latencia del dispositivo dentro del chart.

> Un `PASS` del validador de candidatos significa que el flujo es reproducible y no modifica producción. No significa que las voces estén sincronizadas al 100%.

## Automatización

El workflow `audio-sync-candidates.yml` es de solo lectura. Instala las dependencias analíticas, congela los OGG, genera candidatos, valida su aislamiento y publica artifacts para revisión. No tiene permisos de escritura, no hace `git commit`, no hace `git push` y no genera versiones ni ZIPs.
