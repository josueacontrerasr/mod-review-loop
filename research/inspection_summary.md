# Hallazgos iniciales confirmados

## Repositorio

Se confirmó el repositorio público `josueacontrerasr/mod-review-loop`, con rama por defecto `main`. En la raíz del repositorio aparecen veinte archivos de audio `.m4a`, un `README.md` y el PDF `Mod_«Daño_de_Esperón»__producción_ampliada_y_verif.pdf`.

## Audios detectados en la raíz

- `Esperón  Arcoloria (Letra).m4a`
- `Esperón  Cortamos y Volvemos (Letra).m4a`
- `Esperón  Daño _Letra_.m4a`
- `Esperón  Días Mágicos (Letra).m4a`
- `Esperón  Eclipsis (Letra).m4a`
- `Esperón  Fango.m4a`
- `Esperón  Luma (LETRA).m4a`
- `Esperón  Maratón de Películas.m4a`
- `Esperón  Me Voy A Morir Si No Me Besas Ahora Mismo (LETRA).m4a`
- `Esperón  Meteora (Letra).m4a`
- `Esperón  Mi Hogar (Letra).m4a`
- `Esperón  Nubia __ Letra.m4a`
- `Esperón  Nuestro Amor No es Normal (Audio).m4a`
- `Esperón  Peligrosa.m4a`
- `Esperón  Rompecabezas __ Letra.m4a`
- `Esperón  Solare (Letra).m4a`
- `Esperón  Tristella (LETRA).m4a`
- `Esperón  Tu Dealer de Nostalgia (LETRA).m4a`
- `Esperón  Un Poco Bien un Poco Mal _Letra_.m4a`
- `Esperón  Volver a Vernos.m4a`

## PDF de producción: puntos visibles confirmados

Las primeras páginas visibles del PDF establecen estos lineamientos:

| Tema | Hallazgo confirmado |
|---|---|
| Plataforma objetivo | FNF Mobile V-Slice **0.8.6** |
| Formato de entrega | ZIP con carpeta raíz por mod |
| Dificultades | Easy, Normal y Hard, compartiendo el mismo mapa temporal |
| Datos V-Slice | Metadata `2.2.4`, chart `2.0.0`, `api_version: "0.8.6"` |
| Personajes y escenario | Originales y optimizados para móvil |
| Scripts | Ninguno por defecto; priorizar datos y eventos de chart |
| Rondas de inspección | Cada 10 minutos hasta el **14 de agosto de 2026, 09:00 CST** |
| Política post-congelado | Las rondas periódicas solo inspeccionan y documentan; no regeneran chart ni reemplazan audio |
| Audio | Tratar el M4A como máster; analizar hash, duración, silencios, códec, BPM y stems si proceden |
| Sincronización | Reconstruir mapa temporal con el OGG final; anclajes revisados manualmente; tolerancia estática inicial de ±5 ms y deriva de hasta 10 ms por sección |
| Calidad del chart | Notas ordenadas, direcciones válidas, holds positivos, cobertura por dificultad y prueba estática PASS antes de avanzar |
| Distribución | Si falta autorización de redistribución, conservar como bloqueo de publicación |

## Enfoque paralelo del PDF

El PDF divide el trabajo en estos flujos coordinados:

| Flujo | Función |
|---|---|
| A | Contratos V-Slice, schemas, rutas, manifiesto y convenciones de IDs |
| B | Audio, hash, duración, BPM, compás, cambios de tempo y anclajes |
| C | Dirección visual, personajes, sprites/atlas, iconos y escenario |
| D | Chart y jugabilidad |
| E | Empaquetado, validación, créditos, licencia e instalación |
| F | Inspector nocturno con línea base SHA-256 e informes inmutables |

## Restricciones confirmadas para esta implementación

1. No se debe afirmar sincronización aprobada sin evidencia manual adicional del entorno oficial cuando el PDF lo exige.
2. El ZIP final debe crearse de forma serial y reproducible, evitando carreras de escritura.
3. La automatización periódica debe limitarse a revisiones y correcciones no musicales.
4. La identidad visual debe mantenerse original y optimizada para móvil.

## PDF de producción: páginas finales confirmadas

Las páginas restantes añaden estos requisitos explícitos:

| Fase | Requisito confirmado |
|---|---|
| Fase 3 — Personajes y escenario | Cada personaje debe tener al menos `idle`, `singLEFT`, `singDOWN`, `singUP` y `singRIGHT`, con prefijos comprobables en el atlas. El escenario debe usar un número moderado de props visibles, sin shaders, partículas ni llamadas por frame. Deben verificarse `assetPath`, renderizador, prefijos, offsets y `cameraOffsets`. |
| Fase 4 — Empaquetado | El ZIP de v1 debe tener una sola carpeta raíz del mod; el inventario SHA-256 del árbol y del ZIP pasa a ser línea base. Cualquier modificación posterior se informa, no se remedia automáticamente. |
| Fase 5 — Rondas cada 10 minutos | La primera ronda empieza al siguiente límite de diez minutos tras congelar el ZIP. Las rondas se serializan; si una sigue activa a las 09:00 CST del 14 de agosto de 2026, termina y luego se detiene el programador. |
| Bloques de ronda | Inmutabilidad, archivo/estructura, JSON/enlaces, audio, chart, visual/móvil y distribución. |
| Salida de rondas | Informe solo de lectura, con hallazgos clasificados como bloqueante, importante, informativo o pendiente de playtest móvil. |
| Fase 6 — Cierre | Entregar ZIP congelado, informe consolidado, evidencia de sincronización, matriz de pruebas móviles y registro de acciones propuestas no ejecutadas. |
| Criterios de aceptación | Manifiesto, metadata, chart y JSON válidos; rutas e IDs resueltos; tres charts con claves y velocidades; OGG final trazable; ZIP sin carpeta extra; anclajes sin deriva no explicada. El Audio Sync Test y el playtest móvil deben declararse pendientes si no se realizaron. |
| Riesgos abiertos | La autorización de distribución de la canción sigue pendiente; la calidad de stems depende del análisis; el diseño exacto puede resolverse como arte original; la ventana horaria de congelamiento limita cuántas rondas caben antes del corte. |

## Implicación inmediata para la implementación

1. Los mods nuevos deben generarse con atlas válidos y cinco animaciones mínimas por personaje.
2. El workflow periódico debe limitarse a revisión y corrección no musical, nunca a cambios automáticos de timing o audio.
3. Toda entrega debe distinguir entre validación estructural aprobada y pruebas manuales pendientes.
4. Debe preservarse una línea base por ZIP para futuras rondas de inspección y comparación de hashes.
