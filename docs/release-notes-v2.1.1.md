# Esperón FNF Mobile V-Slice 0.8.6 — v2.1.1

Esta versión corrige un error interno que impedía cargar los HUD HScript de los mods. Los veinte scripts declaraban `extends Module`, pero no importaban la clase oficial `funkin.modding.module.Module`; además, la referencia a `PlayState` tampoco estaba declarada de forma explícita en los archivos empaquetados.

## Corrección aplicada

Cada uno de los 20 HUD ahora incluye:

```haxe
import funkin.modding.module.Module;
import funkin.play.PlayState;
```

La clase base y el callback `onCountdownStart` fueron contrastados con el código oficial de FNF v0.8.6. No se modificaron audio, voces, charts, BPM, offsets, `timeChanges`, personajes, escenarios ni sincronía musical.

## Verificación

- 20/20 ZIP con imports HScript corregidos.
- 20/20 auditoría de paquetes y colección PASS.
- 20 rondas × 20 mods = 400 revisiones QA.
- 0 errores y 0 advertencias estructurales.
- 20/20 verificación estática V-Slice 0.8.6 PASS.
- Los ZIP v2.1.0 anteriores se conservaron en `dist/historico/hscript-pre-fix-v2.1.0/`.

La apariencia del HUD y la ausencia del diálogo de parseo deben confirmarse abriendo un ZIP v2.1.1 en FNF Mobile V-Slice 0.8.6. El análisis estático no reemplaza la prueba de ejecución en Android/iOS ni el Audio Sync Test.
