# Informe técnico V2.6.3 — alineación por sílabas e intermedios

## Alcance

V2.6.3 reemplaza el pipeline de onsets vocales por un pipeline de alineación fonética aproximada para los 21 mods de Esperón. El audio final objetivo continúa siendo FNF Mobile V-Slice oficial `0.8.6`. Se preservan metadata `2.2.4`, chart `2.0.0`, tres dificultades, lanes de jugador `0..3`, personajes, escenarios, note styles, HUD y carátulas Freeplay.

## Método utilizado

Cada stem `Voices-*.ogg` fue transcrito en español con Whisper `small`, con timestamps por palabra. Después se aplicó una segmentación silábica conservadora basada en núcleos vocálicos, refinamiento mediante energía RMS local y revisión de límites de palabra. Las repeticiones e intermedios se conservan como unidades separadas cuando el audio entrega ataques temporales distinguibles. Los duplicados artificiales de Whisper con timestamps idénticos fueron colapsados; los empates acústicos reales se mantienen como ataques simultáneos con lanes distintos.

Los charts de Normal y Hard conservan todas las sílabas confiables. Easy reduce densidad desde los mismos timestamps, preservando intermedios y sostenidos importantes. Los holds se crean solamente cuando la duración vocal medida alcanza el umbral; el final queda limitado al intervalo vocal de la sílaba y no cruza el siguiente ataque.

No se incluyeron letras completas, transcripciones ASR ni reportes dentro de los ZIP runtime. La guía de texto se mantiene únicamente en la evidencia fuera de la entrega.

## Resultado de alineación

| Métrica | Resultado |
|---|---:|
| Canciones procesadas | 21/21 |
| Unidades silábicas candidatas | 10,945 en el lote Whisper `small` |
| Intermedios detectados | 470 |
| Holds candidatos | 1,126 antes de la promoción final |
| Candidatos validados | 21/21 PASS |
| Notas fuera de intervalos silábicos | 0 |
| Notas no alineadas a una sílaba | 0 |
| Holds cruzando límites vocales | 0 |
| Metadata candidata en producción | 0 |
| Lanes inválidos | 0 |

La comparación Wide Research utilizó seis workers para medir energía vocal, errores de ataque y diferencias frente a producción. Su estado se conserva como `MANUAL_REVIEW_REQUIRED` porque la cercanía a un pico RMS es una métrica diagnóstica, no una prueba humana de fonética. Los segmentos de baja confianza quedan registrados por canción para revisión futura.

## Gates de V-Slice y entrega

| Gate | Resultado |
|---|---:|
| Resolver PlayState | 63/63 PASS |
| Producción silábica | 21/21 PASS |
| Contratos y assets | 21/21 PASS |
| ZIPs individuales | 21/21 PASS |
| `Esperon-Completo.zip` | PASS; 21 raíces de mod |
| Loader headless móvil | 21/21 PASS |
| QA profundo | 420/420 PASS; 20 rondas × 21 mods |
| CRC del ZIP completo | PASS |
| ZIPs de entrega | 22; colección + 21 individuales |
| ZIP runtime limpio | PASS; sin reports, logs, staging ni letras |

## Correcciones durante la revisión

La primera ejecución reveló duplicados de timestamps producidos por Whisper en intermedios repetidos. Se añadieron deduplicación temporal, ventanas RMS locales y asignación de lanes únicos para ataques que comparten timestamp. También se corrigió el gate para empates entre sílabas superpuestas: un hold se valida contra el intervalo vocal correspondiente al ataque con mayor duración, no contra una sílaba corta elegida arbitrariamente por empate.

## Limitación de certificación

El pipeline confirma una relación estática y reproducible entre timestamps de voz, sílabas candidatas, holds y charts. No puede certificar por sí solo la percepción humana de cada fonema ni la latencia de un dispositivo físico. La validación final recomendada sigue siendo Audio Sync Test en Chart Editor y playtest de inicio, centro, frase larga, intermedios y final en FNF Mobile V-Slice `0.8.6`.
