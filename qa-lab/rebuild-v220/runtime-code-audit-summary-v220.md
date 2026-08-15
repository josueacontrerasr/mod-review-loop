# Auditoría de código runtime V2.2.0 — FNF Mobile V-Slice 0.8.6

## Resultado

Se revisaron en paralelo los 20 mods V2.2.0 siguiendo cada referencia desde metadata y level hasta los JSON de personajes, atlas PNG/XML, escenarios, props, note styles, álbumes de Freeplay, charts y módulos HScript.

| Área de código | Resultado |
|---|---:|
| Metadata 2.2.4 y `playData` | 20/20 PASS |
| IDs de jugador/rival y JSON de personajes 1.0.2 | 20/20 PASS |
| `renderType`, `assetPath` y resolución `shared:` | 40/40 personajes PASS |
| Atlas XML, `imagePath`, PNG y límites de frames | 40/40 atlas PASS |
| Prefijos `Idle`, `Left`, `Down`, `Up`, `Right` y variantes hold | 40/40 personajes PASS |
| Stage JSON, props y assets visuales | 20/20 PASS |
| Levels visibles, `songs[]` y `titleAsset` | 20/20 PASS |
| Note styles, note atlas, strumline y judgments | 20/20 PASS |
| Álbum, portada y título de Freeplay | 20/20 PASS |
| Charts, dificultades, tiempos ordenados y eventos | 20/20 PASS |
| Imports y clase `Module` en HScript | 20/20 PASS |
| Validador independiente sync/UI | 20/20 PASS; 19 warnings esperados de evidencia vocal |

## Qué se comprobó

Cada personaje declara un `renderType` permitido, un `assetPath` que resuelve a PNG/XML y animaciones cuyos prefijos coinciden con frames reales del atlas. Cada atlas tiene `imagePath`, frames válidos, textura existente y coordenadas dentro de los límites del PNG. Esto cubre las causas estáticas más frecuentes de personajes invisibles o congelados.

Cada metadata enlaza IDs existentes de personaje, escenario, note style y álbum. Los stages resuelven sus props y los levels enlazan la canción mediante `songs[]`, tienen `visible` activo y resuelven `titleAsset`. Los note styles resuelven sus atlas de notas, strumline, judgments y números de combo, incluidos sus prefijos. Los HScript contienen los imports de `Module` y `PlayState`, extienden `Module` y usan hooks de ciclo de vida reconocibles.

## Resultado de corrección

No se detectó un error de código confirmado, por lo que **no se modificaron personajes, escenarios, charts, metadata, HScript ni audio**. La auditoría sí generó evidencia nueva y se conserva en este directorio. El repositorio no cuenta con compilador Haxe/HScript instalado; por esa razón la validación de HScript es estática y no una compilación real del motor.

## Limitaciones

Un PASS estático confirma que los enlaces, prefijos, archivos y contratos son coherentes; no puede demostrar por sí solo que el renderer de FNF Mobile dibuje cada frame en un dispositivo. Para cerrar definitivamente un incidente de invisibilidad o animación trabada todavía se necesita abrir cada ZIP individual en FNF Mobile V-Slice 0.8.6 y comprobar Freeplay, Story Mode, inicio de canción, idle, las cuatro direcciones, holds, stage, props y HUD.

La metadata actual tiene `playerVocals` y `opponentVocals` vacíos y los paquetes distribuyen `Inst.ogg`; esto no rompe la visibilidad de personajes, pero significa que la sincronía vocal no puede considerarse certificada por esta auditoría.

## Referencias

[1] [FunkinCrew — `CharacterData.hx`](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/character/CharacterData.hx)  
[2] [FunkinCrew — `StageData.hx`](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/stage/StageData.hx)  
[3] [FunkinCrew — `SongData.hx`](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/song/SongData.hx)  
[4] [FunkinCrew — `LevelData.hx`](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/story/level/LevelData.hx)
