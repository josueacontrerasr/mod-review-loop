# Hallazgos iniciales sobre visibilidad V-Slice

## Fuente oficial: Funkin v0.8.6

La release oficial v0.8.6 indica correcciones de Polymod, incluida la validación de argumentos y compatibilidad con imports de módulos. URL: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6

## Caso oficial de Freeplay: issue #3109

En el issue https://github.com/FunkinCrew/Funkin/issues/3109, un mod no aparecía en Freeplay porque la week no era visible y faltaba un PNG con el nombre de la week. La conversación también señala que se requieren dificultades y variaciones para Freeplay; posteriormente se indica que la canción debía estar dentro de una week/level para aparecer en Story Mode.

Aplicación al diagnóstico actual: además de validar ZIP y assets, hay que comprobar `data/levels/<level-id>.json`, visibilidad del level, el icono/PNG que espera el level o week, el vínculo de la canción dentro del arreglo `songs`, las dificultades y las variaciones de Freeplay, y si el ID del level coincide con la carpeta y los assets.

## Código oficial de SongRegistry v0.8.6

La clase `SongRegistry` de v0.8.6 (`https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/data/song/SongRegistry.hx`) escanea `songs/` buscando archivos que terminen en `-metadata.json`; el ID se obtiene del primer segmento de la ruta. Para el ID `solare`, el juego intenta leer `data/songs/solare/solare-metadata.json` y `data/songs/solare/solare-chart.json`. Esta parte sí coincide con los mods actuales.

La URL probada para `source/funkin/data/level/LevelRegistry.hx` devolvió 404; se debe localizar el registro de niveles mediante el árbol oficial o los nombres usados por el código de v0.8.6, sin asumir que el path consultado es correcto.

## Código oficial de levels v0.8.6

`LevelRegistry.hx` está en `source/funkin/data/story/level/LevelRegistry.hx` y registra los datos desde el registro `levels`; los levels modded se ordenan al final.

`LevelData.hx` define `LEVEL_DATA_VERSION = 1.0.2` y exige `name`, `titleAsset` no vacío y `songs`; `visible` es opcional pero por defecto `true`. El campo `capsule` es opcional y se usa al mostrar canciones en Freeplay. Un level debe enlazar el ID exacto de cada canción mediante `songs: ["song-id"]`, y `titleAsset` debe resolver el gráfico del level en Story Mode.

## Código oficial de SongData y Freeplay v0.8.6

`SongData.hx` define `SongPlayData.album`, `songVariations`, `difficulties`, `ratings`, `characters`, `stage` y `noteStyle` dentro de `playData`. El campo `album` fuera de `playData` es desconocido para el parser y no controla la carátula de Freeplay.

`FreeplayState.hx` importa y utiliza `SongRegistry` y `LevelRegistry`. La lista de canciones se forma desde datos registrados; por tanto se debe comprobar simultáneamente que SongRegistry pueda cargar la metadata y chart y que cualquier level/capsule referido por Freeplay tenga IDs y assets resolubles.

## Hallazgo decisivo de FreeplayState

En `FreeplayState.hx` v0.8.6, durante la inicialización del menú, el juego recorre `LevelRegistry.instance.listSortedLevelIds()`, obtiene cada `Level` y luego recorre `level.getSongs()`. Solo después llama a `SongRegistry.instance.fetchEntry(songId, {variation: currentVariation})` y añade `FreeplaySongData`. Por ello, una canción que solo tiene `data/songs/<id>/...` pero no está enlazada desde un `data/levels/<level-id>.json` no entra en Freeplay ni Story Mode.

Esto coincide exactamente con el repositorio actual: los mods tienen metadata, chart y album, pero no tienen ningún `data/levels/*.json`. La causa principal está confirmada, no es una sospecha.

## Carga de assets de Story Mode

`Level.hx` construye el título con `Paths.image(_data.titleAsset)`, y `LevelProp.hx` carga props estáticos con `Paths.image(propData.assetPath)` cuando `animations` está vacío; solo usa Sparrow atlas si se declaran animaciones. Por tanto, para la corrección se pueden generar `images/storymenu/<level-id>.png` y props PNG estáticos en `images/storymenu/props/`, enlazados desde `data/levels/<level-id>.json` sin HScript adicional.

## Aplicación al repositorio Esperón

La reparación de V2.1.3 añade un level visible por canción bajo `data/levels/esperon-<song>.json`, enlaza el ID exacto en `songs`, crea `titleAsset` y props estáticos resolubles bajo `images/storymenu/`, y mueve cada album al campo `playData.album`. El laboratorio QA incluye una regla de alto nivel para bloquear futuras entregas sin estos registros.
