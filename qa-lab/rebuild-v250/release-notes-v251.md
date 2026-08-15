# Esperón FNF Mobile V-Slice 0.8.6 — V2.5.1

## Motivo de la revisión

La revisión fresca de V2.5.0 mostró que muchas notas individuales estaban cerca de algún onset vocal, pero fácil y normal omitían demasiados eventos vocales y los acentos instrumentales inflaban el error cuando todo se comparaba contra la voz. V2.5.1 reconstruye los charts con una prioridad vocal más estricta y evalúa por separado voz e instrumental.

## Cambios

Los 60 charts de las 20 canciones se regeneraron usando onsets de las voces distribuidas `Voices-<player>.ogg` como fuente primaria. Las notas vocales se colocan en lanes oficiales de jugador `d=0..3`. Los acentos instrumentales se conservan como capa secundaria y se limitan a 5 % en fácil, 10 % en normal y 15 % en difícil respecto de las notas vocales. Cada familia se valida contra su propia señal: las notas vocales contra la voz y los acentos contra `Inst.ogg`.

Las tres dificultades mantienen una progresión de densidad y velocidad. Fácil usa separación mínima aproximada de 300 ms y velocidad 0.78; normal usa 180 ms y velocidad 0.98; difícil usa 120 ms y velocidad 1.18. Se preservan los archivos OGG y `timeChanges`; solo se sustituyen los JSON de chart y se actualiza `mod_version` a `2.5.1`.

## Resultados de sincronía

Las 60 dificultades pasan el gate de nota vocal→voz y nota rítmica→instrumental. La cobertura de cada nota vocal respecto del onset vocal más cercano es 100 % dentro de 120 ms en las 60 dificultades bajo el método de anclajes utilizado. La cobertura evento vocal→nota se interpreta según la densidad de dificultad: el mínimo fue 55.93 % en fácil, 76.26 % en normal y 100 % en difícil; esto significa que fácil y normal contienen deliberadamente menos flechas que micro-onsets vocales, no que sus flechas estén fuera de la voz. Los percentiles de eventos se conservan en la evidencia antes/después para revisión.

## QA y distribución

- Runtime V-Slice 0.8.6: 20/20 PASS.
- ZIP layout: 20 ZIPs individuales y colección PASS, con CRC válido y sin evidencia dentro de los ZIPs.
- QA profundo: 20 rondas × 20 mods = 400 revisiones PASS; 900 archivos examinados por ronda.
- Promoción: 20/20 charts cambiados respecto de V2.5.0; audio y `timeChanges` sin cambios.
- Carpeta de entrega: solo ZIPs finales V2.5.1.

## Límite de certificación

La auditoría usa VAD CPU, consenso de onsets y comparación contra señales vocales/instrumentales reales; no sustituye el Audio Sync Test del Chart Editor ni un playtest perceptual dentro de FNF Mobile 0.8.6. Después de instalar, elimina la versión previa, cierra completamente el juego y vuelve a abrirlo para descartar caché de assets. Si el desfase percibido permanece, será necesario un video del gameplay y el modelo del dispositivo para distinguir timing del chart de latencia o reproducción móvil.

## Referencias

- [FunkinCrew — Release v0.8.6](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)
- [FunkinCrew — Modding Documentation](https://funkincrew.github.io/funkin-modding-docs/)
- [Creating a Note Style](https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html)
- [Polymod — Creating Mods](https://polymod.io/docs/creating-mods/)
