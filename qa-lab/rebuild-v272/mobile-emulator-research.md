# Investigación de laboratorio móvil gratuito para FNF V-Slice 0.8.6

## Fuentes oficiales consultadas

- Android Emulator — aceleración gráfica/VM: https://developer.android.com/studio/run/emulator-acceleration
- Android Emulator — línea de comandos, AVD, datos y opciones de arranque: https://developer.android.com/studio/run/emulator-commandline
- `avdmanager`: https://developer.android.com/tools/avdmanager
- ADB: https://developer.android.com/tools/adb
- Android Studio y command-line tools: https://developer.android.com/studio
- Android Studio — instalación y requisitos: https://developer.android.com/studio/install
- Waydroid — documentación: https://docs.waydro.id/
- Waydroid — instalación: https://docs.waydro.id/usage/install-on-desktops
- Waydroid — instalar/ejecutar APK: https://docs.waydro.id/usage/install-and-run-android-applications
- Waydroid — ADB: https://docs.waydro.id/faq/using-adb-with-waydroid
- Waydroid — carpeta compartida: https://docs.waydro.id/faq/setting-up-a-shared-folder
- Android-x86 en VirtualBox: https://www.android-x86.org/documentation/virtualbox.html
- GitHub Actions — aceleración Android: https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/
- GitHub-hosted runners: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- FNF 0.8.6 release oficial: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6
- FNF oficial en Google Play: https://play.google.com/store/apps/details?id=me.funkin.fnf&hl=en_US

## Hallazgos verificables

Android Emulator es el método más fiel para simular un teléfono Android en una computadora: permite crear un AVD con `avdmanager`, iniciarlo con `emulator -avd`, instalar APKs con `adb install`, transferir archivos con `adb push` y reiniciar una instalación limpia con `-wipe-data`. Google documenta que `adb` trata al emulador como un dispositivo real y que se debe seleccionar el serial con `adb -s` cuando hay más de un dispositivo.

La aceleración VM del emulador requiere extensiones de virtualización del procesador y un hipervisor. En Linux se apoya en KVM; Google documenta que no se puede ejecutar un emulador acelerado dentro de otra VM, incluyendo VirtualBox, VMware o Docker. El modo software existe, pero es considerablemente más lento y no representa de forma fiable el rendimiento táctil/gráfico de un teléfono.

Waydroid ejecuta Android en un contenedor Linux, no en una VM tradicional. Su documentación ofrece `waydroid app install archivo.apk`, `waydroid app launch paquete`, conexión ADB mediante la IP del contenedor y montajes bind para exponer carpetas del host dentro del almacenamiento Android. Requiere un Linux de escritorio con soporte gráfico y kernel adecuado; no es una opción portátil para un sandbox Linux sin acceso a la sesión gráfica/privilegios necesarios.

Android-x86 puede ejecutarse en VirtualBox y transferir archivos por ADB, pero su propia guía recomienda VT-x/AMD-V, al menos 2 GB de RAM para la VM y 8 GB de disco como punto de partida. En el sandbox actual esto implicaría virtualización anidada, que no está disponible.

GitHub documenta que los runners Linux hospedados admiten aceleración Android y que los repositorios públicos tienen uso estándar gratuito e ilimitado. El changelog oficial indica que se puede habilitar el grupo KVM y usar acciones de emulador Android. Por tanto, GitHub Actions es una alternativa viable para pruebas nativas automatizadas si se dispone del APK de FNF y de un harness que pueda manejar el flujo de instalación/importación; no sustituye un dispositivo físico para medir latencia táctil individual.

La release oficial FNF v0.8.6 existe y la aplicación oficial aparece en Google Play con el paquete `me.funkin.fnf`. La instalación desde Play Store dentro de un emulador puede requerir una imagen AVD con Play Store y una cuenta del usuario; no se debe descargar ni redistribuir un APK de sitios de terceros no autorizados.

## Estado medido del sandbox actual

- Ubuntu Linux x86_64 dentro de una VM KVM.
- 6 vCPU Intel Xeon.
- Aproximadamente 3.8 GiB de RAM disponibles para el entorno.
- `/dev/kvm` ausente.
- `adb`, `emulator`, `avdmanager`, `sdkmanager`, `qemu-system-x86_64` y `waydroid` no están instalados.
- `DISPLAY=:0`, pero no existe una sesión Android ni un renderer Android.

## Consecuencia para el laboratorio FNF

El repositorio ya tiene un loader headless que copia cada mod a `qa-lab/mobile-sim/storage/emulated/0/Android/data/com.funkin.fnf/files/mods` y valida manifests, charts, assets, audio y scripts. El propio loader advierte que no ejecuta un APK, HScript, renderer nativo, latencia táctil ni importación real desde el menú del juego.

La opción gratuita más fiel no es instalar Android-x86 dentro del sandbox actual. La ruta técnicamente correcta es ejecutar Android Emulator con KVM en una computadora local conectada, o usar GitHub Actions Linux con aceleración Android para pruebas nativas automatizadas. En el sandbox actual solo es viable continuar con el loader headless o intentar un emulador sin aceleración, que sería lento y no tendría valor suficiente para afirmar el comportamiento real del juego.

## Hallazgo crítico de rutas

La documentación oficial de FNF v0.8.6 indica que Android debe usar `/sdcard/Android/obb/me.funkin.fnf/mods` y que allí debe colocarse la carpeta extraída del mod. El repositorio actual usa `qa-lab/mobile-sim/storage/emulated/0/Android/data/com.funkin.fnf/files/mods` como ruta simulada. Esa ruta no representa la ruta oficial documentada ni el identificador de paquete publicado en Google Play (`me.funkin.fnf`). Antes de afirmar una simulación de instalación real, el laboratorio debe separar dos rutas: una ruta canónica oficial para el emulador (`/sdcard/Android/obb/me.funkin.fnf/mods`) y, si se conserva por compatibilidad histórica, una ruta legacy explícitamente marcada como no oficial. El cambio debe acompañarse de una prueba de resolución del paquete y de una verificación de que la carpeta raíz contiene directamente `_polymod_meta.json`.

## Compilación y CI nativo

La documentación de Lime indica que FNF puede compilarse para Android con `lime build android` y ejecutarse en un emulador con `lime test android -emulator`. El toolchain requiere JDK, Android SDK, Android NDK y configuración de Lime; la documentación recomienda NDK r21e para versiones de hxcpp compatibles. La guía oficial de FNF v0.8.6 usa el repositorio fuente y sus submódulos de assets, por lo que compilar una APK de prueba desde fuente es técnicamente posible, pero descarga contenido propietario y no debe confundirse con redistribuir una build oficial.

La acción open source `ReactiveCircus/android-emulator-runner` instala los componentes SDK, crea el AVD, arranca el emulador, ejecuta un script y lo apaga. Documenta `target: google_apis_playstore`, `arch: x86_64`, `-no-window`, `-gpu swiftshader_indirect`, `-noaudio`, `-no-boot-anim`, desactivación de animaciones y caché del AVD. GitHub recomienda habilitar permisos KVM en los runners Linux. Esta acción es adecuada para una prueba nativa no interactiva cuando la APK ya está disponible; para una instalación desde Play Store se necesitaría una sesión/cuenta de Google y no debe automatizarse con credenciales privadas.
