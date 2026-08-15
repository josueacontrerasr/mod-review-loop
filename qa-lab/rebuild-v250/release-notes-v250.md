# Esperón FNF Mobile V-Slice 0.8.6 — V2.5.0

## Corrección principal

V2.5.0 corrige el fallo que hacía invisibles las notas descendentes en los 20 mods. El diagnóstico comparó los charts con el contrato oficial de `SongData.hx`: `d=0..3` es la strumline del jugador y `d=4..7` es la segunda strumline/oponente. Las versiones anteriores habían generado todas las notas del jugador en `d=4..7`; por eso podían aparecer los receptores sin que el jugador recibiera notas visibles.

Todos los charts V2.5.0 fueron reconstruidos con notas del jugador exclusivamente en `d=0..3`. También se corrigieron los generadores legacy para que futuras ejecuciones no reproduzcan el mismo error.

## Sincronización

Los charts se generaron con prioridad vocal: onsets detectados sobre `Voices-<player>.ogg` mediante VAD CPU, consenso de detectores de onset y una pasada de verificación independiente. Después se añadieron acentos instrumentales secundarios con límites conservadores. La cobertura vocal dentro de 120 ms fue validada con mínimos de 0.85 en fácil, 0.80 en normal y 0.75 en difícil; los valores obtenidos fueron superiores en las 20 canciones y 60 dificultades.

Las tres dificultades mantienen el mismo mapa temporal base con densidad creciente: fácil usa separación mínima de 360 ms y velocidad 0.80; normal usa 220 ms y velocidad 1.00; difícil usa 140 ms y velocidad 1.22. Los conteos de notas cumplen `easy < normal < hard` en todas las canciones.

## Preservado

Los archivos `Inst.ogg`, `Voices-*.ogg` y `timeChanges` se conservaron sin cambios. Las carátulas de Freeplay siguen usando la ruta oficial `freeplay/albumRoll/`; los note styles conservan `version: 1.0.0` y `fallback: "funkin"`, compatibles con el rango de esquema de V-Slice 0.8.6.

## Validación

- Runtime V-Slice: 20/20 PASS.
- ZIP installation layout: 20 ZIPs individuales PASS, colección PASS, CRC PASS.
- QA archivo por archivo: 20 rondas × 20 mods = 400 revisiones PASS; cada ronda revisó aproximadamente 900 archivos fuente.
- Sincronía voice-first: 20/20 canciones, 60/60 dificultades PASS.
- Entrega: carpeta `Mods .zip terminados/` contiene únicamente 20 ZIPs V2.5.0 y una colección V2.5.0.

## Límite de certificación

La validación estática, de assets y de audio no sustituye un playtest perceptual dentro de FNF Mobile 0.8.6 en un dispositivo real. Al instalar, eliminar primero los ZIPs anteriores, importar la versión V2.5.0, cerrar completamente FNF Mobile y volver a abrirlo para evitar caché de assets. Si una nota todavía no se ve, el siguiente dato necesario sería un video o captura del gameplay en el dispositivo y el modelo exacto del teléfono.

## Referencias

- [FunkinCrew — Release v0.8.6](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)
- [FunkinCrew — Modding Documentation](https://funkincrew.github.io/funkin-modding-docs/)
- [Creating a Note Style](https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html)
- [Polymod — Creating Mods](https://polymod.io/docs/creating-mods/)
