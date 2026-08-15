# Evidencia visual adjunta — V2.6.5

## Captura `1000406388.jpg` — Freeplay

La imagen muestra la pantalla **FREEPLAY** con varias cápsulas de canciones. La flecha roja señala la tarjeta grande situada a la derecha del listado, que contiene literalmente el texto **ALBUM PLACEHOLDER** y el dibujo placeholder de FNF. Esta es la carátula que el usuario quiere reemplazar; no es suficiente con modificar únicamente el arte del `albumRoll` interno si esa tarjeta continúa mostrando el fallback.

La tarjeta seleccionada visible en el listado es `Si Te Vas`, mientras que también aparecen `Solare`, `Tristella`, `Tu Dealer de Nost...` y `Un Poco Bien...`. La evidencia debe interpretarse como un problema del arte asociado a la cápsula/selección de Freeplay, vinculado al nivel y su `titleAsset`, además del contrato de álbum como regresión.

## Captura `1000406386.jpg` — gameplay

La imagen muestra dos grupos de receptores. En la parte superior izquierda aparece un grupo compacto de cuatro flechas; en la parte inferior aparece otro grupo de cuatro flechas grandes que corresponde al receptor jugable visible. El usuario señala que la presión/activación se está reflejando en el grupo superior izquierdo, por lo que la revisión debe comprobar tanto el lane del chart como la asociación runtime entre notas, strumline del oponente y strumline del jugador.

La captura también revela una asimetría relevante para el diagnóstico: aunque los charts V2.6.4 están declarados como lanes de jugador `d=4..7`, la auditoría estática descubrió que casi todas las notas usan `d=4` repetido. Esto significa que `d=4..7` estaba corregido solo en el dominio de lado, pero no en la distribución direccional: el generador V2.6.4 reiniciaba el contador por timestamp y asignaba casi todas las notas a la primera dirección del jugador. V2.6.5 debe distribuirlas globalmente en `4,5,6,7` y comprobar después si la activación superior izquierda persiste por un problema runtime independiente.

## Regla de uso

Estas observaciones provienen de las capturas adjuntas proporcionadas por el usuario. No sustituyen un playtest nativo, pero sí fijan visualmente qué elemento debe cambiar y qué síntoma debe reproducirse en las pruebas estáticas y móviles.

## Comparación visual de assets del repositorio

Se abrió `mods/esperon-dano-si-te-vas/images/storymenu/esperon-si-te-vas.png`. Es una imagen horizontal de 512×256 con marco y texto `SI TE VAS`; corresponde al título/arte de nivel de Story/Freeplay capsule, no al formato cuadrado del placeholder mostrado en la captura.

Se abrió `mods/esperon-dano-si-te-vas/images/freeplay/albumRoll/esperon-si-te-vas-art.png`. Es un PNG cuadrado de 512×512 con una fotografía y texto `NUBIA`, lo cual demuestra que existe un arte de álbum visualmente válido en la ruta `albumRoll`. También revela una posible asociación incorrecta de carátula: el archivo entregado para `Si Te Vas` contiene texto `NUBIA`, por lo que la selección puede estar resolviendo un asset equivocado aunque el PNG exista. La auditoría V2.6.5 debe comprobar que el ID/archivo de cada álbum corresponde a su canción, además de comprobar que no sea placeholder.
