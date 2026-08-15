# Esperón V-Slice 0.8.6 — V2.6.3

## Alineación vocal mejorada

Esta versión rehace los charts de los 21 mods para seguir la voz del cantante con una granularidad silábica. Cada sílaba confiable produce una nota en su ataque vocal; los intermedios como `oh`, `ah` y repeticiones vocales se tratan como unidades separadas cuando tienen ataques distinguibles. Las frases largas mantienen sus notas silábicas y reciben holds únicamente en vocales realmente sostenidas.

Los tiempos se derivan de `Voices-*.ogg` y se refinan con energía vocal local. El instrumental no genera notas. Easy, Normal y Hard comparten los mismos anclajes absolutos; Easy reduce densidad, mientras Normal y Hard conservan todas las sílabas confiables. Hard puede compartir la cantidad de notas de Normal cuando no existen subdivisiones vocales adicionales, pero mantiene su velocidad de desplazamiento.

## Validación

El lote final pasó 21/21 candidatos, 21/21 gate de producción silábica, 63/63 casos PlayState, 21/21 contratos/assets, 21/21 loader headless y 420/420 revisiones QA. El `Esperon-Completo.zip` contiene 21 mods y los ZIPs runtime no incluyen letras completas, transcripciones, reportes, staging ni logs.

## Descargas

La Release contiene `Esperon-Completo.zip` y 21 ZIPs individuales `Mod-<Canción>-V2.6.3.zip`. Para instalar la colección completa, extrae `Esperon-Completo.zip` y coloca las 21 carpetas de mod dentro de la carpeta `mods/` de FNF Mobile.

## Alcance de la certificación

Los resultados certifican estructura V-Slice, contratos, resolución PlayState, timestamps internos de charts, límites de holds, relación con stems vocales y carga headless. La certificación perceptual final requiere Audio Sync Test en el Chart Editor oficial y playtest real en el dispositivo, especialmente en frases largas, intermedios, cambios de tempo y el último downbeat.
