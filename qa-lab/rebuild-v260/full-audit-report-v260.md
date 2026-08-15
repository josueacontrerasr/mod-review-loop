# Verificación completa de los 20 mods FNF Mobile V-Slice 0.8.6

## Resumen ejecutivo

Se ejecutó el plan Wide Research completo sobre las 20 canciones de Esperón utilizando el entorno autónomo de auditoría. La revisión cubrió audio, voces, charts, las tres dificultades, metadata, manifests, lanes, personajes, stages, HUD, HScript, note styles, carátulas, Freeplay, Storymode, estructura Android simulada, ZIPs, hashes y regresión remota.

El resultado estructural es positivo: los 20 mods pasaron los gates de contratos, assets, loader headless, charts, ZIPs y QA. Se procesaron **20 canciones, 60 dificultades, 400 revisiones QA y 900 archivos de mods**, además de los **21 ZIPs de entrega**. No se modificó ningún archivo bajo `mods/` ni ningún ZIP de producción.

> La única reserva importante es de certificación musical perceptual: los candidatos actuales se generan en modo `FULL_MIX_PROXY` cuando no existe un stem vocal distribuido y verificado. Por lo tanto, la auditoría confirma coherencia estática y matemática, pero no permite declarar sincronía vocal perceptual perfecta sin Audio Sync Test y playtest móvil.

## Estado por gate

| Gate | Resultado | Interpretación |
|---|---:|---|
| Audio y charts | 20/20 canciones, 60/60 dificultades | PASS estructural con revisión vocal manual requerida |
| Contratos y assets | 20/20 | PASS; 40 warnings corresponden a ausencia de renderer nativo |
| Loader headless Android | 20/20 | PASS de resolución estática |
| QA profundo | 400/400 | 20 rondas × 20 mods, 0 errores |
| ZIP/HScript actualizado | 20/20 + colección | PASS |
| Hashes de mods | 900/900 | Sin cambios frente al baseline |
| Hashes de entrega | 21/21 | Sin cambios frente al baseline |
| Workflow remoto | success | Artifacts publicados |

## 1. Baseline y aislamiento

La auditoría se ejecutó en la rama aislada `auto/fnf-vslice-full-audit-v260`, basada en el laboratorio V-Slice 0.8.6. El commit auditado fue `020d84fef88430bd45aac0341ea3eee6f0502f29`. Se identificaron exactamente 20 carpetas fuente `mods/esperon-dano-*` y 21 ZIPs en `Mods .zip terminados/`: 20 paquetes individuales V2.5.1 y una colección.

El baseline registró 900 archivos de mods y 21 ZIPs mediante SHA-256. La comprobación final produjo **900/900 hashes de mods correctos y 21/21 hashes de ZIPs correctos**. La rama no contiene modificaciones bajo `mods/` ni en la carpeta de entrega respecto de la producción estable.

La configuración mantiene `fnf_version: 0.8.6`, `api_version: 0.8.6`, metadata `2.2.4`, chart `2.0.0`, note style `1.0.0`, fallback `funkin` y la política de no promoción automática de charts.

## 2. Audio, voces y sincronización

Se regeneraron los 20 manifiestos de audio antes de producir candidatos, evitando reutilizar hashes stale. Los 20 candidatos y sus reportes pasaron la validación de aislamiento. La auditoría fresca de audio y charts comprobó orden temporal, lanes, densidad, scroll speed, versiones, timestamps y proximidad de notas a candidatos de onsets del audio actual.

| Medición | Resultado |
|---|---:|
| Canciones analizadas | 20/20 |
| Dificultades analizadas | 60/60 |
| Charts estructuralmente válidos | 20/20 |
| Lanes de jugador comprobados | `d=0..3` |
| Densidad easy < normal < hard | PASS |
| Scroll speed easy < normal < hard | PASS |
| Candidatos aislados | 20/20 PASS |
| Modo de análisis | `FULL_MIX_PROXY` |
| Promoción automática | 0 |

Los charts siguen priorizando la voz dentro de los límites de la evidencia disponible. Sin embargo, un onset de mezcla completa no prueba que corresponda a una sílaba, a un cantante concreto o a una dirección de strumline. Por esa razón, las 20 canciones mantienen `MANUAL_REVIEW_REQUIRED` para certificación vocal perceptual.

La auditoría matemática anterior del baseline también había encontrado cobertura conjunta de voz y ritmo de 100 % dentro de 120 ms y 0 % de notas no ancladas al clasificar notas vocales frente a voz y acentos rítmicos frente a instrumental. Esa evidencia es compatible con el resultado actual, pero no sustituye una prueba humana dentro del motor.

## 3. Charts y dificultades

Para cada una de las 60 dificultades se verificaron timestamps numéricos, no negativos y ordenados; lanes válidos; ausencia de duplicados exactos; charts no vacíos; versiones; densidad creciente y scroll speed creciente. La comparación contra candidatos actuales del audio no detectó errores estructurales que justificaran reescribir charts.

No se cambiaron BPM, `timeChanges`, offsets, notas, instrumental ni voces. Los candidatos permanecieron aislados y no se publicó una versión artificial.

## 4. Contratos, descubrimiento y resolución de recursos

