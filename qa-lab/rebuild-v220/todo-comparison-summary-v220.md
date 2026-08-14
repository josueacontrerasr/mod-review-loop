# Comparación Wide Research contra TODO.zip

## Hallazgo principal

`TODO.zip` no es un mod individual ni una estructura única: es un contenedor masivo de **1,409 entradas**, con una raíz `TODO/`, **13 subdirectorios directos**, **12 subdirectorios con `_polymod_meta.json` válido** y **1 candidato sin manifiesto** (`Xonada V-SLICE PORT By XxAxemxX`). Por tanto, no se debe copiar su raíz `TODO/` ni tratar todos sus contenidos como un solo mod instalable.

| Medición | Resultado |
|---|---:|
| Mods internos con manifiesto | 12 |
| Candidatos sin manifiesto | 1 |
| Versiones API observadas en TODO | 0.8.4 y 0.8.5 |
| Archivos TXT/MD internos detectados | 12 |
| ZIPs individuales V2.2.0 comparados | 20 |
| TXT/MD en la raíz ejecutable V2.2.0 | 0 |
| Reportes/evidencia en ZIPs V2.2.0 | 0 |

Los 12 TXT/MD de TODO.zip están anidados dentro de subcarpetas de algunos mods y funcionan como placeholders o documentación, por ejemplo `readme.txt`, `Your XML and PNG characters here.txt`, `Your freeplay icons here!.txt` y `README.md` de un mod utilitario. No constituyen una regla para introducir documentación en todos los ZIPs; de hecho, los 20 V2.2.0 son más estrictos y no llevan esos archivos dentro del árbol runtime.

## Patrón válido observado

Los mods internos funcionales de TODO usan una raíz individual con `_polymod_meta.json` y carpetas como `data/`, `images/`, `songs/`, `shared/` y, según el mod, `scripts/`, `shaders/`, `videos/`, `music/`, `sounds/`, `fonts/` o `_polymod_icon.png`. Los recursos opcionales aparecen solo cuando el mod realmente los necesita. También se observó un script `.hxc` en la raíz de `it's-been-so-long`, por lo que los validadores ahora permiten `_polymod_icon.png`, `_polymod_icon.astc` y scripts `.hxc` raíz, pero siguen rechazando TXT, reportes, logs, previews y carpetas QA en los paquetes individuales de Esperón.

Los mods de TODO declaran API 0.8.4/0.8.5, mientras que los de Esperón declaran 0.8.6 como objetivo. La diferencia de API es una diferencia de antigüedad, no un error de organización: los V2.2.0 ya están dirigidos a la versión más reciente indicada por el proyecto.

## Conclusión

La comparación masiva no encontró una discrepancia estructural que requiera modificar los 20 mods V2.2.0. Los paquetes actuales siguen un subconjunto runtime limpio del patrón observado en TODO.zip y cumplen una política más segura para distribución: una raíz por ZIP, manifiesto Polymod en esa raíz, datos/assets/audio en sus carpetas runtime y documentación/evidencia fuera del paquete instalable.

La auditoría es estática y de archivos. No sustituye instalar un ZIP individual en FNF Mobile V-Slice 0.8.6 y comprobar visualmente Freeplay, Story Mode y el inicio de una canción en un dispositivo real.
