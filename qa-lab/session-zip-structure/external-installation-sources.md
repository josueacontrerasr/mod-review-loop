# Fuentes oficiales consultadas

La guía oficial de instalación de mods de FNF indica que se debe iniciar el juego para crear `mods`, extraer el ZIP y colocar la carpeta del mod dentro de `mods`; en Android especifica `/sdcard/Android/obb/me.funkin.fnf/mods`, y en iOS `En mi iPhone/Friday Night Funkin/mods`.

Fuente: https://github.com/FunkinCrew/Funkin/blob/main/docs/INSTALLING_MODS.md

La publicación oficial sobre el Mod Menu explica que el juego acepta arrastrar una carpeta o ZIP al sistema de mods y que la nueva organización de assets puede requerir migración. También indica que las rutas antiguas de reemplazo de assets pueden dejar de funcionar y deben moverse a las rutas nuevas; por ejemplo, recursos antes ubicados en `shared/images/...` deben seguir la organización de assets que el motor reconoce.

Fuente: https://funkin.me/blog/2026-08-03/

La comparación de los tres ZIP adjuntos mostró estructuras mixtas: `fnf_el_chavo_del_8_v2__7638d.zip` y `MoonLightMobile.zip` usan una única carpeta raíz con `_polymod_meta.json` dentro; `vs_huggy_wuggy_c6a32.zip` distribuye directamente los archivos del mod en la raíz del ZIP. Los 20 ZIP Esperón se validan con una única carpeta raíz y el manifiesto dentro de ella, pero sus referencias `shared:` apuntaban inicialmente a archivos ubicados bajo `images/` en lugar de `shared/images/`, y faltaba `data/songs/<song>/manifest.json`. Esa discrepancia fue la causa estructural investigada.
