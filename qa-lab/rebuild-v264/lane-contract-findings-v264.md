# V2.6.4 — hallazgos de diagnóstico

## Evidencia visual aportada por el usuario

Las cuatro capturas muestran el mismo defecto de gameplay en dos escenarios distintos: las flechas descendentes se apilan en la columna izquierda/oponente y la strumline inferior del jugador conserva sus cuatro receptores sin recibir una distribución jugable. La captura de Freeplay muestra literalmente `ALBUM PLACEHOLDER` en el panel de álbum, no una carátula de canción.

## Diagnóstico del baseline V2.6.3

Los 21 charts contienen principalmente lanes `d=0..3`, con distribución no vacía en varias direcciones pero sin indicar la strumline del jugador. El diagnóstico local contabilizó 14,596 notas sin coincidencia con los timestamps del archivo de alineación V2.6.3 porque esa evidencia histórica no coincide con el chart runtime actual; por eso V2.6.4 debe reconstruir la evidencia desde la fuente canónica y no reutilizar ese informe como certificación.

Los JSON de álbum declaran rutas `freeplay/albumRoll/esperon-<song>-art` y los PNG existen como 512×512. Sin embargo, la captura demuestra que la ruta estática no es suficiente: se debe probar la resolución efectiva del album asset, el `playData.album`, el JSON de álbum y el fallback del juego para evitar que Freeplay use el placeholder.

## Fuente oficial consultada

La documentación oficial de Charting System de FunkinCrew define que `d=0..3` pertenece a la strumline del oponente y `d=4..7` a la strumline del jugador; el mapeo de dirección es `0/4=Left`, `1/5=Down`, `2/6=Up`, `3/7=Right`. También define `l` como duración positiva en milisegundos para holds.

Referencia: https://funkincrew-funkin-59.mintlify.app/systems/charting

## Decisión técnica

El generador V2.6.4 debe producir notas vocales del cantante en lanes `4..7`, no `0..3`. La asignación de dirección debe alternar las cuatro direcciones de jugador y conservar los timestamps. El gate debe rechazar charts donde las notas vocales usen exclusivamente `0..3`, aunque el note style tenga cuatro prefijos válidos.
