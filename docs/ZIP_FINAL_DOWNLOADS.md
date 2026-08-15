# Descarga de mods finales

La carpeta **`Mods .zip terminados/`** es la única carpeta del repositorio destinada a descargas. Contiene exclusivamente los paquetes ZIP finales vigentes: veinte mods individuales y una colección completa.

Los nombres siguen la forma `Mod-<Cancion>-V<version>.zip`. Para instalar un mod, descarga el ZIP de la canción deseada, extráelo y coloca directamente la carpeta raíz del mod en la carpeta `mods` de FNF Mobile V-Slice 0.8.6. No dejes el ZIP sin extraer ni añadas una carpeta intermedia.

Las carpetas `dist/historico/`, `qa-lab/`, `sync-candidates/`, `reports/`, `artifacts/` y `tools/` no son carpetas de descarga. Allí se conservan versiones antiguas, hashes, resultados de QA, evidencia de sincronía, scripts y registros reproducibles.

Cuando un mod se modifique y supere las validaciones, su ZIP anterior se retira de `Mods .zip terminados/`, se conserva en `dist/historico/` y se reemplaza por el ZIP de la nueva versión. Si no hay un cambio válido, el ZIP vigente y su versión permanecen sin cambios.

La organización de archivos no certifica por sí sola la sincronía perfecta. La confirmación final de audio requiere Audio Sync Test en Chart Editor y playtest en FNF Mobile V-Slice 0.8.6.
