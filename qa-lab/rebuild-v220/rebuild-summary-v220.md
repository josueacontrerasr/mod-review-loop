# Reconstrucción estructural V2.2.0 — FNF Mobile V-Slice 0.8.6

## Resultado

La auditoría Wide Research confirmó que los tres ZIP de referencia proporcionados por el usuario no colocan archivos TXT de créditos, licencia o instalación dentro de la raíz ejecutable del mod. Los 20 paquetes anteriores sí incluían `CREDITS.txt`, `LICENSE.txt`, `INSTALACION_MOVIL.txt`, `audio-evidence.json`, `sync-report.json` y `visual-v2-integrity.json` dentro de cada mod. Aunque varios de esos archivos son documentación o evidencia útil, no pertenecen al árbol runtime mínimo que se comparó con las referencias.

La reconstrucción V2.2.0 retiró esos archivos de los 20 árboles ejecutables y conservó copias de documentación en `docs/mod-documentation-v220/<song>/` y evidencia en `qa-lab/rebuild-v220/evidence/<song>/`. El ZIP individual contiene ahora únicamente `_polymod_meta.json` como archivo raíz y las carpetas runtime `data/`, `images/`, `scripts/`, `shared/` y `songs/`, siguiendo el patrón de los ejemplos de referencia. La colección se valida por separado como contenedor de distribución.

## Comparación de paquetes

| Comprobación | Resultado |
|---|---:|
| ZIP de referencia inspeccionados | 3 |
| ZIP individuales V2.2.0 | 20 |
| ZIP de colección V2.2.0 | 1 |
| ZIP individuales con TXT runtime | 0/20 |
| ZIP individuales con reportes/evidencia runtime | 0/20 |
| Raíz única y CRC válido | 20/20 |
| Layout V-Slice y enlaces Freeplay/Story Mode | 20/20 |
| Paridad fuente ↔ ZIP | 20/20 |
| Laboratorio QA | 20 rondas × 20 mods = 400 revisiones, 0 errores, 0 warnings |

## Contenido preservado

No se modificaron `Inst.ogg`, charts, metadata temporal, BPM, offsets ni notas durante la limpieza. La paridad byte a byte entre cada fuente y su ZIP V2.2.0 pasó para los 20 mods. Los niveles visibles, `songs[]`, `playData.album`, portadas, títulos, personajes, escenarios, note styles y HUD permanecen dentro de las rutas runtime necesarias.

## Prevención de regresiones

El validador de instalación V2.2.0 rechaza TXT, reportes, logs, previews, `qa-lab`, `artifacts` y `reports` dentro de un ZIP individual. El laboratorio QA también comprueba esa higiene en cada ronda. El empaquetador, Auto evolución, pipeline base, validadores visuales y lectores de evidencia fueron actualizados para guardar documentación y reportes fuera del mod.

## Limitación de ejecución

Esta auditoría confirma estructura, rutas, contratos, extracción, descubrimiento estático y paridad. No sustituye abrir cada paquete en FNF Mobile V-Slice 0.8.6 en Android/iOS. La prueba móvil y `Audio Sync Test` deben seguir registrándose por separado; la reorganización no se usa como evidencia de sincronía vocal perfecta.

## Referencias

[1] [FunkinCrew — FNF v0.8.6](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)  
[2] [FunkinCrew — INSTALLING_MODS.md](https://github.com/FunkinCrew/Funkin/blob/main/docs/INSTALLING_MODS.md)  
[3] ZIPs de referencia adjuntos por el usuario: `v-slice_yo_la_conoci_en_un_taxi.zip`, `tse_disable_shader_v25.zip` e `its-been-so-long.zip`.
