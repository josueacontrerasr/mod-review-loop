# Hallazgos de referencias públicas V-Slice para V2.7.1

Fecha de consulta: 2026-08-16.

| Fuente | Evidencia observada | Uso y limitación |
|---|---|---|
| [High Beta Vocal Cover (V-Slice Port)](https://gamebanana.com/mods/612981) | La página lo clasifica como `Mobile Compatible (Base)` y el título lo presenta como `Vocal Cover (V-Slice Port)`. La descripción accesible indica que es un port de un chart de Psych Engine 0.6.3; no ofrece métricas ni prueba de sincronización vocal. | Referencia válida para compatibilidad declarada y para separar un port vocal de un chart instrumental, pero **no se acepta como evidencia de sincronización**. |
| [High Recharted [V-Slice]](https://gamebanana.com/mods/645371) | La página lo identifica como mod V-Slice y `Base Game Mod Folder`, pero el texto accesible no aporta stems, offsets, métricas ni prueba de que las notas sigan la voz. | Referencia de nomenclatura/port y rediseño de chart; se excluye de la muestra de sincronización demostrada. |
| [77 Rings (Bintang Vocals) V-Slice Charted](https://gamebanana.com/mods/704006) | La página declara `Chart and Vocal Retake` y enlaza un port V-Slice; es la referencia pública más cercana a un chart con vocals explícitos. También aparece restringida por problemas de créditos, por lo que no se usa como fuente de assets. | Aceptada como referencia de patrón conceptual `vocal take + chart`, pero no como prueba de tiempos perfectos porque no hay análisis audio↔chart disponible. |
| [FNF v0.8.6 release notes](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6) | La versión 0.8.6 documenta mejoras del Chart Editor, exportación de charts, vocals, holds y compatibilidad móvil/Polymod. | Fuente oficial de compatibilidad, no de sincronización específica de los mods comunitarios. |

## Regla aplicada

Ninguna de las páginas públicas aporta evidencia suficiente para declarar que un chart está sincronizado con la voz mediante comparación de onda, offsets revisados o `Audio Sync Test`. Por ello, las referencias se usarán únicamente para comparar patrones de diseño: separación entre chart vocal e instrumental, densidad legible, vocal retake y compatibilidad V-Slice. La decisión de reducir clusters en Esperón dependerá de sus stems `Voices-*.ogg`, alineaciones y timestamps propios.

## Evidencia de video analizada

| Fuente | Observación técnica | Decisión |
|---|---|---|
| [High Beta Vocal Cover gameplay](https://www.youtube.com/watch?v=UCAU5sqvqB4) | El análisis multimodal identifica notas que siguen ataques vocales, escaleras asociadas a glissandos, ausencia de notas cuando calla la voz y holds en finales de frases. Reporta aproximadamente 3–4 notas/s en secciones lentas, 7–9 notas/s en una sección intensa y hasta 5 notas/500 ms en un trino vocal; esas cifras son observaciones del video, no mediciones del chart fuente. | **Incluir como referencia de patrón vocal**, no como prueba absoluta: el video no permite comprobar offsets numéricos ni latencia visual con precisión de milisegundos. |

La salida completa se conserva en `reference-high-beta-video-analysis.txt` y el informe fuente generado por el análisis queda fuera de los ZIP runtime. La muestra sugiere que un chart vocal puede superar 3 notas/s cuando la voz realmente contiene ataques rápidos, pero las ráfagas deben distribuir direcciones y no añadir densidad durante silencios instrumentales.

## Referencias adicionales consultadas

| Fuente | Evidencia observada | Decisión |
|---|---|---|
| [77 Rings (Bintang Vocals) V-Slice Charted](https://gamebanana.com/mods/704006) | El título confirma `Bintang Vocals` y `V-Slice Charted`; la página pública accesible identifica el mod como `Base Game Mod Folder`. La descripción no muestra timestamps ni Audio Sync Test. | Incluir como referencia conceptual de vocal retake, excluir como prueba cuantitativa. |
| [It's Not Like I Like You V-Slice FanChart +Mobile](https://gamebanana.com/mods/674346) | El título declara `V-Slice FanChart +Mobile` y la página lo clasifica como `Base Game Mod Folder`. La información accesible no demuestra si las notas siguen voz o instrumental. | Incluir solo para comparar distribución/compatibilidad declarada. |

La muestra externa queda compuesta por cuatro páginas de mods, un video de gameplay vocal y las notas oficiales de FNF 0.8.6. No se encontró evidencia pública suficiente para copiar umbrales exactos; por eso los thresholds V2.7.1 se decidirán con los stems de Esperón y sus métricas de densidad.
