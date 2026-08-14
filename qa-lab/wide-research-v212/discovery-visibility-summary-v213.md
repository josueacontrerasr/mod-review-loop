# Diagnóstico y corrección de visibilidad en Freeplay y Story Mode

**Objetivo:** explicar por qué las 20 canciones Esperón no aparecían en FNF Mobile V-Slice 0.8.6 y corregir únicamente los contratos de descubrimiento confirmados.  
**Resultado:** **corregido y validado en V2.1.3 — 20/20**.

## Causa raíz confirmada

La auditoría encontró que los 20 mods tenían `data/songs/<song-id>/` con metadata y chart, pero ninguno tenía un archivo `data/levels/*.json`. Esto impedía que el juego los enumerara en ambos menús. El código oficial de `FreeplayState.hx` v0.8.6 recorre `LevelRegistry`, obtiene cada level y solo entonces añade las canciones incluidas en `level.getSongs()` a la lista de Freeplay. Por la misma razón, Story Mode tampoco podía mostrar una week/level inexistente.[1] [2]

La auditoría encontró además un segundo error: `album` estaba en la raíz del metadata, mientras que el contrato oficial lo define dentro de `playData.album`. El parser tolera el campo desconocido, pero Freeplay no lo usa para asociar la carátula.[3]

| Hallazgo antes de la corrección | Resultado en 20 mods |
|---|---:|
| `data/levels/*.json` ausente | 20/20 |
| Canción sin enlace `songs[]` de un level | 20/20 |
| `album` fuera de `playData` | 20/20 |
| `playData.songVariations` ausente | 20/20 opcional; se normalizó a `[]` |

## Corrección aplicada en V2.1.3

Cada mod ahora contiene `data/levels/esperon-<song-id>.json` con schema `1.0.2`, `visible: true`, `songs: ["<song-id>"]`, `titleAsset`, cápsula de Freeplay, fondo temático y props estáticos. También se generaron los PNG necesarios bajo `images/storymenu/` y `images/storymenu/props/`. El campo del álbum fue movido a `playData.album` y se conservaron las carátulas y títulos existentes. No se tocaron BPM, offsets, charts, audio, voces ni sincronización musical.

Los 20 ZIP V2.1.2 anteriores fueron reemplazados en `Mods .zip terminados/` por 20 ZIP V2.1.3 y una colección V2.1.3. La carpeta ahora contiene únicamente los 21 ZIP finales; los ZIP anteriores quedaron archivados en `dist/historico/discovery-pre-fix-v2.1.2/`.

## Validación paralela posterior

La revalidación se ejecutó sobre las carpetas fuente y los ZIP finales. Los resultados fueron idénticos en ambos lados.

| Prueba | Resultado |
|---|---:|
| Auditoría de descubrimiento fuente | 20/20 PASS |
| Auditoría de descubrimiento ZIP | 20/20 PASS |
| Layout de instalación V-Slice 0.8.6 | 20/20 PASS |
| Cross-validation con 3 referencias oficiales | PASS |
| Paridad byte a byte fuente ↔ ZIP | 20/20 PASS |
| Auditoría integral de rutas, schemas, PNG/XML, HUD y OGG | 20/20 PASS |
| Laboratorio QA | 20 rondas × 20 mods = 400 revisiones; 0 errores, 0 warnings |

Además, el laboratorio QA fue reforzado para que futuras revisiones fallen si falta un level, si la canción no aparece en `songs[]`, si `visible` es falso, si `titleAsset` no resuelve o si `album` vuelve a quedar fuera de `playData`. El modo `--clean` también fue corregido para limpiar solo salidas generadas y no borrar la evidencia Wide Research rastreada.

## Alcance y limitación restante

La causa de que no aparecieran en los menús quedó corregida a nivel de contratos de descubrimiento y empaquetado. La confirmación final de funcionamiento visual requiere importar un ZIP V2.1.3 en FNF Mobile V-Slice 0.8.6, abrir Freeplay y Story Mode y ejecutar un playtest en Android o iOS. GitHub Actions no puede sustituir ese renderer oficial ni la prueba táctil del dispositivo. La sincronía vocal conserva su estado honesto de `PASS_EVIDENCE_ONLY` hasta completar Audio Sync Test y playtest móvil.

## Referencias

[1] [FunkinCrew — `FreeplayState.hx` v0.8.6](https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/ui/freeplay/FreeplayState.hx)  
[2] [FunkinCrew — `LevelData.hx` v0.8.6](https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/data/story/level/LevelData.hx)  
[3] [FunkinCrew — `SongData.hx` v0.8.6](https://raw.githubusercontent.com/FunkinCrew/Funkin/v0.8.6/source/funkin/data/song/SongData.hx)  
[4] [FunkinCrew — FNF v0.8.6 release](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)  
[5] [FunkinCrew — Freeplay issue #3109](https://github.com/FunkinCrew/Funkin/issues/3109)
