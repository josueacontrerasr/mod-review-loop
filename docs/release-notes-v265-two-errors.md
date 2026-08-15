# Release V2.6.5 — Corrección de strumline y carátula de cápsula Freeplay

## Resumen

La V2.6.5 corrige dos fallos observados en FNF Mobile V-Slice 0.8.6. El primero no era únicamente un problema de lado de jugador: aunque V2.6.4 ya usaba el dominio correcto `d=4..7`, el cursor de dirección se reiniciaba por cada timestamp y casi todas las notas terminaban en `d=4`, que corresponde a la dirección **Left** del jugador. La V2.6.5 recorre globalmente las cuatro direcciones `d=4,5,6,7` en orden cronológico y conserva offsets separados para colisiones simultáneas. La documentación oficial define `0/4=Left`, `1/5=Down`, `2/6=Up` y `3/7=Right` [1].

El segundo fallo se verificó con la captura adjunta `1000406388.jpg`: el elemento señalado es la tarjeta grande de álbum de la pantalla Freeplay que todavía dibuja **ALBUM PLACEHOLDER**. La causa operativa de V2.6.4 fue que el gate comprobaba solamente `albumRoll` y resolución estática de álbum, pero no auditaba de forma independiente el `titleAsset` del nivel/cápsula ni el registro runtime que carga el álbum. V2.6.5 añade ambos recorridos: `data/levels/*.json → titleAsset → images/storymenu/*.png` y `playData.album → data/ui/freeplay/albums/<id>.json → albumRoll`. El runtime oficial obtiene el álbum mediante `AlbumRegistry` y luego carga `albumArtAsset` con `Paths.image`; cuando el registro no se encuentra, el componente conserva el placeholder [2] [3].

## Cambios principales

| Área | Cambio V2.6.5 |
|---|---|
| Charts | Candidatos regenerados desde las alineaciones Whisper cacheadas y promovidos con generatedBy V2.6.5. |
| Lanes | Cobertura obligatoria de `d=4,5,6,7` en Easy, Normal y Hard; se rechaza una chart con una sola dirección. |
| Holds | Se conserva la duración vocal medida, la cola RMS y el límite antes de la siguiente sílaba. |
| Freeplay | Nuevo diagnóstico y gate independiente para cápsula `titleAsset`, álbum, PNG cuadrado, PNG/XML de título y frames `idle0`/`switch0`. |
| Versionado | `_polymod_meta.json` y `config/fnf_target.json` actualizados a `2.6.5`. |
| Entrega | 21 ZIPs individuales V2.6.5 y `Esperon-Completo.zip` limpio con 21 raíces. |
| Automatización | Workflow V2.6.5 conservando `*/10 * * * *` y `workflow_dispatch`. |

## Evidencia visual incorporada

La captura `1000406386.jpg` muestra un grupo de cuatro receptores en la esquina superior izquierda y otro grupo de cuatro receptores jugables en la zona inferior. El síntoma reportado indica que la presión/activación se refleja en el grupo superior izquierdo. Por eso V2.6.5 valida tanto el dominio de lane como la cobertura de las cuatro direcciones y conserva una advertencia: la comprobación estática no puede sustituir un playtest nativo que confirme la asociación visual de cada strumline.

La captura `1000406388.jpg` identifica el placeholder de la tarjeta grande de Freeplay. Los assets locales comprobados incluyen el arte cuadrado `512×512` de `albumRoll` y el título Sparrow `512×128` con XML. En el caso de `Si Te Vas`, la referencia pública encontrada en Spotify muestra el mismo arte que contiene el texto `NUBIA`; por ello no se reemplazó esa portada válida por una imagen inventada [4].

## Validación ejecutada

| Gate | Resultado |
|---|---:|
| Candidatos aislados | 21/21 PASS |
| Charts de producción vocal | 21/21 PASS; 0 fuera de intervalo, 0 no alineadas y 0 holds inválidos |
| Lanes | 21/21 con `d=4,5,6,7` en las tres dificultades |
| Contratos y assets | 21/21 PASS |
| Cápsula y álbum Freeplay | 21/21 PASS |
| Resolver PlayState | 63/63 PASS |
| Loader headless móvil | 21/21 PASS |
| ZIP individual | 21/21 PASS |
| Esperon-Completo | PASS; 21 raíces y 945 archivos runtime |
| QA archivo por archivo | 420/420 PASS en 20 rondas × 21 mods |
| CRC de ZIPs | PASS |

> Estas pruebas cubren datos, rutas, assets, atlas, audio legible, charts y empaquetado. No se debe presentar el loader headless como ejecución del motor nativo: la latencia táctil, la caché del APK y el renderizador real en Android/iOS aún requieren playtest del dispositivo.

## Referencias

[1] [FNF Charting System — Note Direction Mapping](https://funkincrew-funkin-59.mintlify.app/systems/charting)  
[2] [FNF v0.8.6 — AlbumRegistry.hx](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/data/freeplay/album/AlbumRegistry.hx)  
[3] [FNF v0.8.6 — AlbumRoll.hx](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/ui/freeplay/AlbumRoll.hx)  
[4] [Spotify — Si Te Vas, Esperón](https://open.spotify.com/search/Esper%C3%B3n%20Si%20Te%20Vas)
