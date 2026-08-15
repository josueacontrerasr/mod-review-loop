# Hallazgos oficiales para el diagnóstico PlayState

## Variaciones

La documentación oficial de modding describe las variaciones como grupos de dificultades que comparten metadata. El archivo `metadata.json` define las variaciones de una canción y el juego busca `metadata-<variationID>.json` y `chart-<variationID>.json` para cada variación. Esto hace que el mensaje `variation default` sea una pista crítica: el cargador puede estar buscando archivos específicos de la variación default, no solamente un mapa `notes` dentro de un único chart.

Fuente: https://funkincrew.github.io/funkin-modding-docs/02-custom-songs-and-custom-levels/02-04-what-are-variations.html

## V-Slice 0.8.6

El release oficial 0.8.6 indica correcciones relacionadas con sufijos correctos de tracks vocales en el Chart Editor, scripts de canciones empaquetadas durante playtests y cambios de variaciones no-default. Estas correcciones justifican comprobar rutas y nombres de archivos de variación, además de la estructura de audio, antes de regenerar notas.

Fuente: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6

## Nota metodológica

La página general de charting consultada describe campos y mappings de forma más reciente y no se tomará como autoridad única para el contrato 0.8.6. La decisión final se basará en la fuente local de SongData/PlayState 0.8.6, archivos de referencia y la reproducción de las 60 combinaciones `default/easy`, `default/normal` y `default/hard`.

Fuente: https://funkincrew-funkin-59.mintlify.app/systems/charting
