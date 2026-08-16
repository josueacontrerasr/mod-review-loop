# Wide Research V2.7 — informe consolidado

Generado: 2026-08-16T00:19:29.509636+00:00

> Este informe compara la línea base V2.6.6 con candidatos aislados V2.7. La métrica de 0 ms representa coincidencia con el onset acústico calculado por RMS/VAD; no sustituye `Audio Sync Test` ni playtest móvil.

## Resumen

Se analizaron 21 canciones en paralelo con 8 workers. Los candidatos pasan la validación estructural: **PASS**, 0 errores. El desfase mediano absoluto global pasó de 100.0 ms en V2.6.6 a 0.0 ms en el modelo V2.7; el máximo p95 de inicio dentro de los 21 análisis es 0.0 ms.

La reconstrucción produjo 6492 holds frente a 3293 de V2.6.6 y aplicó balanceo a 2823 ataques repetitivos. Un solo mod queda marcado por hold ratio alto; no se oculta y se conserva en la lista de revisión.

## Matriz de las 21 canciones

| Canción | V2.6.6 mediana onset | V2.7 mediana onset | V2.7 p95 onset | p95 final vocal | Holds V2.7 | Balanceo | Revisión |
|---|---:|---:|---:|---:|---:|---:|---|
| arcoloria | 90 ms | 0 ms | 0 ms | 115 ms | 336 | 119 | PASS_AUTO |
| cortamos-y-volvemos | 100 ms | 0 ms | 0 ms | 115 ms | 302 | 158 | PASS_AUTO |
| dano | 90 ms | 0 ms | 0 ms | 115 ms | 264 | 242 | PASS_AUTO |
| dias-magicos | 100 ms | 0 ms | 0 ms | 115 ms | 318 | 155 | PASS_AUTO |
| eclipsis | 100 ms | 0 ms | 0 ms | 115 ms | 411 | 199 | PASS_AUTO |
| fango | 90 ms | 0 ms | 0 ms | 115 ms | 318 | 197 | PASS_AUTO |
| luma | 100 ms | 0 ms | 0 ms | 115 ms | 335 | 117 | PASS_AUTO |
| maraton-de-peliculas | 100 ms | 0 ms | 0 ms | 115 ms | 370 | 136 | PASS_AUTO |
| me-voy-a-morir-si-no-me-besas-ahora-mismo | 100 ms | 0 ms | 0 ms | 115 ms | 253 | 78 | WARNING_REVIEW |
| meteora | 90 ms | 0 ms | 0 ms | 115 ms | 319 | 150 | PASS_AUTO |
| mi-hogar | 100 ms | 0 ms | 0 ms | 115 ms | 180 | 100 | PASS_AUTO |
| nubia | 100 ms | 0 ms | 0 ms | 115 ms | 270 | 125 | PASS_AUTO |
| nuestro-amor-no-es-normal | 100 ms | 0 ms | 0 ms | 115 ms | 227 | 62 | PASS_AUTO |
| peligrosa | 100 ms | 0 ms | 0 ms | 115 ms | 342 | 173 | PASS_AUTO |
| rompecabezas | 100 ms | 0 ms | 0 ms | 115 ms | 366 | 144 | PASS_AUTO |
| si-te-vas | 100 ms | 0 ms | 0 ms | 115 ms | 294 | 143 | PASS_AUTO |
| solare | 100 ms | 0 ms | 0 ms | 115 ms | 395 | 137 | PASS_AUTO |
| tristella | 100 ms | 0 ms | 0 ms | 115 ms | 353 | 138 | PASS_AUTO |
| tu-dealer-de-nostalgia | 100 ms | 0 ms | 0 ms | 115 ms | 272 | 132 | PASS_AUTO |
| un-poco-bien-un-poco-mal | 100 ms | 0 ms | 0 ms | 115 ms | 275 | 102 | PASS_AUTO |
| volver-a-vernos | 100 ms | 0 ms | 0 ms | 115 ms | 292 | 187 | PASS_AUTO |

## Muestras revisadas

Para cada canción se conservaron muestras de inicio, centro y final, además de los diez holds más largos. También se calcularon cuatro secciones por cuartiles para detectar deriva progresiva. Las muestras se encuentran en `phase5-section-drift-v267.json`.

| Evidencia | Resultado |
|---|---:|
| Onsets RMS/VAD procesados | 10945 sílabas |
| Desfase V2.6.6 mediano absoluto | 100.0 ms |
| Desfase V2.7 mediano absoluto | 0.0 ms |
| p95 de inicio V2.7 más alto | 0.0 ms |
| Candidatos con error estructural | 0 |
| Producción modificada durante investigación | No |

## Revisión pendiente

El caso con hold ratio alto se conserva como `WARNING_REVIEW`. Antes de una afirmación de sincronización perfecta, se deberá ejecutar `Audio Sync Test` y revisar físicamente en el runtime móvil una entrada vocal, una vocal larga, una palabra corta prolongada, una racha repetitiva y el último downbeat de cada canción o, si se usa muestreo, justificar el muestreo y registrar sus excepciones.
