# Informe de calidad — Sync/UI V2

## Resultado consolidado

La entrega `v2.0.0` contiene **20 mods** con estilos de notas propios, flechas, receptores, assets de HUD y atlas multi-frame de canto para ambos personajes. La auditoría de referencias de UI aprobó los 20 mods, el validador específico de Sync/UI aprobó los 20 mods y se verificó la integridad de los 20 ZIPs mediante prueba de archivo.

| Control | Resultado | Alcance |
|---|---:|---|
| Mods cubiertos | 20 / 20 | Directorios, metadata, charts, personajes, estilos de notas y UI. |
| Estilos de notas resueltos | 20 / 20 | Cada `playData.noteStyle` enlaza a un JSON y assets presentes. |
| HUD y scripts de barra de vida | 20 / 20 | PNG de barra de vida y un módulo HScript por mod, sin mutación de timing detectada. |
| Atlas vocales multi-frame | 40 / 40 | Personaje y rival: idle, cuatro direcciones de canto y cuatro variantes hold. |
| Charts candidatos | 20 / 20 | Tres dificultades y evidencia de análisis por canción. |
| Comparación chart ↔ anclajes candidatos | 20 / 20 | Los anclajes generados se encuentran en el chart candidato. |
| Integridad de ZIP `v2.0.0` | 20 / 20 | Prueba de archivo ZIP aprobada. |

## Estado de sincronía

> **No se declara sincronía perfecta ni aprobada aún.** Los anclajes usados para reconstruir los charts son candidatos automáticos; la comparación estática solo confirma que el chart conserva esos timestamps, no que cada onset corresponda musicalmente a una voz o sílaba.

La canción **Solare** cuenta con un stem vocal de trabajo generado por separación de fuentes. Sus ataques vocales fueron analizados y el chart candidato se construyó a partir de ellos. Las otras 19 canciones se analizaron como mezcla completa, por lo que sus resultados requieren revisión humana prioritaria antes de declarar que cada frase cantada activa la flecha y animación correctas.

El validador V-Slice estándar en modo `song` bloquea los informes `sync-report.json` porque, de manera correcta, conservan `REQUIRES_HUMAN_REVIEW` en lugar de afirmar anclajes revisados y Audio Sync Test aprobado. Esto es un control de honestidad, no un error de rutas, JSON, assets o ZIP.

| Prueba pendiente | Razón |
|---|---|
| Audio Sync Test en Chart Editor | Debe realizarse sobre el juego oficial con la forma de onda y los OGG empaquetados. |
| Revisión de asignación vocal | Las 19 canciones analizadas con mezcla completa no permiten garantizar intérprete/sílaba exactos automáticamente. |
| Playtest Android/iOS | Requiere FNF Mobile V-Slice 0.8.6 en un dispositivo para comprobar latencia, HUD y animaciones durante gameplay. |

## Artefactos relevantes

- `artifacts/ui-audit/reference-audit.json`: referencias de note style, flechas y HUD.
- `artifacts/vocal-animation-report.json`: cobertura de los 40 atlas multi-frame.
- `artifacts/sync-ui-v2-validation.json`: validación estática, con advertencias por fuente de análisis.
- `analysis/`: evidencia de BPM, onsets, segmentos vocales candidatos, anclajes y comparaciones por canción.
- `reports/sync-ui-v2-manifest.json`: listado de los 20 ZIP `v2.0.0`.

## Conclusión

La entrega está preparada para el siguiente paso de control en el Chart Editor y prueba móvil. Sus recursos visuales, enlaces y paquetes son comprobables; su sincronía musical se mantiene explícitamente como **candidata y pendiente de confirmación oficial**, tal como exige el flujo V-Slice.
