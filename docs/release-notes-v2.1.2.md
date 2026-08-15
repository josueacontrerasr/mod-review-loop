# Esperón V-Slice 0.8.6 — v2.1.2

## Corrección principal

Se reorganizaron los 20 mods para que los assets declarados con `shared:` estén físicamente bajo `shared/images/`, conforme al layout de los mods V-Slice oficiales de referencia. Antes, los JSON de personajes, escenarios y note styles apuntaban a `shared:characters/...`, `shared:stages/...`, `shared:notes/...` y `shared:ui/...`, pero los PNG/XML estaban bajo `images/`, por lo que el motor no podía resolverlos.

También se añadió `data/songs/<song-id>/manifest.json` a cada canción con `version: 1.0.0` y su `songId`, siguiendo el patrón observado en los mods oficiales adjuntos.

## Alcance

La reparación cubre los 20 mods: Arcoloria, Cortamos y Volvemos, Daño, Días Mágicos, Eclipsis, Fango, Luma, Maratón de Películas, Me Voy a Morir Si No Me Besas Ahora Mismo, Meteora, Mi Hogar, Nubia, Nuestro Amor No Es Normal, Peligrosa, Rompecabezas, Solare, Tristella, Tú Dealer de Nostalgia, Un Poco Bien Un Poco Mal y Volver a Vernos.

No se modificaron los hashes de `Inst.ogg`, charts, metadata musical, BPM, offsets ni `timeChanges`. Los ZIP v2.1.1 previos se conservaron en `dist/historico/asset-layout-pre-fix-v2.1.1/`.

## Validación

- 20/20 ZIP individuales con una única carpeta raíz.
- `_polymod_meta.json` resoluble dentro de la carpeta del mod.
- 20/20 manifests de canción presentes y coherentes.
- 20/20 resoluciones de personajes, stages y note styles bajo `shared/images`.
- 20/20 auditoría HScript con import oficial de `Module`.
- 20 rondas QA sobre 20 mods: 400 revisiones, 0 errores y 0 advertencias.
- Colección completa v2.1.2 reconstruida y verificada.

La validación estática y la inspección de ZIP no sustituyen una instalación real en FNF Mobile V-Slice 0.8.6. La prueba final en el dispositivo debe extraer un ZIP v2.1.2, colocar la carpeta raíz en `mods/`, reiniciar el juego y confirmar que aparece en el Mod Menu.