El auditor paralelo comprobó manifests, metadata, charts, niveles, stages, personajes, note styles, álbumes, JSON, XML y PNG de los 20 mods. El resultado fue **20/20 PASS**. Las comprobaciones incluyeron rutas bajo `shared/images`, atlas XML, límites de frames, integridad PNG, prefijos de animación, assets de stages, note styles, album art, title atlases, levels y vínculos de canción.

El loader headless copió los 20 mods a la ruta Android simulada `qa-lab/mobile-sim/storage/emulated/0/Android/data/com.funkin.fnf/files/mods/` y resolvió estáticamente los recursos. El resultado fue **20/20 PASS**.

La verificación de descubrimiento se interpretó con el contrato actualizado V2.5.1. Dos validadores históricos devolvieron cero ZIPs porque estaban fijados a versiones antiguas V2.2.0 y V2.1.2; no representan fallos actuales. El auditor actualizado `full_zip_hscript_audit_v260.py` validó correctamente los paquetes V2.5.1 y la colección.

## 5. Personajes, stages, HUD y visuales

La hoja de contacto visual contiene 60 assets principales: album art, stages y personajes para las 20 canciones. La inspección multimodal observó carátulas con contenido visible, stages con fondos y props, y atlas de personaje con múltiples poses y expresiones. Un atlas representativo de Solare contiene una tira multi-frame visible sobre transparencia, no un PNG vacío ni un solo frame.

El auditor también comprobó 60 assets principales mediante PIL/XML, incluyendo decodificación, dimensiones, alpha, frames y límites de atlas. Los scripts HScript fueron revisados sin ejecutarse; los scripts con HUD presentan el import oficial de `funkin.modding.module.Module` y `extends Module`.

La limitación restante es el renderer: una inspección de PNG/XML y un loader estático no prueban que cada animación se reproduzca, que el HUD se actualice o que el stage aparezca en un APK real. Esto se registra como warning de entorno, no como fallo de los mods.

## 6. ZIPs y carpeta de entrega

El auditor ZIP actualizado encontró una sola raíz por paquete, `_polymod_meta.json` en la raíz runtime, metadata/chart/song manifests, audio `Inst.ogg`, voces, `data/`, `images/`, `shared/`, `songs/`, scripts Module y ausencia de carpetas de trabajo como `qa-lab/`, `artifacts/`, `logs/` o `sync-candidates/`.

El resultado fue **20/20 ZIPs PASS** y colección PASS con 20 miembros. La carpeta `Mods .zip terminados/` mantiene solo los 21 ZIPs finales V2.5.1 y ningún archivo auxiliar.

## 7. QA 20×20 y GitHub Actions

La regresión profunda terminó con **20 rondas × 20 mods = 400 registros**, estado `STABLE_PLATEAU_REACHED` y cero errores. La validación remota del workflow `qa-lab-vslice.yml` terminó correctamente en el run `31896612305`, sobre el commit `020d84fef88430bd45aac0341ea3eee6f0502f29`, y publicó artifacts.

El aviso de GitHub Actions relacionado con la deprecación de Node.js 20 pertenece a las acciones usadas por el runner y no afectó la conclusión del job. El job terminó en `success`.

## Decisión final

Todos los mods pasan la verificación estructural, de assets, carga headless, ZIP y regresión. La producción V2.5.1 debe conservarse sin cambios porque la auditoría no encontró una mejora objetiva segura que justifique modificar los mods o crear V2.6.0 como Release.

La sincronización vocal queda en dos niveles claramente separados:

| Nivel | Estado |
|---|---|
| Evidencia estática, matemática y de charts | PASS en las 20 canciones |
| Certificación vocal perceptual en el motor móvil | MANUAL_REVIEW_REQUIRED en las 20 canciones |

La siguiente acción musical válida no es regenerar notas automáticamente. Requiere stems vocales identificados por cantante/strumline o un Audio Sync Test documentado en Chart Editor, seguido de playtest en FNF Mobile V-Slice 0.8.6.

## Evidencias

| Archivo | Contenido |
|---|---|
| `qa-lab/rebuild-v260/full-audit-summary-v260.json` | Consolidado de estados y política |
| `qa-lab/rebuild-v260/full-audio-chart-audit-v260.json` | 20 canciones, 60 dificultades y métricas chart↔audio |
| `qa-lab/rebuild-v260/full-contract-asset-audit-v260.json` | JSON/XML/PNG, characters, stages, album, discovery y scripts |
| `qa-lab/rebuild-v260/full-mobile-loader-v260.json` | Carga Android headless 20/20 |
| `qa-lab/rebuild-v260/full-zip-hscript-audit-v260.json` | 20 ZIPs y colección |
| `qa-lab/rebuild-v260/full-qa-20x20-v260.json` | 400 revisiones QA |
| `qa-lab/rebuild-v260/full-sync-candidate-validation-v260.json` | Aislamiento de 20 candidatos |
| `qa-lab/rebuild-v260/full-audit-baseline/` | Hashes y ambiente reproducible |
| `qa-lab/rebuild-v260/visual-contact-sheet-v260.png` | Hoja visual de 60 assets |

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release oficial V-Slice 0.8.6"

[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — documentación oficial de modding"

[3]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
