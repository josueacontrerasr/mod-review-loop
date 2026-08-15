# Hallazgos de compatibilidad para barra de vida V-Slice

La documentación oficial de GitHub para `createCommitOnBranch` confirma que la mutación añade archivos y actualiza una rama de forma atómica, con una punta esperada para evitar sobrescrituras.[1]

Para el HUD, se consultó de forma pasiva el repositorio público `JugieNoob/V-Slice-Healthbar-Plus`. Su módulo HScript usa `PlayState.instance.healthBar.createFilledBar(opponentColor, playerColor)` y `updateBar()` después de comprobar que existen la barra y los iconos. El patrón demuestra que la recolorización de la barra puede hacerse en V-Slice sin tocar el chart, BPM, offsets, notas ni audio. No se reutilizará código ni recursos de terceros; se implementará una clase mínima propia con colores derivados de la paleta ya generada para cada canción.

Las llamadas serán defensivas y se limitarán a la creación de PlayState. La actualización visual no ejecutará trabajo por fotograma ni inspección de píxeles, y no añadirá mecánicas de juego.

## Referencias

[1] [GitHub Docs — `createCommitOnBranch`](https://docs.github.com/en/graphql/reference/commits#mutation-createcommitonbranch)

[2] [JugieNoob — V-Slice Healthbar Plus (referencia pública inspeccionada pasivamente)](https://github.com/JugieNoob/V-Slice-Healthbar-Plus)
