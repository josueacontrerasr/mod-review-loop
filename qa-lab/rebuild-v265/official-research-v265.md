
## Fuentes web consultadas

### Incidencia oficial sobre Album Placeholder

Fuente: https://github.com/FunkinCrew/Funkin/issues/3206

La incidencia oficial describe el síntoma “when going to freeplay, album placeholder image shows” y registra que fue corregido en la versión 0.6.0. Esto confirma que el placeholder es un fallback conocido del runtime de Freeplay y que no basta con asumir que cualquier PNG existente se está cargando. La investigación V2.6.5 debe seguir el ID/registro que selecciona el asset de la cápsula y comprobar la versión exacta del formato.

### Documentación oficial de modding

Fuente: https://funkincrew.github.io/funkin-modding-docs/

La documentación oficial mantiene capítulos separados para “Custom Songs and Custom Levels”, “Adding a Custom Level”, “Custom Note Styles” y “Using a Custom Note Style in a Song”. Esto respalda separar la corrección del nivel/cápsula Freeplay de la corrección del note style/HUD y no modificar una ruta de álbum como sustituto de la ruta de nivel.

## Contrato oficial de charting

Fuente: https://funkincrew-funkin-59.mintlify.app/systems/charting

La documentación define `d=0..3` como opponent y `d=4..7` como player. El mapeo direccional es `0/4=Left`, `1/5=Down`, `2/6=Up` y `3/7=Right`; los holds usan `l` en milisegundos. La misma documentación recomienda que las notas player estén en `d=4..7` durante las secciones del jugador.

La auditoría V2.6.5 encontró la causa adicional: la producción V2.6.4 sí estaba dentro del dominio player, pero casi todas sus notas eran `d=4` porque el cursor de dirección se reiniciaba por cada timestamp. Eso explica la activación visual repetida de la flecha izquierda. El candidato V2.6.5 ya muestra una distribución equilibrada y cronológica entre `d=4,5,6,7` en los 21 mods.

Fuente complementaria: https://github.com/FunkinCrew/Funkin/blob/main/source/funkin/ui/debug/charting/ChartEditorState.hx

El Chart Editor oficial también separa explícitamente las entradas del oponente y del jugador: teclas `1/2/3/4` para el oponente y `5/6/7/8` para el jugador; WASD corresponde al oponente y las flechas al jugador. Esto respalda que el dominio `4..7` no debe volver a trasladarse a `0..3`.
