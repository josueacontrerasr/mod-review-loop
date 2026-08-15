# Esperón FNF Mobile V-Slice 0.8.6 — V2.2.2

## Correcciones

- Reparación del contrato StageData: `directory: shared`, rutas relativas de props y mapa explícito de personajes.
- Reparación de CharacterData: `assetPath` relativo `characters/...`, compatible con el fallback de `Paths.getSparrowAtlas` en V-Slice 0.8.6.
- Rediseño de flechas y receptores con atlas compactos de 128×128, escalas móviles legibles y estilos únicos por canción.
- Regeneración de carátulas cuadradas y títulos Sparrow `idle0`/`switch0` para Freeplay.
- Promoción de charts ajustados por outliers contra onsets vocales independientes; audio, voces, BPM y `timeChanges` se conservaron.

## Validación

- Contrato runtime: 20/20 PASS.
- QA: 20 rondas × 20 mods = 400 revisiones PASS.
- ZIPs: 20 individuales + colección maestra, CRC PASS y SHA-256 incluido.

## Límite

Los resultados automáticos son evidencia de ingeniería, no sustituyen el Audio Sync Test del Chart Editor ni el playtest dentro de FNF Mobile V-Slice 0.8.6.
