# Laboratorio de emulación FNF Mobile V2.7.3

## Propósito

Esta versión mejora el laboratorio de pruebas para los 21 mods de Esperón en **FNF Mobile V-Slice 0.8.6**. La mejora no cambia charts, audios ni ZIPs de distribución. Se concentra en hacer más confiable la detección de capacidades, el arranque Android, la recopilación de evidencia y la persistencia del mod de diagnóstico `optimods`.

> Un resultado estático o headless no se presenta como prueba de gameplay real. La ejecución nativa necesita un APK legal de FNF 0.8.6 y un host con aceleración VM disponible.

## Mejoras implementadas

| Área | Antes | V2.7.3 |
|---|---|---|
| Capacidades | No había una línea base única | `diagnose_emulator_capabilities_v273.py` registra KVM, flags de virtualización, RAM, disco, SDK, ADB, AVD y herramientas gráficas. |
| Arranque | Esperas fijas y una comprobación simple de `sys.boot_completed` | `android_device_health_v273.py` espera estado ADB, `sys.boot_completed`, package manager, captura inicial, resolución, densidad y propiedades del dispositivo. |
| Proceso FNF | `sleep` después de `monkey` | El runner espera que `me.funkin.fnf` tenga PID y actividad visible antes de capturar. |
| UI | Solo PNG y logcat | Se guarda un `uiautomator dump` por captura para estudiar selectores de Freeplay/Story/PlayState. |
| Rendimiento | No había snapshots de memoria/frames | Se guardan `dumpsys meminfo` y `dumpsys gfxinfo` por campaña/mod. |
| Gráficos | `swiftshader_indirect` | El workflow usa `-gpu software`, opción vigente en la documentación del emulador; el diagnóstico distingue GPU y VM. |
| Aceleración | No se verificaba antes del arranque | El workflow ejecuta `emulator -accel-check` y falla temprano si el runner no ofrece la aceleración requerida. |
| Persistencia | El optimizador se conservaba por convención | El staging reinstala/valida `optimods`; el runner elimina solo `esperon-dano-*` y el gate verifica 14 condiciones. |
| Evidencia CI | Arranque y captura básicos | Se archivan health check, UI dumps, capturas, logs y métricas de memoria/frames. |

## Política de `optimods`

El ZIP original se conserva en `qa-lab/rebuild-v272/persistent-mods/source/`. La copia de laboratorio compatible con FNF 0.8.6 queda en `qa-lab/rebuild-v272/persistent-mods/normalized/optimods/` y se instala en la simulación interna bajo:

```text
qa-lab/mobile-sim/storage/emulated/0/Android/obb/me.funkin.fnf/mods/optimods/
```

El optimizador no entra en los ZIPs Esperón y no se desinstala durante las campañas. La única acción que lo elimina debe ser una solicitud explícita del usuario.

## Resultado real del entorno interno

La línea base V2.7.3 confirma que el sandbox tiene SDK, ADB, emulador y AVD, pero no tiene `/dev/kvm` ni flags `vmx/svm` visibles. El intento de arranque por software no alcanzó `sys.boot_completed=1` de forma estable y generó presión de memoria. Por eso la capa interna actual es una simulación de almacenamiento y validación headless; no se declara que el APK de FNF haya sido jugado dentro de Android en este sandbox.

La capa nativa queda preparada para un runner Linux con KVM. Antes de iniciar la prueba, el workflow exige una APK legal, verifica su SHA-256, comprueba aceleración y luego ejecuta el health check. No se descargan APKs de sitios no verificados ni se automatizan credenciales de Play Store.

## Siguiente capa recomendada

Los dumps UI de V2.7.3 son la base para una segunda iteración de automatización. Con un APK operativo se debe identificar primero la estructura accesible de Freeplay, la selección de canción y las tres dificultades. Después se pueden añadir selectores UI Automator con fallback de coordenadas calibradas por resolución. Solo cuando esos selectores sean estables se debe activar una matriz de 21 canciones × 3 dificultades con capturas de inicio, sección media y final.

Para rendimiento, se recomienda conservar `dumpsys gfxinfo` y complementar con trazas Perfetto en las canciones/escenarios con shaders o alta densidad. Los percentiles P95/P99 de timing de frames y la memoria antes/después de reinicio deben considerarse más informativos que una captura aislada. Los fallos bloqueantes siguen siendo crash, ANR, mod ausente, pantalla negra, personaje/escenario invisible, memoria creciente y stutter reproducible.

## Fuentes

[1] [Android Developers — Configure hardware acceleration for the Android Emulator](https://developer.android.com/studio/run/emulator-acceleration)

[2] [Android Developers — Write automated tests with UI Automator](https://developer.android.com/training/testing/other-components/ui-automator)

[3] [Android Developers — Overview of measuring app performance](https://developer.android.com/topic/performance/measuring-performance)

[4] [Android Developers — Macrobenchmark metrics](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-metrics)

[5] [Android Developers — Start the emulator from the command line](https://developer.android.com/studio/run/emulator-commandline)

[6] [ReactiveCircus — android-emulator-runner](https://github.com/ReactiveCircus/android-emulator-runner)

[7] [Waydroid — Install instructions](https://docs.waydro.id/usage/install-on-desktops)

[8] [Android-x86 — Running in VirtualBox](https://www.android-x86.org/documentation/virtualbox.html)
