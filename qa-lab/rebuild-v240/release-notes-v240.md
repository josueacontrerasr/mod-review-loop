# Esperón FNF Mobile V-Slice 0.8.6 — V2.4.0

## Correcciones incluidas

Esta versión corrige la resolución de las carátulas de Freeplay para los 20 mods. Los manifiestos de álbum ahora apuntan a `images/freeplay/albumRoll/`, la ruta que utiliza el registro de álbumes de V-Slice 0.8.6, y cada carátula/title atlas incluye sus PNG/XML y los prefijos Sparrow requeridos (`idle0000` y `switch0000`).

También se reemplazaron los charts por una versión mixta rítmico-vocal en las tres dificultades. La base conserva eventos derivados del pulso, percusión, bajo y melodía del instrumental, mientras que los acentos vocales se mantienen en entradas y frases relevantes. Las dificultades permanecen ordenadas por densidad y velocidad: fácil `0.80`, normal `1.00` y difícil `1.22`.

## Elementos preservados

El audio instrumental y las voces se conservaron byte por byte respecto de V2.3.0. También se conservaron `timeChanges`, BPM y metadata musical; el cambio de chart está limitado a las notas mixtas y los valores de `scrollSpeed` por dificultad. Los hashes y la evidencia de invariancia se encuentran en `qa-lab/rebuild-v240/chart-promotion-v240.json`.

## Verificación realizada

Se ejecutó el validador de contratos runtime, el diagnóstico de Freeplay/note style, el validador de layout/CRC de los 20 ZIPs y una revisión de 20 rondas por 20 mods. Cada ronda recorrió todos los JSON, XML, PNG/JPG y OGG de cada mod, además de comprobar los contratos principales y el CRC del ZIP individual. La evidencia PASS se publica como artifact del workflow.

## Instalación

Para instalar una canción, extrae el ZIP individual elegido de modo que su única carpeta raíz `esperon-dano-<cancion>` quede dentro de la carpeta `mods` de FNF Mobile V-Slice. La colección contiene los 20 ZIPs individuales y un archivo de instrucciones; no contiene reportes dentro de los paquetes individuales.

## Alcance y límite conocido

La validación estática y de audio en laboratorio confirma que las rutas, atlas, JSON, charts, notas tempranas, orden temporal, audio y empaquetado resuelven. No se afirma una certificación móvil nativa de flechas visibles ni una sincronización perceptual perfecta sin ejecutar el juego en un dispositivo Android/iOS con Chart Editor/Audio Sync Test y playtest real. Después de instalar, cierra completamente FNF Mobile y vuelve a abrirlo para evitar caché de assets.
