# Hallazgos visuales iniciales para V2.3.0

## Fuentes observadas

| Canción | Fuente | Evidencia pública observada |
|---|---|---|
| Arcoloria | [video oficial de Esperón](https://www.youtube.com/watch?v=D8xYouxhoK4) | Canal `Esperón`, aproximadamente 416 mil suscriptores; la página muestra cerca de 5.6 millones de vistas y enlaces del canal a Luma, Tristella y Eclipsis. En el panel de recomendaciones se observan miniaturas con predominio de tonos oscuros y cálidos; se usará únicamente como referencia de atmósfera y contraste, no como copia de arte. |
| Solare | [video oficial de Esperón](https://www.youtube.com/watch?v=jY3j6tvPXFE) | Canal `Esperón`, aproximadamente 416 mil suscriptores; la página muestra cerca de 14 millones de vistas. La descripción y comentarios del propio canal mencionan la experiencia de grabación y un símbolo de sol; la miniatura recomendada asociada a Solare utiliza una atmósfera cálida, naranja/amarilla y oscura. |

## Decisiones visuales derivadas

Las carátulas V2.3.0 se crearán como arte original inspirado en **paleta, contraste, atmósfera y nombre**, no como extracción o redistribución de las portadas de YouTube. Arcoloria recibirá una combinación oscura con acentos cálidos y un motivo de arco/cromatismo; Solare recibirá una paleta solar de naranja, oro y sombra profunda con un motivo radial. La misma regla se aplicará a las otras 18 canciones después de abrir sus fuentes oficiales o alternativas públicas.

## Limitación de la observación

YouTube mostró una pantalla de autenticación dentro del reproductor en el entorno de investigación; por ello no se tratará esa vista como evidencia del video completo. Las miniaturas, título, canal, descripción y comentarios públicos se conservarán como referencia contextual. Cuando sea necesario, se analizarán URLs públicas con análisis multimodal o se usará la miniatura pública del video como referencia de color. No se afirma que una miniatura revele toda la dirección artística del video.

## Métodos documentados para sincronía

La documentación oficial del Chart Editor describe `Instrumental Offset`, `Vocal Offset` y `Audio Sync Test` como controles separados; por tanto, el plan no mezclará la latencia personal del dispositivo con los timestamps del chart. La misma documentación expone cambios de BPM y de compás como funciones del editor, por lo que una deriva al final de una canción se tratará como un problema del mapa temporal, no como una razón para desplazar notas individualmente. Fuente: [Chart Editor de Friday Night Funkin'](https://funkincrew-funkin-59.mintlify.app/tools/chart-editor).

La documentación de `librosa.onset_detect` define la salida como eventos estimados obtenidos al seleccionar picos en una envolvente de fuerza de onset. También documenta `backtrack` como el desplazamiento al mínimo de energía anterior, útil para segmentación, y permite devolver unidades temporales. Por eso V2.3.0 usará `librosa` como referencia independiente y no como única verdad para convertir cada pico en una flecha. Fuente: [librosa.onset.onset_detect](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_detect.html).

## Consecuencia para el pipeline

La decisión técnica es combinar VAD vocal por energía/segmentos, onsets espectrales con más de una configuración, BPM/timeChanges y revisión multimodal. La promoción solo ocurrirá cuando los métodos coincidan dentro de las puertas métricas registradas; los casos ambiguos se marcarán como revisión y no como sincronía perfecta automática.

## Inventario del canal oficial

La pestaña de videos del canal oficial `@Esperon_mx` muestra aproximadamente 416 mil suscriptores y 83 videos. La página permitió localizar fuentes directas para varias canciones y miniaturas públicas con IDs reproducibles:

| Canción | URL oficial localizada |
|---|---|
| Eclipsis | https://www.youtube.com/watch?v=6MTptExfQNk |
| Meteora | https://www.youtube.com/watch?v=-0lfqKeDyl0 |
| Arcoloria | https://www.youtube.com/watch?v=D8xYouxhoK4 |
| Solare | https://www.youtube.com/watch?v=jY3j6tvPXFE |
| Luma | https://www.youtube.com/watch?v=L2EmaRBEOx0 |
| Días Mágicos | https://www.youtube.com/watch?v=K65c4-MenIY |
| Me Voy A Morir Si No Me Besas Ahora Mismo | https://www.youtube.com/watch?v=JRysCcNm0Es |
| Tristella | https://www.youtube.com/watch?v=hQsbS3SMGsg |
| Maratón de Películas | https://www.youtube.com/watch?v=Ltnh5_ENUj8 |
| Peligrosa | https://www.youtube.com/watch?v=d7jX66W-U98 |
| Rompecabezas | https://www.youtube.com/watch?v=p3lnWU23iaU y https://www.youtube.com/watch?v=LdZL3j7uHVA |
| Nubia | https://www.youtube.com/watch?v=QPt3bcvn1XA |
| Mi Hogar | https://www.youtube.com/watch?v=jsgxrw4PnNQ |
| Daño | https://www.youtube.com/watch?v=jf0I4ZfkJKI |

La página también expone miniaturas públicas `i.ytimg.com` para inspección de color. En la vista del canal se observaron composiciones distintas: Eclipsis usa contraste verde/negro con tipografía clara; Meteora combina fondo luminoso con rojo y tomas cálidas; el banner del canal usa una escena interior cálida; y las miniaturas de contenido musical mezclan retratos, escenas exteriores y placas tipográficas. Estas observaciones se tratarán como referencias de paleta/composición, no como autorización para copiar imágenes.

Las canciones sin video oficial inequívoco visible en la primera carga —Cortamos y Volvemos, Fango, Nuestro Amor No Es Normal, Tu Dealer de Nostalgia, Un Poco Bien Un Poco Mal y Volver a Vernos— se buscarán individualmente en el canal y en fuentes públicas alternativas antes de fijar su brief.

## Fuentes antiguas verificadas

| Canción | Fuente | Observaciones públicas |
|---|---|---|
| Nuestro Amor No Es Normal | https://www.youtube.com/watch?v=B0anw7LDcDU | Video oficial de Esperón, aproximadamente 388 mil vistas; la página confirma que pertenece al canal oficial. En las recomendaciones aparece una miniatura de Tristella con escena exterior clara y una placa tipográfica de Eclipsis; esto refuerza que el catálogo combina video musical y placas de letra, por lo que las carátulas V2.3.0 deben priorizar una identidad propia por canción. |
| Cortamos y Volvemos | https://www.youtube.com/watch?v=vXjIguLTV6o | Video musical de Esperón, aproximadamente 321 mil vistas; la descripción indica que es un video musical del tema y menciona acordes. La miniatura/recomendación visible del video presenta una escena oscura azul-violeta con el artista, mientras que el canal recomienda Un Poco Bien, Un Poco Mal con una escena verde/roja. Se usará azul-violeta como punto de partida para Cortamos y Volvemos y no se copiará la imagen. |

Las fuentes oficiales muestran suficientes diferencias de fotografía y tratamiento de color para que las flechas no se diseñen con una única plantilla cromática. La función visual V2.3.0 utilizará el brief por canción, un motivo semántico y contraste accesible para distinguir las cuatro direcciones en una pantalla móvil.

## Análisis multimodal de dos referencias oficiales

### Arcoloria

El análisis multimodal describió cian/teal profundo y negro como dominante, con acentos cálidos de amarillo/naranja y refracciones arcoíris en magenta, verde lima y amarillo. También identificó alto contraste de siluetas oscuras contra fuentes de luz, glow, velas blancas, un arco de medio punto y una atmósfera de niebla o humo. La traducción V2.3.0 será: flechas cian, magenta, verde lima y amarillo por dirección; personaje jugador oscuro con gafas circulares y borde crema; rival con silueta de arco y borde de luz; escenario de arco, altar geométrico y haces de luz, sin copiar objetos ni composición exacta del video.

### Solare

El análisis multimodal describió naranjas, dorados y sepias, con teal oscuro y negros como contraste. Observó contraluz, rayos crepusculares, paredes desgastadas, persianas, una habitación decadente y un gran sol naranja con órbitas gráficas. La traducción V2.3.0 será: flechas solar-naranja, amarillo, blanco y ocre; jugador con gafas circulares y cabello representado mediante formas; rival como silueta oscura con rim-light dorado; escenario de ventanas/persianas y sol orbital estilizado. Las decisiones anteriores son adaptaciones originales y se clasifican como inferencias de diseño, no como hechos del video.

Archivos completos de análisis: `qa-lab/rebuild-v230/arcoloria-multimodal-visual.md` y `qa-lab/rebuild-v230/solare-multimodal-visual.md`.

## Evaluación de herramientas abiertas

La búsqueda localizó Demucs como herramienta de separación de voces, `python-audio-separator` como alternativa con modelos de separación, y `CPJKU/onset_detection` como implementación de detectores espectrales. La estrategia V2.3.0 conservará **Demucs ya instalado** para producir stems temporales cuando sea necesario, y combinará el VAD CPU propio con `librosa` y un juez independiente. No se añadirá otra dependencia de separación a ciegas: solo se incorporaría si una prueba A/B sobre las 20 canciones mejora cobertura y reduce falsos positivos sin cambiar el OGG distribuido.

Fuentes evaluadas: [Demucs](https://github.com/facebookresearch/demucs), [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator), [CPJKU/onset_detection](https://github.com/CPJKU/onset_detection) y la documentación de [librosa.onset_detect](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_detect.html).

## Prueba multimodal sobre voz aislada

Se probó el análisis multimodal directamente sobre `Voices-esperon-solare.ogg`. El resultado aportó estructura auxiliar de frases: entradas aproximadas en 0, 13.2 s, 26.5 s, 107 s, 133 s, 159 s, 212 s y 238 s, además de un interludio vocal con poca actividad entre 52 y 107 s. También señaló mayor densidad de sílabas en el puente alrededor de 159 s. Estos timestamps se conservarán como **anclajes auxiliares de baja/mediana confianza**, porque el propio análisis los describe como aproximaciones basadas en onda/oído; no sustituirán los tiempos calculados por VAD, onsets y mapa BPM.

Archivo completo: `qa-lab/rebuild-v230/solare-multimodal-audio.md`.

## Revisión de personajes actuales

La vista de los atlas actuales de Solare confirma un diseño geométrico muy simple: cabeza circular, cuerpo rectangular y extremidades triangulares repetidas en una tira Sparrow de 12 frames. El jugador usa naranja/azul y el rival invierte esos colores; aunque la transparencia y la tira cargan correctamente, la identidad visual es genérica y no incorpora el motivo solar/orbital investigado. V2.3.0 reemplazará ambos atlas con siluetas más distintivas por canción, manteniendo una tira Sparrow compacta, prefijos de animación existentes, transparencia real y un cuerpo central legible en móvil.

## Validación visual V2.3.0 de Solare

La carátula nueva de Solare quedó en 512×512, con composición original de bloques naranja/teal, doble órbita y marco oscuro; no contiene texto generado ni elementos de la miniatura oficial. El atlas de notas quedó en 512×128 con cuatro flechas nítidas, contorno azul oscuro y núcleo circular; las orientaciones izquierda/abajo/arriba/derecha se distinguen sin depender del color. La versión final usará además los atlas de strumline, personajes y stage generados por el mismo brief.

La vista del atlas jugador V2.3.0 muestra 18 frames Sparrow de 128×192 con transparencia, idle, cuatro poses direccionales y poses hold; las expresiones y brazos cambian, evitando el aspecto trabado de un único frame. El stage V2.3.0 mide 1280×720, tiene fondo naranja/teal visible, doble órbita central, plataforma inferior con perspectiva y suficiente contraste; ya no depende de un fondo negro vacío.

## Auditoría multimodal de hojas de contacto

La hoja de contacto de carátulas muestra 20 composiciones diferenciadas. Las primeras 15 usan ilustraciones AI originales con paletas y motivos distintos; las cinco últimas —Solare, Tristella, Tu Dealer de Nostalgia, Un Poco Bien Un Poco Mal y Volver a Vernos— usan el fallback geométrico por límite diario, pero conservan colores, marco y motivos específicos por canción. No se observan imágenes negras, atlas incrustados ni carátulas ausentes; los nombres se mantienen fuera de la imagen para el registro de QA, no dentro del asset distribuido.

La hoja de stages muestra 20 fondos visibles con plataformas inferiores y líneas de perspectiva. Cada stage comparte el mismo contrato visual de juego pero mantiene la paleta de su canción; Solare tiene fondo naranja/azul orbital, Peligrosa rojo/carmesí, Fango verde/ocre, y las cinco carátulas fallback tienen sus correspondientes geometrías. No se aprecia un fondo completamente negro ni una plataforma ausente en la muestra.

La hoja de contacto de los 20 personajes jugadores confirma atlas Sparrow con transparencia, escala uniforme y poses repetidas por dirección. Cada canción usa su propia paleta; las siluetas son pequeñas en la hoja por mostrar 18 frames completos, pero conservan cabeza, cuerpo, extremidades y cambios de pose. La validación XML/runtime confirma que los prefijos Idle, Left, Down, Up, Right y Hold resuelven; esta hoja funciona como revisión de variedad y no sustituye el playtest de animación dentro del APK.
