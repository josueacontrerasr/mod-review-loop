# Informe final V2.6.1: PlayState, sincronización vocal y Freeplay

**Proyecto:** 20 mods de Esperón para FNF Mobile V-Slice 0.8.6  
**Rama de reparación:** `auto/playstate-fix-v260`  
**Versión de mods:** `2.6.1`  
**Fecha de auditoría:** 15 de agosto de 2026  
**Autor:** Manus AI

## Resumen ejecutivo

Las capturas mostraban el error crítico `Error loading PlayState` al intentar cargar las tres dificultades con variación `default`. La reproducción estricta del resolver de V-Slice confirmó que el fallo no era causado por lanes, densidad o tiempos: los 20 charts carecían del campo obligatorio `generatedBy` definido por el contrato de `SongChartData`. El parche mínimo añadió `generatedBy: "Friday Night Funkin' - 0.8.6"` sin alterar eventos, `timeChanges`, audio ni recursos visuales.

Además, los 20 charts fueron refinados para que las notas procedan solamente de `Voices-*.ogg`, con cero notas fuera de los segmentos vocales en la validación final. Se reemplazaron las imágenes de Freeplay por miniaturas de las publicaciones oficiales de Esperón seleccionadas por título y canal, convertidas a 512×512 PNG. Finalmente se regeneraron los 20 ZIPs individuales y `Esperon-Completo.zip`, que contiene los 20 mods completos y no incluye reportes ni archivos de auditoría.

## Diagnóstico del error de las capturas

El mensaje mostrado en las capturas correspondía a una falla de resolución de datos de notas en `PlayState` para `easy`, `normal` y `hard`, usando la variación `default`. El resolver headless reprodujo exactamente 60 casos: 20 canciones × 3 dificultades.

| Estado | Casos | Resultado |
|---|---:|---|
| Antes del parche | 60 | 0 PASS; 60 con `chart_required_missing:generatedBy` |
| Después del parche | 60 | 60 PASS; 0 fallos |

El campo añadido fue el siguiente:

```json
{
  "generatedBy": "Friday Night Funkin' - 0.8.6"
}
```

No se modificaron los tiempos de las notas durante este parche. La estructura `notes.easy`, `notes.normal` y `notes.hard` permaneció disponible, y los lanes de jugador continuaron siendo `d=0..3`.

## Sincronización vocal-only

El generador V2.6.1 usa únicamente los archivos `Voices-*.ogg` y refina los onsets hacia picos locales de energía vocal. `Inst.ogg` queda excluido de la generación. La validación independiente comprobó que las tres dificultades de cada canción son progresivas y que cada nota final cae dentro de un segmento vocal con tolerancia interna de 45 ms.

| Gate | Resultado |
|---|---:|
| Candidatos vocal-only | 20/20 PASS |
| VAD independiente | 60/60 dificultades PASS |
| Notas fuera de segmentos vocales | 0 |
| Lanes fuera de `0..3` | 0 |
| Metadata de candidato filtrada de producción | 0 |
| Gate vocal sobre charts promovidos | 20/20 PASS |

La validación confirma procedencia vocal y alineación temporal estructural. La certificación perceptual de sílabas exactas y latencia del dispositivo todavía requiere un playtest real dentro de FNF Mobile V-Slice 0.8.6.

## Carátulas de Freeplay

La primera auditoría visual detectó que varias imágenes eran repetidas o correspondían a otra canción. Para corregirlo, se consultaron las publicaciones oficiales de Esperón y se seleccionó, por canción, el resultado original no instrumental ni slowed. Las fuentes se registraron con título, video ID, canal, URL de miniatura y hash en `official-yt-dlp-covers-v261.json`.

Todas las carátulas finales fueron recortadas al centro, convertidas a RGBA y guardadas como PNG de 512×512. El contrato de álbum se conservó con el prefijo `freeplay/albumRoll/`, por lo que `albumArtAsset` continúa resolviendo el archivo correcto al seleccionar la canción en Freeplay.

| Validación visual y de contrato | Resultado |
|---|---:|
| Carátulas sustituidas | 20/20 |
| Publicaciones oficiales identificadas | 20/20 |
| PNG de 512×512 | 20/20 |
| Imágenes vacías o corruptas | 0 |
| `albumArtAsset` inválido | 0 |
| Hojas de contacto visual | PASS |

## ZIP `Esperon-Completo`

La carpeta `Mods .zip terminados/` fue limpiada y reconstruida. Ahora contiene exactamente 21 archivos: 20 ZIPs individuales V2.6.1 y `Esperon-Completo.zip`. El nombre `Esperon-Completo.zip` aparece antes de los paquetes `Mod-*` en el orden alfabético de la carpeta y fue preparado para subirse primero al Release.

`Esperon-Completo.zip` contiene exactamente las 20 carpetas raíz de mod, con 900 archivos runtime en total. Los archivos `.txt`, `.md`, `.log`, `.csv`, `.html` y `.bak` fueron excluidos de los paquetes. La colección no contiene evidencias, informes ni copias de staging.

## Verificación integral

| Área | Resultado |
|---|---:|
| PlayState `default/easy`, `default/normal`, `default/hard` | 60/60 PASS |
| Contratos V-Slice 0.8.6 y assets | 20/20 PASS |
| Loader headless Android | 20/20 PASS |
| QA profundo | 20 rondas × 20 mods = 400/400 PASS |
| ZIPs individuales | 20/20 PASS |
| `Esperon-Completo.zip` | PASS; 20 miembros |
| CRC de los 21 ZIPs | PASS |
| Audio original | Sin cambios |
| Personajes, stages, HUD y note styles | Sin cambios funcionales |

## Límites declarados

El laboratorio verifica contratos, resolución de rutas, parseo de assets, procedencia vocal y empaquetado. No sustituye un playtest táctil en un dispositivo Android/iOS real. En particular, la sensación de adelanto o retraso puede depender de latencia, caché o configuración del dispositivo aun cuando los timestamps del chart sean correctos. La validación definitiva de percepción debe realizarse en Chart Editor mediante Audio Sync Test y posteriormente en FNF Mobile V-Slice 0.8.6.

## Evidencia principal

- `playstate-resolver-before-fix.json`: 0/60 antes del parche.
- `playstate-resolver-production-v261.json`: 60/60 después del parche.
- `production-vocal-gate-v261.json`: procedencia vocal de producción.
- `contracts-assets-v261.json`: contratos, personajes, stages, carátulas y HScript.
- `qa-20x20-v261.json`: 400 revisiones.
- `zip-gate-v261.json`: 20 ZIPs individuales y colección.
- `freeplay-covers-contact-sheet-v261.png`: inspección visual de las 20 carátulas.

## Referencias

[1]: https://funkincrew.github.io/funkin-modding-docs/02-custom-songs-and-custom-levels/02-04-what-are-variations.html "FNF Modding Docs: What are variations?"
[2]: https://www.youtube.com/@Esperon "Canal oficial de Esperón en YouTube"
