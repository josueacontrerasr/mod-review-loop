## Correcciones incluidas

Esta versión corrige el fallo que producía `Null Object Reference` en `FlxAtlasFrames`/`Paths` durante la construcción de `AlbumRoll`: cada uno de los 20 `albumTitleAsset` ahora incluye su PNG y un atlas Sparrow XML válido con los prefijos `idle0` y `switch0` que usa FNF Mobile V-Slice 0.8.6.

También se incorporan stems vocales separados mediante Demucs como `Voices-<personaje>.ogg`, se enlazan al strumline del jugador y se reemplazan los charts de producción por candidatos guiados por actividad vocal. Los candidatos fueron comparados contra un segundo detector independiente; los reportes guardan hashes, duración, distancia temporal y limitaciones. No se cambiaron BPM ni offsets automáticamente.

## Validación

Los 20 mods pasaron el auditor de Freeplay/AlbumRoll, personajes, stages, Story Mode y rutas visuales. El laboratorio ejecutó **20 rondas × 20 mods = 400 revisiones**, con 0 errores y 0 warnings. Los 20 ZIP individuales y la colección pasaron CRC, raíz única, política runtime limpia, metadata/chart/manifest y presencia de XML de título y voces.

## Instalación

Descarga un ZIP individual `Mod-<Canción>-V2.2.1.zip` y extrae su única carpeta de mod dentro de la carpeta `mods` de FNF Mobile V-Slice 0.8.6. La colección contiene los 20 ZIPs individuales; no la extraigas como si fuera un mod individual.

## Límite importante

Los análisis automáticos no pueden certificar por sí solos la semántica de cada sílaba, la asignación de personaje por línea vocal ni sustituir `Audio Sync Test` y el playtest final dentro de FNF Mobile V-Slice 0.8.6. La versión queda marcada como revisión humana requerida para esa última confirmación.
