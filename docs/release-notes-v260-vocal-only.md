# Esperón FNF Mobile V-Slice 0.8.6 — V2.6.0 Vocal-only

## Mejora principal

Las flechas de los 20 mods ahora se generan exclusivamente desde `Voices-*.ogg` cuando existe actividad vocal. `Inst.ogg` se conserva para reproducir el instrumental, pero no se utiliza como fuente para crear notas ni acentos rítmicos.

## Validación

Se verificaron 20 canciones y 60 dificultades. El gate de procedencia vocal pasó 20/20 canciones; el VAD independiente pasó 60/60 dificultades; la prueba dinámica registró 20 lecturas de fuentes `Voices-*.ogg` y cero lecturas de `Inst.ogg`; el runtime V-Slice 0.8.6 pasó 20/20; el QA 20×20 pasó 400/400; y el gate ZIP pasó los 20 paquetes individuales y la colección de 20 miembros.

El workflow remoto `qa-vocal-only-v260.yml` terminó en `success` en el run `31898774095` y publicó artifacts.

## Entrega

Esta versión contiene 20 ZIPs individuales y `Mod-Esperon-Coleccion-V2.6.0.zip`. La carpeta de entrega no incluye reports, logs ni archivos de laboratorio.

## Limitación

La procedencia de cada nota es vocal-only, pero la certificación perceptual final de sílabas, cantante y latencia móvil todavía requiere Audio Sync Test dentro de Chart Editor y playtest en FNF Mobile V-Slice 0.8.6.
