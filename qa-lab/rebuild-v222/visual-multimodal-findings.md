# Hallazgos visuales V2.2.2

La carátula de Solare mide 512×512, usa un marco claro, fondo oscuro, círculo naranja, triángulo azul y una diagonal de contraste. La composición conserva lectura a tamaño pequeño y no contiene texto que pueda generar errores de tipografía; el título se entrega por separado como `albumTitleAsset` Sparrow.

El atlas `esperon-solare-notes-strumline.png` mide 512×384 y organiza 12 frames de 128×128 en tres filas: static, press y confirm. Las cuatro direcciones están separadas, mantienen siluetas reconocibles y tienen contraste naranja/azul con borde oscuro. La versión press/confirm añade círculos y diagonales, pero no invade el espacio de los frames vecinos. La escala de runtime se redujo a 0.92 para el strumline y 0.82 para las notas.

Estas revisiones son de los assets generados, no una confirmación de su renderizado dentro del APK; el playtest móvil sigue siendo el gate final de visibilidad.
