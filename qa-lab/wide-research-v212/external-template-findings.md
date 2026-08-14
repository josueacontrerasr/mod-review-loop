# Evidencia externa: template comunitario V-Slice

Repositorio consultado: https://github.com/crowplexus/Funkin-VSlice-Template

Commit consultado: `8c40412bf352d37b37641bb039dca26df157db77`, último commit visible `2024-05-03`.

El README indica que los scripts HScript usan extensión `.hxc`, que pueden ubicarse en distintas partes del mod siempre que extiendan la clase correcta (`Module`, `Song`, `NoteStyle`, etc.), y que los assets siguen la organización normal de V-Slice, incluyendo `assets/images` y `assets/shared/images`. El README es histórico y anterior a FNF 0.8.6, por lo que se usa como confirmación secundaria del patrón `shared/images`, no como autoridad de schemas actuales ni de APIs móviles.

La fuente primaria continúa siendo la documentación/código oficial de FunkinCrew v0.8.6 y la guía oficial de instalación. La auditoría de los 20 mods debe comprobar tanto las rutas de assets como la clase/import de cada HScript.
