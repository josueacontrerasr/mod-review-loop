# Fuentes de separación vocal y sincronía

La selección técnica para el análisis mejorado utiliza Demucs de manera **serial** y con segmentación corta por la limitación de memoria observada en el entorno. Demucs documenta que la separación de fuentes genera stems de voces, batería, bajo y otros, y que usar trabajos paralelos multiplica el consumo de RAM. También documenta el uso de `--two-stems=vocals`, CPU y segmentación para reducir presión de recursos.[1]

PyTorch Audio indica que Hybrid Demucs es intensivo en memoria y recomienda dividir canciones en chunks con overlap para reconstruirlas. Esa documentación sustenta el uso de `segment=7`, `overlap=0.1` y concurrencia 1 en este lote.[2]

Los stems resultantes son evidencia para candidatos, no aprobación automática: pueden tener sangrado instrumental o artefactos. Por ese motivo la sincronía se mantiene como revisión manual hasta completar los controles oficiales de Chart Editor y FNF Mobile V-Slice.

## Referencias

[1] [Demucs — Music Source Separation](https://github.com/facebookresearch/demucs)

[2] [PyTorch Audio — Music Source Separation with Hybrid Demucs](https://docs.pytorch.org/audio/2.7.0/tutorials/hybrid_demucs_tutorial.html)

[3] [FunkinCrew — Chart Editor](https://funkincrew-funkin-59.mintlify.app/tools/chart-editor)
