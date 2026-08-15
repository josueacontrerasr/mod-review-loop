# Esperón FNF Mobile V-Slice 0.8.6 — V2.3.0

## Alcance

V2.3.0 actualiza los 20 mods de Esperón para FNF Mobile V-Slice 0.8.6. Cada canción conserva su audio instalado y recibe charts `easy`, `normal` y `hard`, con menor densidad y velocidad en easy, referencia normal en normal y mayor densidad/velocidad en hard. Las tres dificultades comparten anclajes temporales derivados del audio; la velocidad se cambia mediante `scrollSpeed`, no desplazando las notas.

## Sincronía chart-voces

El pipeline usa VAD CPU a 16 kHz con ventanas de 20 ms y umbral calibrado al ruido, dos perfiles independientes de detección de ataques para generar el consenso, un perfil mediano separado para reparar outliers y un cuarto perfil espectral a 44.1 kHz para verificar. La promoción conserva BPM, `timeChanges`, `Inst.ogg` y las voces. El gate multimétodo exige que al menos dos de cuatro métodos respalden al menos 90% de las notas dentro de 80 ms; las 60 dificultades pasan ese gate.

## Visuales

Se regeneraron los 20 estilos de notas con cuatro direcciones, contornos y motivos derivados de paleta; los 40 personajes recibieron atlas Sparrow de 18 frames con idle, cuatro direcciones y cuatro poses hold; los 20 stages recibieron fondo 1280×720, plataforma y contraste visible; y las 20 carátulas Freeplay se actualizaron a 512×512 con títulos Sparrow 512×128 y frames `idle0000`/`switch0000`. Quince carátulas se generaron con el estilo visual de referencia; cinco se produjeron mediante fallback geométrico determinista porque se alcanzó el límite diario del generador visual del plan gratuito.

## Verificación y uso

Runtime contract: 20/20 PASS. ZIP install layout: 20/20 PASS más colección CRC PASS. Los ZIPs individuales contienen solamente la raíz del mod y sus assets; los reportes permanecen fuera. Para instalar, extrae un ZIP individual directamente en `mods/`, elimina la versión anterior y reinicia FNF Mobile para limpiar caché.

> El análisis estático y el gate multimétodo no pueden sustituir el Audio Sync Test nativo del Chart Editor ni el playtest en el dispositivo móvil. La latencia personal debe calibrarse en el teléfono sin desplazar el chart distribuido.
