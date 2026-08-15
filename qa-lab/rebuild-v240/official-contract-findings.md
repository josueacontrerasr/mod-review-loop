# Hallazgos oficiales para regresión Freeplay y notas V2.4.0

## Custom Note Styles

Fuente: https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html

La documentación oficial indica que `fallback: "funkin"` es el fallback recomendado. El asset `note` necesita datos para `left`, `down`, `up` y `right`; `noteStrumline` necesita `Static`, `Press`, `Confirm` y `ConfirmHold` por dirección. También distingue `holdNote`, `noteSplash`, `holdNoteCover`, `countdown`, `judgementSick` y `comboNumber`. Un custom note style con assets faltantes debe poder recurrir al fallback; los prefijos del atlas deben coincidir exactamente.

## Album Freeplay

Fuente oficial: https://github.com/FunkinCrew/funkin.assets/blob/main/preload/data/ui/freeplay/albums/volume1.json

El JSON oficial vive en `preload/data/ui/freeplay/albums/<id>.json` y usa `albumArtAsset`/`albumTitleAsset` con rutas como `freeplay/albumRoll/volume1` y `freeplay/albumRoll/volume1-text`, es decir, rutas relativas a `images/`. La comparación con los mods Esperón debe comprobar especialmente si el runtime móvil 0.8.6 espera `freeplay/albumRoll/...` en lugar de `freeplay/albums/...`, además de PNG/XML basenames, prefijos y merge de metadata.

## Note style oficial completo

Fuente oficial: https://github.com/FunkinCrew/funkin.assets/blob/main/preload/data/notestyles/funkin.json

El note style oficial `funkin.json` usa `assetPath: "shared:notes"` para las notas y `assetPath: "shared:noteStrumline"` para los receptores, con prefijos `noteLeft`, `noteDown`, `noteUp`, `noteRight` y `static/press/confirm/confirmHold` por dirección. Por tanto, el prefijo `shared:` en note styles sí es válido y no debe eliminarse como se hizo con personajes/stages. El problema de notas invisibles debe investigarse en la existencia/ruta exacta de PNG/XML, nombres de frames, merge del JSON, contenido del chart, fallback y versión instalada; no se debe corregir quitando `shared:` a ciegas.

## Charting y versión

La documentación oficial consultada en https://funkincrew-funkin-59.mintlify.app/systems/charting muestra actualmente un ejemplo con chart `version: "2.2.4"`, `t` en milisegundos y direcciones 0–3 para opponent / 4–7 para player. La ruta tentativa `source/funkin/data/song/SongChartData.hx` en el tag GitHub `v0.8.6` devolvió 404, por lo que no se usará esa URL fallida como evidencia. Antes de migrar charts 2.0.0 a otra versión se debe verificar el archivo real del tag 0.8.6 o el formato exportado por el Chart Editor de la versión móvil instalada; una migración automática sin esa verificación podría romper la carga.

## Constantes oficiales v0.8.6

Fuente: `FunkinCrew/Funkin` tag `v0.8.6`, `source/funkin/data/song/SongRegistry.hx`, consultado mediante GitHub API de solo lectura.

`SONG_METADATA_VERSION = 2.2.4` con regla `2.2.x`; `SONG_CHART_DATA_VERSION = 2.0.0` con regla `2.0.x`; `SONG_MUSIC_DATA_VERSION = 2.0.0` con regla `2.0.x`. Por tanto, los charts actuales `version: 2.0.0` sí coinciden con V-Slice 0.8.6. La documentación web actual que muestra chart 2.2.4 no debe usarse para migrar este objetivo móvil.

El código `SongData_v2_0_0.hx` confirma que en metadata antigua `noteSkin` fue renombrado a `noteStyle` en v2.2.0; los mods ya usan el campo moderno `noteStyle`.
