# Hallazgos oficiales V2.5.0

## Fuentes consultadas

- https://funkincrew.github.io/funkin-modding-docs/06-custom-notestyles/06-01-creating-a-notestyle.html
- https://funkincrew.github.io/funkin-modding-docs/
- https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6

## Contratos relevantes

La documentación oficial indica que `data/notestyles/<id>.json` usa formato `version: 1.0.0`, que `fallback: "funkin"` es la opción recomendada para assets no definidos, y que el asset `note` requiere `left`, `down`, `up`, `right` con prefijos de atlas. `noteStrumline` requiere las variantes Static, Press, Confirm y ConfirmHold por dirección. Los `assetPath` pueden apuntar a cualquier ubicación del mod siempre que resuelvan directamente.

La release oficial 0.8.6 menciona correcciones relevantes: fallback de notestyle en PlayState, desaparición de hold note covers bajo carga, correcciones de salud/iconos y estabilidad de Polymod. Por tanto, el diagnóstico V2.5.0 debe probar fallback, `note`, `noteStrumline`, `holdNote` y la resolución efectiva del `noteStyle`, no únicamente la existencia de PNG/XML.

## Hipótesis priorizadas

1. El chart tiene notas válidas y lanes 4–7, pero el runtime Mobile podría no estar aplicando el `noteStyle` personalizado a PlayState o podría caer en el fallback si el asset `holdNote` no está definido.
2. Los assets de nota simples tienen atlas/XML, pero hay que verificar visualmente que sus frames no sean transparentes, de tamaño cero o fuera del canvas.
3. La sincronía no puede certificarse solo por orden temporal; debe recalcularse con timestamps de voz y después comparar la nota contra la voz antes que contra el instrumental.
4. Un chart que empieza varios segundos después del inicio puede dar la impresión de flechas ausentes; se deben crear anclajes vocales tempranos cuando la voz realmente entra, sin inventar notas antes del audio.

## Inspección visual de Solare

El atlas `notes/esperon-solare-notes-notes.png` mide 512×128 y muestra cuatro flechas opacas, grandes y centradas, con contorno azul y relleno naranja; no es transparente total ni tiene dimensiones cero. El atlas `notes/esperon-solare-notes-strumline.png` mide 512×384 y contiene 12 frames visibles organizados en tres filas de cuatro direcciones; tampoco presenta un canvas vacío. Esto reduce la probabilidad de que el fallo sea un PNG ausente o completamente invisible y aumenta la prioridad de probar el contrato efectivo de `noteStyle`/fallback y la forma exacta de los datos cargados por PlayState Mobile.
