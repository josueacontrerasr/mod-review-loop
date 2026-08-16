# Laboratorio móvil Android para FNF V-Slice 0.8.6

## Objetivo

Este laboratorio reproduce la parte verificable del flujo móvil: arranque de un Android virtual, instalación de una APK de FNF 0.8.6 proporcionada de forma legal, copia de un mod extraído a la ruta oficial, reinicio de la aplicación, captura de pantalla y recolección de logcat. No altera el chart para compensar la latencia del emulador y no descarga APKs desde sitios no autorizados.

La ruta oficial documentada por FNF v0.8.6 es `/sdcard/Android/obb/me.funkin.fnf/mods`. La carpeta de cada mod debe quedar directamente dentro de `mods/` y contener `_polymod_meta.json` en su raíz. El paquete de la aplicación oficial es `me.funkin.fnf`.

El laboratorio mantiene además `optimods` como mod persistente de diagnóstico. El ZIP original se conserva por su SHA-256 y la copia instalada se adapta mínimamente a la regla de API 0.8.x; no se elimina cuando se regeneran los 21 mods Esperón y no se incorpora a sus ZIPs de distribución. Solo se retirará si el usuario lo solicita explícitamente.

## Comparación de alternativas

| Alternativa | Qué reproduce | Coste directo | Viabilidad para este proyecto | Limitación principal |
|---|---|---:|---|---|
| Android Studio Emulator en la computadora del usuario | Android real virtualizado, APK, almacenamiento, renderer, input y logcat | Gratis | **Muy alta** si el equipo tiene VT-x/AMD-V y RAM suficiente | Requiere instalación inicial local y el APK oficial |
| GitHub Actions Linux con Android Emulator | AVD headless, APK, ADB, logs, screenshots y smoke tests por commit/manual | Gratis en el repositorio público según la cuota de GitHub | **Alta para automatización** | No reproduce la cuenta Play Store ni la latencia táctil personal |
| Waydroid en Linux de escritorio | Android en contenedor, APK, ADB y almacenamiento compartido | Gratis | Media | Requiere kernel, sesión gráfica y configuración del equipo anfitrión |
| Android-x86 en VirtualBox | Sistema Android completo en una VM | Gratis | Baja en este sandbox | Necesita virtualización anidada y más recursos |
| Loader headless existente | Contratos, JSON, rutas, assets, audio y charts | Gratis | Alta como gate estructural | No ejecuta APK, HScript, renderer ni input |

Google indica que el Android Emulator necesita aceleración VM para un rendimiento adecuado y que un emulador acelerado no puede ejecutarse dentro de otra VM. El sandbox actual está dentro de una VM, no expone `/dev/kvm`, tiene aproximadamente 3.8 GiB de RAM y no tiene SDK/ADB/emulador instalados; por ello no es un anfitrión apropiado para el emulador nativo. [1] [2]

## Opción recomendada sin coste para el usuario

La solución más práctica combina dos capas. El repositorio conserva el loader headless y el stage oficial de archivos para que cada cambio tenga un gate rápido. El workflow manual `native-android-smoke-v272.yml` proporciona el emulador Android acelerado en un runner Linux público de GitHub y ejecuta un smoke test nativo cuando se proporciona una APK válida. GitHub documenta aceleración Android en runners Linux y uso gratuito e ilimitado de runners estándar para repositorios públicos, sujeto a sus políticas vigentes. [3]

La prueba nativa requiere una APK universal o instalable de FNF 0.8.6. La página oficial de FNF dirige Android a Google Play y la release de GitHub v0.8.6 no publica un APK Android; por eso el workflow exige una URL directa y un SHA-256 proporcionados por el usuario o una APK generada legalmente desde el código fuente. No se deben usar APKMirror, Aptoide, enlaces de terceros ni credenciales de Play Store dentro de GitHub Actions. [4] [5]

## Flujo automatizado

El workflow crea un AVD x86_64 con Android API 35, habilita KVM, desactiva animaciones, inicia el emulador sin ventana y espera a que ADB lo marque como `device`. Después instala la APK, confirma que existe el paquete `me.funkin.fnf`, conserva `optimods`, limpia únicamente los directorios de prueba `esperon-dano-*`, transfiere cada uno de los 21 mods, fuerza el cierre y arranque del juego, captura una pantalla y guarda los últimos mensajes de logcat.
 Cada mod obtiene un reporte individual; cualquier señal de `FATAL EXCEPTION`, `ANR` o muerte del proceso hace fallar el smoke test.

