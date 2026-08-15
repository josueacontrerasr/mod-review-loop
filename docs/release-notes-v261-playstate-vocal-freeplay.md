# Esperón FNF Mobile V-Slice 0.8.6 — V2.6.1

Esta versión corrige el error `Error loading PlayState` que aparecía al iniciar las canciones en `easy`, `normal` y `hard`. El problema era la ausencia de `generatedBy` en los charts; los 20 charts ahora incluyen el valor compatible con V-Slice 0.8.6:

```json
"generatedBy": "Friday Night Funkin' - 0.8.6"
```

Las flechas fueron refinadas para proceder exclusivamente de `Voices-*.ogg`. El instrumental no se usa para generar notas. Las tres dificultades se conservan con densidad progresiva y lanes de jugador `d=0..3`.

También se sustituyeron las 20 imágenes de Freeplay por miniaturas seleccionadas de las publicaciones oficiales de Esperón, convertidas a PNG 512×512 y enlazadas mediante `freeplay/albumRoll/`.

El Release incluye 21 archivos ZIP:

- 20 mods individuales `Mod-<Canción>-V2.6.1.zip`.
- `Esperon-Completo.zip`, con los 20 mods completos en una sola descarga.

Los gates finales fueron: 60/60 casos PlayState, 20/20 contratos/assets, 20/20 loader headless, 400/400 revisiones QA, 20/20 ZIPs individuales y colección PASS. Los ZIPs no incluyen reportes, logs ni archivos de evidencia.

La validación perceptual definitiva todavía depende de Audio Sync Test en Chart Editor y de un playtest en FNF Mobile V-Slice 0.8.6, porque la latencia de un dispositivo móvil no puede certificarse mediante análisis estático.
