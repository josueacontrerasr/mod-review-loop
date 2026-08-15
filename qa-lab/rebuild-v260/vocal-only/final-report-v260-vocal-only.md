# V2.6.0 Vocal-only — informe de migración de los 20 mods

## Resumen

Los 20 mods de Esperón fueron regenerados en la rama `auto/vocal-only-v260` para que las flechas se creen únicamente desde las fuentes `Voices-*.ogg`. El instrumental `Inst.ogg` no fue cargado por el generador vocal-only y no pudo producir ninguna nota. La producción se actualizó como **V2.6.0**, una mejora real sobre V2.5.1: se eliminó la política anterior que añadía acentos instrumentales de 5/10/15 %.

La modificación está limitada a los 20 charts y sus 20 manifests de versión. Los 40 archivos de audio, los 660 assets PNG/XML/HScript y los demás JSON runtime permanecieron intactos. La carpeta `Mods .zip terminados/` ahora contiene únicamente 20 ZIPs V2.6.0 y la colección V2.6.0.

## Resultado de los gates

| Gate | Resultado |
|---|---:|
| Fuentes vocales inventariadas | 20/20 PASS |
| Candidatos vocal-only | 20/20 PASS |
| Procedencia de notas | 20/20 canciones, 60/60 dificultades PASS |
| VAD independiente CPU | 20/20 canciones, 60/60 dificultades PASS |
| Input dinámico del generador | 20 llamadas a `Voices-*.ogg`, 0 llamadas a `Inst.ogg` |
| Staging contratos/assets | 20/20 PASS |
| Staging loader Android | 20/20 PASS |
| Staging QA | 400/400 PASS |
| ZIPs staging | 20/20 + colección PASS |
| Runtime V2.6.0 | 20/20 canciones, 60/60 dificultades PASS |
| ZIP gate V2.6.0 | 20/20 + 20 miembros de colección PASS |
| Hashes de audio | 40/40 sin cambios |

## Exclusión del instrumental

La comparación de procedencia confirma que el generador solo abrió 20 archivos `Voices-*.ogg`. La prueba dinámica registró cero entradas `Inst.ogg`. El código no contiene una ruta de selección rítmica o instrumental y cada nota candidata recibió un origen interno `voice` antes de limpiarse para el chart V-Slice final.

Los charts V2.5.1 de referencia contenían 30.077 notas en las 60 dificultades; 10.492 de esas notas, el 34,884 %, quedaban fuera de los segmentos vocales detectados por la nueva auditoría. Los candidatos V2.6.0 contienen 24.904 notas, una reducción global de 5.173 notas, equivalente al 17,20 %. La reducción no se rellenó con instrumental: las notas solo se conservaron cuando existía actividad en el stem vocal.

> Estos porcentajes describen la comparación automática contra segmentos vocales. No significan que cada nota antigua fuera necesariamente instrumental, porque un chart anterior también puede contener errores de timing o eventos vocales que el nuevo VAD no retuvo. La procedencia del nuevo chart sí es estrictamente vocal-only.

## Dificultades y contratos

Cada canción conserva `easy`, `normal` y `hard`. Las notas están ordenadas, usan lanes de jugador `d=0..3`, no tienen duplicados exactos y mantienen densidad creciente easy < normal < hard. Se conservaron los eventos y `timeChanges` del chart anterior; el reemplazo afecta la lista de notas y no el mapa temporal.

Los manifests ahora declaran `mod_version: 2.6.0` y `api_version: 0.8.6`. Metadata, charts, Freeplay, Storymode, personajes, stages, note styles, carátulas, HUD, XML, PNG, HScript y audio pasaron los validadores existentes y el loader headless.

## Empaquetado

La carpeta `Mods .zip terminados/` fue limpiada y reconstruida determinísticamente. Contiene los siguientes tipos de entrega:

| Entrega | Estado |
|---|---:|
| 20 ZIPs individuales `Mod-*-V2.6.0.zip` | PASS |
| `Mod-Esperon-Coleccion-V2.6.0.zip` | PASS |
| Reports o logs dentro de ZIPs | 0 |
| ZIPs V2.5.1 restantes en la carpeta | 0 |

## Alcance y límite de certificación

La sincronización ahora se rige por la señal vocal, no por la mezcla instrumental. El VAD independiente usa frames CPU de 20 ms, noise floor, umbral reproducible y hangover. Aun así, un stem vocal puede contener bleed instrumental o varias voces mezcladas. Por eso, los gates demuestran procedencia, cobertura y contratos, pero no identifican automáticamente sílaba, cantante o strumline por personaje.

La certificación perceptual final sigue requiriendo Audio Sync Test en Chart Editor y playtest en FNF Mobile V-Slice 0.8.6. El workflow remoto ejecutará los mismos gates y publicará artifacts; no hará commits ni Releases automáticos.

## Decisión

La promoción V2.6.0 queda justificada porque elimina de manera verificable la generación de notas instrumentales y mantiene todos los contratos de runtime. La rama se sometió al workflow remoto `qa-vocal-only-v260.yml` en el run `31898774095`, sobre el commit `91a32efc0b7fd2a0d6f19fd8c9f774186885303a`. El run terminó en `success` y publicó artifacts vocal-only. Con ese gate remoto aprobado, se puede publicar V2.6.0 con los 21 ZIPs.

## Evidencias principales

| Archivo | Contenido |
|---|---|
| `source-inventory-v260.json` | Hashes, codecs y duración de las 20 fuentes vocales |
| `candidate-summary-v260.json` | Candidatos vocal-only aislados |
| `provenance-gate-v260.json` | Procedencia de las 60 dificultades |
| `independent-vad-gate-v260.json` | Segundo método VAD CPU |
| `dynamic-input-probe-v260.json` | Cero lecturas de instrumental durante generación |
| `production-comparison-v260.json` | Comparación V2.5.1 frente a vocal-only |
| `runtime-v260.json` | Gate post-promoción de runtime |
| `zip-gate-v260.json` | Gate de 20 ZIPs y colección |
| `final-qa-20x20-v260.json` | 400 revisiones QA |
| `final-report-v260-vocal-only.md` | Este informe |

## Referencias

[1]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — Release oficial V-Slice 0.8.6"

[2]: https://funkincrew.github.io/funkin-modding-docs/ "FunkinCrew — documentación oficial de modding"

[3]: https://polymod.io/docs/creating-mods/ "Polymod — Creating Mods"
