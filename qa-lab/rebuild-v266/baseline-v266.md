# Baseline V2.6.6

Fecha de congelación: 2026-08-15 (zona del entorno)

| Campo | Valor |
|---|---|
| Rama de trabajo | `auto/fnf-vocal-lane-album-v266` |
| Rama base | `main` |
| Commit base | `ace2877f612c507bf032046446e50da45f84e90c` |
| Release base | `esperon-vslice-086-v2.6.5` |
| Mods | 21 |
| ZIPs existentes en entrega | 22 |
| Versión objetivo | FNF Mobile V-Slice 0.8.6 |
| Cambios de producción al congelar | 0 |

## Canciones auditadas

`arcoloria`, `cortamos-y-volvemos`, `dano`, `dias-magicos`, `eclipsis`, `fango`, `luma`, `maraton-de-peliculas`, `me-voy-a-morir-si-no-me-besas-ahora-mismo`, `meteora`, `mi-hogar`, `nubia`, `nuestro-amor-no-es-normal`, `peligrosa`, `rompecabezas`, `si-te-vas`, `solare`, `tristella`, `tu-dealer-de-nostalgia`, `un-poco-bien-un-poco-mal` y `volver-a-vernos`.

## Regla de ownership a validar

El runtime oficial V-Slice 0.8.6 (`SongData.hx`) define `d=0..3` como la strumline del jugador y `d=4..7` como la siguiente strumline del oponente. V2.6.6 debe comprobar esta regla contra el chart y contra el comportamiento observado, y no reutilizar el gate invertido de V2.6.5.
