## Esperón V2.6.7 — FNF Mobile V-Slice 0.8.6

Esta versión rehace los charts vocales de los 21 mods de Esperón a partir de una auditoría Wide Research paralela sobre los stems `Voices-*.ogg` exactos incluidos en el release V2.6.6.

### Cambios principales

Los ataques se retimaron con RMS/VAD y se auditaron por secciones de inicio, centro y final. La línea base V2.6.6 presentaba una mediana de desfase aproximada de 90–100 ms frente al onset acústico calculado; los candidatos V2.7 se anclan al onset revisado sin alterar el instrumental ni introducir latencia del dispositivo dentro del chart.

Los finales vocales se reconstruyeron con evidencia de energía, margen de liberación y límite del siguiente ataque. Se añadieron holds para vocales largas y palabras cortas prolongadas cuando la energía vocal lo respalda. El límite por sílaba es 1800 ms y las dificultades comparten los mismos anclajes vocales.

El mapeo primario conserva A→d=0 izquierda, E→d=2 arriba, I→d=3 derecha y O/U→d=1 abajo. En rachas repetitivas de una misma vocal se aplica un balanceo determinista después del primer ataque, sin cambiar timestamps ni convertir el instrumental en notas. Las Hard subdivisions heredan dirección e intervalo vocal del ataque padre.

### Evidencia

Los candidatos pasan 21/21. PlayState pasa 63/63. Producción vocal pasa 21/21 con 0 notas fuera de intervalo, 0 desalineadas y 0 holds inválidos. Contratos/assets pasan 21/21; Freeplay/AlbumRoll pasa 21/21; el loader móvil headless pasa 21/21; el ZIP gate pasa 21/21 más el paquete completo; y QA pasa 20 rondas × 21 mods = 420/420 con CRC PASS.

El release contiene 22 ZIPs: `Esperon-Completo.zip` y los 21 ZIP individuales V2.6.7. Los ZIP runtime no incluyen reportes, evidencia, Markdown ni archivos TXT auxiliares.

### Límite de verificación

Los análisis estáticos, RMS/VAD, loader headless y GitHub Actions no sustituyen el `Audio Sync Test` ni el playtest táctil dentro del runtime oficial FNF Mobile 0.8.6. La rama conserva esa limitación documentada y no afirma una prueba móvil física inexistente. El caso `me-voy-a-morir-si-no-me-besas-ahora-mismo` conserva una advertencia de hold ratio alto para revisión humana.
