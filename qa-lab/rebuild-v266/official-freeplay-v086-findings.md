# Evidencia oficial de Freeplay V-Slice 0.8.6

Fecha de consulta: 2026-08-15.

## AlbumRoll.hx

Fuente: https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/ui/freeplay/AlbumRoll.hx

En `updateAlbum()`, V-Slice obtiene `albumData = AlbumRegistry.instance.fetchEntry(albumId)`. Si el identificador no resuelve, registra `Could not find album data for album ID` y deja `albumData` nulo; el renderer usa el placeholder. Cuando sí resuelve, reemplaza el símbolo de arte con `Paths.image(albumData.getAlbumArtAssetKey())` y construye el título con `albumData.getAlbumTitleAssetKey()` y sus offsets.

## AlbumRegistry.hx

Fuente: https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/freeplay/album/AlbumRegistry.hx

El registro se inicializa con la ruta lógica `ui/freeplay/albums` y la regla de versión `1.0.x`. La versión declarada en el código oficial es `ALBUM_DATA_VERSION = 1.0.3` y `ALBUM_DATA_VERSION_RULE = 1.0.x`. Por ello, cada mod debe aportar `data/ui/freeplay/albums/<album-id>.json` con un `version` compatible y el `playData.album` debe coincidir exactamente con `<album-id>`.

## Implicación para Esperón V2.6.6

La cadena a verificar por cada canción es: `metadata.playData.album` → `data/ui/freeplay/albums/<album-id>.json` → `albumArtAsset`/`albumTitleAsset` → recursos resolubles bajo `images/freeplay/albumRoll/`. La existencia local de los archivos no demuestra por sí sola que el registro los acepte; por eso el gate V2.6.6 debe comprobar ID, versión `1.0.x`, rutas sin extensión, dimensiones, XML y ausencia de nombres de placeholder.
