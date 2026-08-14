# Reauditoría Wide Research de los mods FNF Mobile V-Slice 0.8.6

**Fecha de auditoría:** 14 de agosto de 2026  
**Versión revisada:** 2.1.2  
**Alcance:** 20 ZIPs individuales finales de Esperón  
**Resultado:** **PASS — 20/20**

## Conclusión

Se volvió a revisar en paralelo cada ZIP final contra la estructura de instalación y los contratos de datos usados por FNF Mobile V-Slice 0.8.6. Los 20 paquetes tienen una sola carpeta raíz, el manifiesto Polymod en la ubicación correcta, los documentos de instalación requeridos, los manifests de canción, los schemas esperados y los assets enlazados desde las rutas `shared:` correctas. No se encontraron rutas legacy bajo `images/characters`, `images/stages`, `images/notes` o `images/ui`.

La auditoría independiente utilizó ocho workers y terminó con **20 paquetes aprobados, 0 paquetes con error y 0 advertencias**. Además, la comparación byte a byte entre cada carpeta fuente y su ZIP final obtuvo **20/20 coincidencias**, por lo que no hay archivos omitidos, agregados inesperadamente o alterados durante el empaquetado.

| Área revisada | Resultado |
|---|---:|
| Integridad ZIP y rutas seguras | 20/20 PASS |
| Raíz única y `_polymod_meta.json` | 20/20 PASS |
| `api_version` 0.8.6 y `mod_version` 2.1.2 | 20/20 PASS |
| Metadata 2.2.4, chart 2.0.0 y manifest 1.0.0 | 20/20 PASS |
| `shared/images/` y rechazo de rutas legacy | 20/20 PASS |
| Personajes, stages y note styles | 20/20 PASS |
| PNG y atlas Sparrow XML | 20/20 PASS |
| Freeplay: álbum 1.0.3, portada 512×512 y título 512×128 | 20/20 PASS |
| HUD HScript, `Module` y `PlayState` imports | 20/20 PASS |
| `Inst.ogg` verificable con `ffprobe` | 20/20 PASS |
| Paridad fuente ↔ ZIP | 20/20 PASS |

## Comparación con referencias

La comparación estructural se repitió usando los tres ZIPs oficiales proporcionados como referencia: `MoonLightMobile.zip`, `fnf_el_chavo_del_8_v2__7638d.zip` y `vs_huggy_wuggy_c6a32.zip`. La comparación incluye 3 referencias, 20 ZIPs individuales y 1 ZIP de colección. El estado de los 20 mods instalables es **PASS**; el ZIP de colección se trata correctamente como contenedor de distribución y no como un mod Polymod independiente.

## Archivos de evidencia

El resultado reproducible se conserva en los siguientes archivos:

- `wide-reaudit-vslice086.json`: auditoría paralela detallada por ZIP, con SHA-256, raíz, canción, personajes, stage, note style y álbum.
- `cross-validation-vslice086.json`: ejecución paralela de los validadores de layout ZIP, comparación con referencias y validación estática de charts/UI.
- `source-zip-byte-parity.json`: comparación byte a byte entre fuentes y ZIPs finales.
- `../session-zip-structure/v2.1.2-install-layout.json`: validación de instalación del paquete.
- `../session-zip-structure/official-reference-comparison.json`: comparación con referencias oficiales.

## Limitación que permanece

Este resultado confirma la **ubicación y coherencia estática de los archivos**. No equivale a una certificación completa de ejecución en el motor oficial: `Audio Sync Test` dentro del Chart Editor y un playtest en FNF Mobile V-Slice 0.8.6 sobre Android o iOS siguen siendo necesarios para confirmar carga, rendimiento, input táctil, animaciones en ejecución y sincronía perceptual de las flechas con las voces. La evidencia de sincronía existente continúa clasificada como `PASS_EVIDENCE_ONLY`.

> No se modificaron BPM, offsets, notas, audio, personajes ni escenarios durante esta reauditoría. Solo se generó y publicó evidencia de verificación.

## Referencias

[1] [FunkinCrew — FNF v0.8.6 release](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)  
[2] [FunkinCrew — PolymodHandler.hx en v0.8.6](https://github.com/FunkinCrew/Funkin/blob/v0.8.6/source/funkin/modding/PolymodHandler.hx)  
[3] [Polymod — Creating Mods](https://polymod.io/docs/creating-mods/)
