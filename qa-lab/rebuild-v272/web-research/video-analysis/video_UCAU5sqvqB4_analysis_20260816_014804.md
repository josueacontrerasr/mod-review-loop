Este es un análisis técnico detallado del gameplay del chart vocal "High Beta Vocal Cover" (V-Slice style).

### (A) Sincronización: ¿Voz o Instrumental?
El chart está diseñado **estrictamente sobre los ataques de la voz**.
*   **Observación:** En fragmentos como **0:08 - 0:15** (Mommy Mearest) y **0:18 - 0:25** (Boyfriend), las notas ignoran los bombos y cajas del instrumental para centrarse exclusivamente en el fraseo melódico.
*   **Inferencia:** Incluso en momentos de silencio instrumental relativo, si hay un "glitch" o respiración vocalizada, el chart coloca una nota (ej. **0:42**).

### (B) Separación de sílabas cercanas
Se observan notas individuales para articulaciones muy rápidas:
*   **0:10 - 0:12:** Cuatro notas rápidas (Izquierda, Abajo, Derecha, Arriba) que corresponden a cuatro sílabas distintas de la voz femenina.
*   **0:42 - 0:44:** BF ejecuta una ráfaga de "beeps" cortos. Cada uno está mapeado como una nota individual (Down-Down, Up-Up), permitiendo sentir la percusión de la voz.
*   **1:15 - 1:17:** Una secuencia de notas en zigzag que separa claramente los cambios de tono en una vocal extendida que suena casi como un trino.

### (C) Uso de Hold Notes (Sustituciones)
Los holds se utilizan para representar el legato y la extensión de las vocales.
*   **0:13:** Un hold largo en la lane "Abajo". Inicia exactamente con el ataque de la vocal y termina cuando la energía del audio decae, justo antes del siguiente ataque.
*   **0:45 - 0:48:** Dos holds consecutivos (Abajo y luego Arriba). El final del primero coincide casi perfectamente con el inicio del segundo, reflejando una transición vocal sin pausa (legato).
*   **1:56:** Hold final que se extiende ligeramente más allá de la percepción auditiva clara, probablemente para dar un cierre visual al patrón.

### (D) Ráfagas densas y distribución
*   **Timestamp:** **0:58 - 1:05** y **1:39 - 1:48**.
*   **Densidad:** Aproximadamente **6 a 9 notas por segundo (NPS)** en los picos más altos.
*   **Distribución:** Las ráfagas no se quedan en una sola lane (evitando *jacks* excesivos), sino que fluyen entre las 4 lanes para imitar el movimiento de la escala melódica de la voz. Esto es típico de los charts V-Slice para mantener el flujo.

### (E) Interpretación de notas (Fusiones y Desapariciones)
*   **Fusión:** En **1:20**, un vibrato rápido en la voz se interpreta como un solo hold largo en lugar de múltiples notas cortas. Esto simplifica la lectura sin perder la esencia del ritmo.
*   **Notas "fantasma":** En **1:40**, hay sonidos glitch muy sutiles en el audio que *tienen* nota asignada. Para un jugador casual, esto podría parecer que la nota no tiene respaldo sonoro, pero al analizar el canal vocal, el ataque existe.

### (F) Patrones para depuración (Contexto Esperón)
Para mejorar o depurar charts vocales similares, se sugieren estos patrones observados:
1.  **Consistencia Pitch-Lane:** Las notas más agudas tienden a estar en "Arriba" y "Derecha", mientras que las graves en "Izquierda" y "Abajo". Si una nota aguda cae en "Abajo", puede causar disonancia cognitiva en el jugador.
2.  **Mapeo de Glitches:** El video muestra que los artefactos de la voz (sonidos robóticos) se mapean como notas cortas. Si el chart de Esperón se siente "vacío", es probable que esté ignorando estos micro-sonidos.
3.  **Final de Hold:** Asegurarse de que el hold termine un *frame* antes de la siguiente nota para evitar que el motor del juego registre un "miss" por soltar tarde (especialmente en motores antiguos).

**Nota técnica:** Debido a la mezcla de audio (instrumental + voz), en las secciones de **1:00 a 1:10**, la precisión del inicio de las notas respecto a la voz es difícil de verificar al 100% sin los archivos *stems* por separado, aunque visualmente el *scroll* parece perfectamente alineado con los transitorios de la voz.