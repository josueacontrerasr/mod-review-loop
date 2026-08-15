# Informe final V2.4.0 — Esperón FNF Mobile V-Slice 0.8.6

**Autor:** Manus AI  
**Rama:** `auto/vslice-sync-ui-v4`  
**Commit final:** `ce467834a77d014ceb98da56c2e1a16cbcab8bed`  
**Release:** [Esperón FNF Mobile V-Slice 0.8.6 V2.4.0](https://github.com/josueacontrerasr/mod-review-loop/releases/tag/esperon-vslice-086-v2.4.0)

## Resultado ejecutivo

Se corrigieron los 20 mods de Esperón para V-Slice Mobile 0.8.6. La carátula placeholder de Freeplay se originaba en una ruta incorrecta: los manifiestos usaban `freeplay/albums/`, mientras que el registro de álbumes de V-Slice resuelve los assets desde `freeplay/albumRoll/`. Se actualizaron los 20 JSON de álbum, se copiaron los PNG/XML al destino correcto y se conservaron los prefijos Sparrow `idle0000` y `switch0000`.

Se promovieron charts mixtos rítmico-vocales para fácil, normal y difícil. La base usa eventos del instrumental —percusión, bajo, melodía, energía y onsets— y conserva acentos vocales en entradas/frases relevantes. Se preservaron byte por byte `Inst.ogg`, las voces y `timeChanges` respecto de V2.3.0. Las dificultades mantienen velocidad y densidad crecientes: fácil `0.80`, normal `1.00` y difícil `1.22`.

## Gates completados

| Gate | Resultado | Evidencia |
|---|---:|---|
| Contrato runtime, 20 mods | **20/20 PASS** | `runtime-contract-v240.json` |
| Diagnóstico Freeplay y note styles | **20/20 PASS** | `diagnose-freeplay-notes-v240.json` |
| Promoción de charts mixtos | **20/20 PASS** | `chart-promotion-v240.json` |
| Audio/voces/timeChanges invariantes | **20/20 PASS** | `chart-promotion-v240.json` |
| Validación de ZIPs y colección | **20/20 + colección PASS** | `zip-validation-v240.json` |
| Revisión archivo por archivo | **20 rondas × 20 mods = 400 revisiones PASS** | `qa-20x20-v240.json` |
| Repetición del empaquetado | **Hashes idénticos en ejecuciones consecutivas** | `package-manifest-v240.json` |
| Workflow QA final | **success** | [Actions run 31863996504](https://github.com/josueacontrerasr/mod-review-loop/actions/runs/31863996504) |
| Artifact QA final | **disponible, no expirado** | `qa-lab-vslice-31863996504` |
| Workflow automático final | **success; sin commit artificial** | [Actions run 31864105993](https://github.com/josueacontrerasr/mod-review-loop/actions/runs/31864105993) |

## Entrega

La carpeta `Mods .zip terminados/` contiene únicamente los 20 ZIP individuales V2.4.0 y la colección maestra se publica como asset del Release. La colección maestra contiene los 20 ZIP individuales y `README-INSTALACION.txt`; los paquetes individuales no contienen `qa-lab`, reportes, artifacts ni evidencia de laboratorio.

El Release público contiene **21 assets**: 20 paquetes individuales y `Mod-Esperon-Coleccion-V2.4.0.zip`. El flujo automático mantiene el cron `*/10 * * * *`; el empaquetado ahora utiliza timestamps ZIP deterministas, por lo que una revisión sin cambios no crea nuevas confirmaciones binarias artificiales.

## Limitación de certificación móvil

La evidencia disponible demuestra que las rutas, contratos JSON, atlas/XML, carátulas, note styles, orden temporal de notas, audio y CRC resuelven de forma estática. No es correcto afirmar una certificación perceptual perfecta de flechas visibles sin ejecutar FNF Mobile 0.8.6 en un dispositivo Android/iOS y realizar el Audio Sync Test/playtest del motor. Tras instalar, se recomienda cerrar completamente FNF Mobile y abrirlo de nuevo para descartar caché de assets. Si las flechas siguieran invisibles en un teléfono, la siguiente prueba debe ser ese playtest nativo y no una nueva modificación automática del audio.

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release v0.8.6"
[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — Modding Documentation"
[3]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
[4]: https://github.com/josueacontrerasr/mod-review-loop/actions "GitHub Actions — mod-review-loop"
[5]: https://github.com/josueacontrerasr/mod-review-loop/releases "GitHub Releases — mod-review-loop"

Los contratos técnicos de V-Slice utilizados en esta iteración fueron contrastados con la documentación y el código oficial de la versión objetivo [1] [2], mientras que la estructura Polymod se mantuvo conforme a la guía de creación de mods [3].