Este procedimiento verifica **instalación, resolución del paquete, transferencia, arranque y ausencia de crash inmediato**. No declara que el usuario haya recorrido Freeplay, Story Mode o PlayState si la build no expone una interfaz automatizable para esas pantallas. Esas áreas requieren una segunda capa de automatización UI con coordenadas/árbol de accesibilidad ajustados al build o una inspección visual dirigida. La sincronización perceptual y la calibración de input siguen necesitando Audio Sync Test y un playtest; la latencia personal no debe convertirse en un cambio del chart.

## Ejecución en GitHub Actions

El workflow es manual para no consumir un emulador en cada PR ni almacenar APKs propietarias. Se ejecuta desde **Actions → Native Android Mobile Smoke V2.7.2 → Run workflow**. Hay que proporcionar una URL directa a una APK legalmente obtenida y su SHA-256 exacto. Una URL de la página de Google Play no sirve como URL directa de APK. Si la APK es un conjunto de splits, debe prepararse una instalación `install-multiple` y el runner actual debe ampliarse antes de probarla.

```bash
sha256sum FNF-0.8.6.apk
```

El artefacto de la ejecución contiene `report.json`, una pantalla inicial, una pantalla por canción y los logs de cada ciclo. Los ZIPs de los mods no se modifican y los artefactos de trabajo no se incluyen en la distribución runtime.

## Ejecución local gratuita

En una computadora Linux, Windows o macOS compatible se puede instalar Android Studio o solo las Android SDK Command-line Tools. Deben estar disponibles JDK, SDK Platform-Tools, Emulator, una imagen x86_64 y virtualización del procesador. En Linux, `emulator -accel-check` debe confirmar KVM; en Windows se usa WHPX/AEHD y en macOS Hypervisor.framework. Crear un AVD con Android API 35 y arrancarlo con `-no-window` para CI o con ventana para inspección manual.

Una vez que el emulador está encendido, el flujo conceptual es:

```bash
adb devices
adb install -r FNF-0.8.6.apk
python3 tools/run_native_mobile_smoke_v272.py . \
  --apk FNF-0.8.6.apk \
  --serial emulator-5554
```

Para una inspección manual, se puede instalar la APK desde la interfaz del emulador, abrir FNF una vez, comprobar que crea la carpeta `mods`, transferir un ZIP extraído con `adb push` a `/sdcard/Android/obb/me.funkin.fnf/mods/` y reiniciar FNF. No se debe dejar el ZIP sin extraer ni añadir una carpeta intermedia.

## Límites actuales y decisión técnica

No es correcto afirmar que el sandbox actual ya tiene un teléfono Android funcional. Se llegó a instalar el SDK oficial y crear el AVD `fnf-vslice-086`, pero el arranque por software sin KVM no alcanzó `sys.boot_completed=1` de forma fiable y provocó presión de memoria; el proceso se detuvo para proteger el entorno. Por tanto, el sandbox conserva una simulación de sistema de archivos y los gates estáticos, pero no debe presentarse como un Android interactivo operativo. La prueba local confirmó que los 21 mods pueden stagedarse con `_polymod_meta.json` en la raíz. La prueba nativa queda preparada en el repositorio y será ejecutable en un anfitrión con KVM, como GitHub Actions o una computadora local compatible, cuando exista una APK legalmente disponible o una build reproducible desde fuente.

### Referencias

[1]: https://developer.android.com/studio/run/emulator-acceleration "Android Developers — Configure hardware acceleration for the Android Emulator"

[2]: https://developer.android.com/studio/run/emulator-commandline "Android Developers — Start the emulator from the command line"

[3]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners "GitHub Docs — GitHub-hosted runners"

[4]: https://github.com/FunkinCrew/Funkin/releases/tag/v0.8.6 "FunkinCrew — FNF v0.8.6 release"

[5]: https://play.google.com/store/apps/details?id=me.funkin.fnf&hl=en_US "Google Play — Friday Night Funkin'"
