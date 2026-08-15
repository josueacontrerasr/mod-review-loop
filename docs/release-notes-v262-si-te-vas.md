# Esperón V-Slice 0.8.6 — V2.6.2

## Novedades

Esta versión añade el mod completo de **Si Te Vas** y amplía la colección de Esperón de 20 a 21 canciones. También regenera `Esperon-Completo.zip` para incluir los 21 mods completos.

El nuevo mod utiliza estructura Polymod compatible con **FNF Mobile V-Slice 0.8.6**, tres dificultades (`easy`, `normal`, `hard`), personajes y escenario propios, note style propio, HUD compatible, metadata/chart V-Slice y carátula de Freeplay 512×512 derivada de la imagen embebida en el audio fuente de Si Te Vas.

## Sincronización vocal

Los charts de Si Te Vas se generaron a partir del stem `Voices-esperon-si-te-vas.ogg` obtenido mediante separación reproducible del M4A fuente. El instrumental no se utilizó para generar timestamps. Las 20 canciones anteriores se reanalizaron con el mismo pipeline vocal-only; las 21 canciones terminaron con cero notas fuera de segmentos vocales, cero lanes inválidos y cero metadata de candidato en producción.

## Archivos de descarga

La Release contiene 22 assets: `Esperon-Completo.zip` y 21 ZIPs individuales, uno por canción. Se recomienda descargar `Esperon-Completo.zip` para instalar la colección completa. Al extraerlo, coloca las 21 carpetas `esperon-dano-*` dentro de la carpeta `mods/` de FNF Mobile.

## Validación

La validación V2.6.2 incluye 63 casos PlayState (`21 × 3`), 21/21 contratos y assets, 21/21 loader headless móvil, 21/21 ZIPs individuales y 20 rondas por cada mod, para un total de 420 revisiones QA. GitHub Actions ejecuta el workflow actualizado mediante `workflow_dispatch` y cada 10 minutos.

Los reportes y evidencias quedan fuera de los ZIPs runtime y se publican como artifacts del workflow. Los ZIPs no contienen `.txt`, `.md`, `.log`, `.csv`, `.html` ni archivos de staging.

## Nota de sincronización móvil

Los resultados automáticos certifican la relación estática chart↔voz y la carga de los assets. Todavía se recomienda ejecutar Audio Sync Test en el Chart Editor oficial y realizar un playtest táctil en FNF Mobile V-Slice 0.8.6 para medir la latencia particular del dispositivo.
