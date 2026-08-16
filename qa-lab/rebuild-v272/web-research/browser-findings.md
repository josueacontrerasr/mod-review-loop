# Hallazgos de navegación web — sincronización vocal V-Slice

## Tutorial Chart Editor — Chaz Beshore

URL: https://www.youtube.com/watch?v=DgYL5kJY7L0

La página identifica el video como un curso de Chart Editor de FNF. El análisis audiovisual archivado en `chart-editor-tutorial-DgYL5kJY7L0.md` señala el uso de la forma de onda de voces, beat snap ajustable, muteo del instrumental, reproducción lenta, hitsounds y prueba de gameplay. Es evidencia de flujo de trabajo del editor, no una medición de nuestros OGG.

## Tutorial V-Slice Modding — Doctor Ducko

URL: https://www.youtube.com/watch?v=IrFpxAsd2KM

La página identifica el video como un tutorial de nuevas canciones y semanas en V-Slice. El análisis archivado en `vslice-modding-tutorial-IrFpxAsd2KM.md` registra carga separada de `Inst.ogg` y voces, exportación de JSON, beat snap, BPM, offsets, taps/holds y playtest. Las advertencias sobre formatos o rutas se tratan como observaciones del tutorial y se contrastan con el código/documentación oficial de V-Slice 0.8.6.

## Tutorial Chart Editor móvil — Gamer Countryballs

URL: https://www.youtube.com/watch?v=t-hSuNZn-SQ

La página lo identifica como tutorial de Chart Editor móvil para PeakSlice 0.7.3 y marca el contenido como auto-doblado. La descripción enlaza PeakSlice. La extracción visible no aporta un procedimiento textual verificable sobre sincronización de voces, por lo que se usará solo como contexto de interfaz móvil y no como autoridad para offsets de V-Slice 0.8.6.

## Fuentes oficiales consultadas

- https://funkincrew-funkin-59.mintlify.app/tools/chart-editor
- https://funkincrew-funkin-59.mintlify.app/systems/gameplay
- https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/song/SongData.hx

Estas fuentes respaldan waveform/offsets/Audio Sync Test, BPM/time changes, timestamps en milisegundos y la separación entre offset del chart y calibración del dispositivo.

## Video móvil PeakSlice

El análisis audiovisual archivado en `mobile-chart-editor-tutorial-t-hSuNZn-SQ.md` confirma waveform, muteo, beat snap, taps, holds y Botplay visibles, pero el video es PeakSlice/V-Slice 0.7.3, no la build oficial 0.8.6. Es útil para el método de revisión táctil, no para copiar rutas ni offsets.

## Gameplay High Beta Vocal Cover

URL: https://www.youtube.com/watch?v=UCAU5sqvqB4

El análisis archivado en `high-beta-vocal-chart-UCAU5sqvqB4.md` observa notas separadas para articulaciones rápidas, holds que terminan cuando decae la energía vocal, dos holds consecutivos en transiciones legato, ráfagas distribuidas entre lanes y una simplificación de vibrato a un hold. La mezcla limita la verificación exacta de cada onset; el video es una referencia de diseño y no una prueba de nuestros stems.
