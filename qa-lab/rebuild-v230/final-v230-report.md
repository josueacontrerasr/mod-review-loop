# Informe final V2.3.0 — Mods Esperón para FNF Mobile V-Slice 0.8.6

**Autor:** Manus AI  
**Repositorio:** `josueacontrerasr/mod-review-loop`  
**Rama de trabajo:** `auto/vslice-sync-ui-v3`  
**Objetivo:** corregir los 20 mods de Esperón, sincronizar sus flechas con las voces y renovar sus assets visuales sin cambiar el audio distribuido.

## Resumen ejecutivo

La versión V2.3.0 modifica los 20 mods y promueve 60 charts —easy, normal y hard— generados desde evidencia de actividad vocal. La sincronía se evaluó con VAD CPU, dos perfiles generadores de ataques, un juez vocal independiente para reparación y un cuarto método espectral para verificación. El gate exige que cada nota quede respaldada por al menos dos señales independientes dentro de 80 ms; las 60 dificultades pasan el gate multimétodo. El audio, BPM, `timeChanges`, `Inst.ogg` y voces se conservaron mediante hashes y comprobación de promoción.

El contrato de V-Slice 0.8.6 pasa para 20/20 mods. Los 40 personajes tienen atlas Sparrow de 18 frames, los 20 stages tienen assets visibles y mapa explícito de `bf`, `dad` y `gf`, los 20 note styles tienen XML y PNG, y las 20 carátulas tienen arte 512×512, título 512×128 y frames `idle0000`/`switch0000`. Los ZIPs individuales y la colección pasan la auditoría de instalación y CRC. La certificación final en un APK móvil sigue siendo necesaria para medir la latencia del teléfono con Audio Sync Test y playtest real.

## Resultados verificables

| Área | Resultado | Evidencia |
|---|---:|---|
| Canciones procesadas | **20/20** | `sync-pipeline-v230.json` |
| Dificultades sincronizadas | **60/60** | `sync-pipeline-v230.json` |
| Contrato runtime V-Slice | **20/20 PASS** | `runtime-contract-v230.json` |
| QA exhaustivo | **20 rondas × 20 mods = 400 revisiones PASS** | `qa-20x20-v230.json` |
| ZIPs individuales | **20/20 PASS** | `zip-validation-v230.json` |
| Colección maestra | **20 ZIPs, CRC PASS** | `collection-v230.json` |
| Paquetes de entrega | **20 individuales + colección** | `package-manifest-v230.json` |
| Audio modificado durante promoción | **No** | `chart-promotion-v230.json` |
| `timeChanges` modificados durante promoción | **No** | `chart-promotion-v230.json` |

## Procedimiento de sincronía

Primero se congeló el audio de cada canción y se conservaron sus archivos finales. El primer detector usa ventanas de 20 ms a 16 kHz, clasificación por energía y calibración del ruido; esto sigue la recomendación de VAD CPU de utilizar ventanas de 20 ms, estimar el piso de ruido y evitar segmentos demasiado cortos.[1] En lugar de tratar un único detector como verdad, el pipeline fusiona dos perfiles de ataques para proponer eventos vocales.

Después se genera cada dificultad desde la misma base temporal. Easy reduce la densidad y usa `scrollSpeed` 0.8; normal usa `scrollSpeed` 1.0; hard aumenta la densidad y usa `scrollSpeed` 1.22. El timestamp de cada evento se conserva: cambiar la velocidad visual no desplaza las flechas respecto al audio.

La segunda etapa usa un juez vocal independiente para corregir outliers sin volver a evaluar contra la misma lista usada para generar. La etapa final incorpora un método espectral de resolución temporal distinta y una auditoría de consenso de cuatro señales. Esta separación evita un falso PASS circular: la nota debe quedar respaldada por métodos que no comparten exactamente el mismo conjunto de eventos.

> El resultado `PASS` significa que las notas están temporalmente respaldadas por el consenso de señales de audio dentro de la tolerancia estadística definida. No significa que se haya medido la latencia específica de cada dispositivo ni sustituye el Audio Sync Test nativo.

