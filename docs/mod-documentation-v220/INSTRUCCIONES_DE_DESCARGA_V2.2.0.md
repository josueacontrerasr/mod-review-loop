# Descarga e instalación correcta — V2.2.0

## No usar

No instalar archivos de `dist/historico/`, especialmente `hscript-pre-fix-v2.1.0/Mod-Solare-V2.1.0.zip`. Esa versión contiene los seis archivos auxiliares que aparecen en la captura: `CREDITS.txt`, `LICENSE.txt`, `INSTALACION_MOVIL.txt`, `audio-evidence.json`, `sync-report.json` y `visual-v2-integrity.json`.

Tampoco se debe instalar `Mod-Esperon-Coleccion-V2.2.0.zip` como si fuera un mod individual. La colección es únicamente un contenedor de distribución que incluye los 20 ZIP individuales.

## Usar

La fuente exclusiva de paquetes instalables es:

```text
Mods .zip terminados/Mod-<Cancion>-V2.2.0.zip
```

Para Solare, el archivo correcto es:

```text
Mods .zip terminados/Mod-Solare-V2.2.0.zip
```

SHA-256 de Solare V2.2.0:

```text
42c48ad82d4e947ef95da3f677101e3b0c8ef1be44fc2f7610ac78a95f820350
```

Un ZIP individual correcto contiene una sola raíz:

```text
esperon-dano-solare/
└── _polymod_meta.json
```

El resto del contenido runtime está dentro de `data/`, `images/`, `shared/`, `songs/` y `scripts/` cuando corresponde. No contiene reportes, logs ni archivos TXT de trabajo.

## Android/iOS

Extraer el ZIP individual y colocar la carpeta `esperon-dano-solare/` directamente dentro de la carpeta `mods` de FNF Mobile. No dejar el ZIP sin extraer, no crear una carpeta intermedia y no colocar la carpeta de colección como si fuera un mod. Después de copiarlo, cerrar FNF por completo y volver a abrirlo para que se reconstruya el registro de mods.

Si el ZIP V2.2.0 con el SHA anterior no aparece tras una instalación limpia y reinicio, el problema ya no es la cantidad de archivos auxiliares: habrá que comprobar la ruta de `mods`, permisos, versión instalada de FNF Mobile y caché del juego.