## Corrección de la estructura V-Slice

Se conservaron los schemas de metadata `2.2.4` y chart `2.0.0`, y se declaró `api_version: "0.8.6"`, coherente con la regla de compatibilidad de la versión objetivo.[2] Los stages usan `directory: "shared"`, rutas relativas `stages/<id>` y un mapa explícito de personajes. Los personajes usan `characters/<id>` con atlas Sparrow y prefijos que coinciden con sus animaciones. Los note styles se mantienen en `shared/images/notes/`, mientras que el arte de Freeplay permanece en `images/freeplay/albums/`.

La auditoría verifica JSON, XML, PNG, OGG, orden de notas, duplicados, dominios de dirección, tres dificultades, escalado de velocidad, presencia de audio, resolución de atlas y frames de álbum. También prueba que los ZIPs tengan una sola raíz instalable y que no incluyan `qa-lab`, `reports`, `artifacts`, `sync-candidates` ni archivos de evidencia.

## Rediseño visual

Cada canción recibió una paleta y un motivo derivados de la investigación visual de videos públicos y de su nombre, sin copiar miniaturas ni introducir texto generado dentro de las ilustraciones. Las flechas usan cuatro direcciones geométricas legibles, contorno oscuro, núcleo secundario y variación de motivo por canción. Los 40 personajes tienen dos identidades por canción —jugador y rival— con idle, cuatro poses de canto y cuatro poses hold.

Quince carátulas fueron generadas con el estilo visual de referencia V2.3.0. Las cinco restantes —Solare, Tristella, Tu Dealer de Nostalgia, Un Poco Bien Un Poco Mal y Volver a Vernos— se produjeron con un fallback geométrico determinista porque se alcanzó el límite diario del generador visual del plan gratuito. Estas cinco no quedaron sin carátula: sus assets son PNG válidos de 512×512, con título Sparrow y stage derivado de la misma paleta.

## Empaquetado y publicación

La carpeta `Mods .zip terminados/` contiene exclusivamente los ZIPs finales V2.3.0: 20 paquetes individuales y una colección maestra. Cada ZIP individual contiene la raíz del mod y sus recursos runtime; los informes, logs, hojas de contacto y hashes quedan fuera del ZIP. La colección contiene un README, un manifiesto de hashes y los 20 ZIPs.

## Limitaciones y siguiente prueba

La prueba pendiente es instalar un ZIP V2.3.0 en FNF Mobile V-Slice 0.8.6, cerrar y abrir el juego para limpiar caché, ejecutar Audio Sync Test y jugar al menos el inicio, una sección vocal central, una sección densa hard y el final de cada canción. Si existe un offset constante, debe calibrarse en el dispositivo; no se debe desplazar el chart distribuido para compensar la latencia personal. Si existe deriva progresiva, debe reportarse junto con canción, dificultad, segundo aproximado y captura del Chart Editor.

## Referencias

[1] [Skill VAD CPU — ventanas, piso de ruido y métricas](file:///home/ubuntu/skills/audio-vad-cpu/SKILL.md)

[2] [FunkinCrew — notas oficiales de FNF v0.8.6](https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6)

[3] [FunkinCrew — Chart Editor](https://funkincrew-funkin-59.mintlify.app/tools/chart-editor)

[4] [librosa — detección de onsets](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_detect.html)

[5] [Polymod — Creating Mods](https://polymod.io/docs/creating-mods/)

[6] [Canal oficial de Esperón en YouTube](https://www.youtube.com/@Esperon_mx/videos)

[7] [Referencia visual Arcoloria](https://www.youtube.com/watch?v=D8xYouxhoK4)

[8] [Referencia visual Solare](https://www.youtube.com/watch?v=jY3j6tvPXFE)

[9] [Referencia visual Nuestro Amor No Es Normal](https://www.youtube.com/watch?v=B0anw7LDcDU)

[10] [Referencia visual Cortamos y Volvemos](https://www.youtube.com/watch?v=vXjIguLTV6o)
