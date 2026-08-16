#!/usr/bin/env python3
"""Run an optional native Android smoke test for the Esperon mods.

The APK must be supplied explicitly with --apk; this tool never downloads or
redistributes a game APK. It requires a connected Android Emulator/device with
adb and the official FNF package name me.funkin.fnf.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
PACKAGE = "me.funkin.fnf"
REMOTE_MOD_ROOT = "/sdcard/Android/obb/me.funkin.fnf/mods"
CRASH_RE = re.compile(r"(?i)(fatal exception|process .* has died|FATAL EXCEPTION|signal 11|ANR in)")


def run_adb(serial: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["adb", "-s", serial, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def require_adb(serial: str) -> None:
    if shutil.which("adb") is None:
        raise SystemExit("ERROR: adb no está instalado; instala Android SDK Platform-Tools.")
    devices = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False)
    if serial not in devices.stdout or f"{serial}\tdevice" not in devices.stdout:
        raise SystemExit(f"ERROR: el dispositivo {serial!r} no aparece como device en adb devices.")


def push_persistent_mod(serial: str, mod: Path) -> dict[str, Any]:
    result = run_adb(serial, "push", str(mod), f"{REMOTE_MOD_ROOT}/", timeout=300)
    return {
        "status": "PASS" if result.returncode == 0 else "ERROR",
        "step": "push_persistent_lab_mod",
        "mod": mod.name,
        "stderr": result.stderr.strip()[-1000:],
        "stdout": result.stdout.strip()[-1000:],
    }


def push_mod(serial: str, mod: Path) -> dict[str, Any]:
    # Keep the persistent lab optimizer. Only remove the Esperon test mods.
    clear = run_adb(serial, "shell", "sh", "-c", f"mkdir -p '{REMOTE_MOD_ROOT}' && rm -rf '{REMOTE_MOD_ROOT}'/esperon-dano-*")
    if clear.returncode != 0:
        return {"status": "ERROR", "step": "clear_remote_mods", "stderr": clear.stderr.strip()[-1000:]}
    result = run_adb(serial, "push", str(mod), f"{REMOTE_MOD_ROOT}/", timeout=300)
    return {
        "status": "PASS" if result.returncode == 0 else "ERROR",
        "step": "push_mod",
        "mod": mod.name,
        "stderr": result.stderr.strip()[-1000:],
        "stdout": result.stdout.strip()[-1000:],
    }


def wait_for_package_ready(serial: str, timeout_seconds: int = 60) -> dict[str, Any]:
    started = time.monotonic()
    polls: list[dict[str, str]] = []
    while time.monotonic() - started < timeout_seconds:
        pid = run_adb(serial, "shell", "pidof", PACKAGE, timeout=30)
        activity = run_adb(serial, "shell", "dumpsys", "activity", "activities", timeout=30)
        row = {"pid": pid.stdout.strip(), "activity_has_package": PACKAGE in activity.stdout}
        polls.append({k: str(v) for k, v in row.items()})
        if pid.returncode == 0 and pid.stdout.strip() and row["activity_has_package"]:
            return {"status": "PASS", "elapsed_seconds": round(time.monotonic() - started, 2), "polls": polls[-12:], **row}
        time.sleep(2)
    return {"status": "ERROR", "elapsed_seconds": round(time.monotonic() - started, 2), "polls": polls[-12:], "error": "package_not_ready"}


def capture_ui(serial: str, output: Path, label: str) -> dict[str, Any]:
    xml_remote = "/sdcard/window-v273.xml"
    xml_local = output / f"{label}.ui.xml"
    dump = run_adb(serial, "shell", "uiautomator", "dump", xml_remote, timeout=60)
    pulled = run_adb(serial, "pull", xml_remote, str(xml_local), timeout=60)
    return {
        "ui_dump": str(xml_local),
        "dump_stdout": dump.stdout[-1000:],
        "dump_stderr": dump.stderr[-1000:],
        "status": "PASS" if dump.returncode == 0 and pulled.returncode == 0 and xml_local.exists() else "ERROR",
    }


def capture_performance(serial: str, output: Path, label: str) -> dict[str, Any]:
    mem_path = output / f"{label}.meminfo.txt"
    gfx_path = output / f"{label}.gfxinfo.txt"
    mem = run_adb(serial, "shell", "dumpsys", "meminfo", PACKAGE, timeout=60)
    gfx = run_adb(serial, "shell", "dumpsys", "gfxinfo", PACKAGE, timeout=60)
    mem_path.write_text(mem.stdout, encoding="utf-8")
    gfx_path.write_text(gfx.stdout, encoding="utf-8")
    return {
        "meminfo": str(mem_path),
        "gfxinfo": str(gfx_path),
        "meminfo_status": "PASS" if mem.returncode == 0 else "ERROR",
        "gfxinfo_status": "PASS" if gfx.returncode == 0 else "ERROR",
    }


def capture(serial: str, output: Path, label: str) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    screenshot = output / f"{label}.png"
    logcat = output / f"{label}.logcat.txt"
    shot = subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"], stdout=screenshot.open("wb"), stderr=subprocess.PIPE, check=False)
    logs = run_adb(serial, "logcat", "-d", "-t", "300", timeout=60)
    logcat.write_text(logs.stdout, encoding="utf-8")
    crash_lines = [line for line in logs.stdout.splitlines() if CRASH_RE.search(line)]
    ui = capture_ui(serial, output, label)
    perf = capture_performance(serial, output, label)
    return {
        "screenshot": str(screenshot),
        "logcat": str(logcat),
        "screenshot_status": "PASS" if shot.returncode == 0 and screenshot.stat().st_size > 0 else "ERROR",
        "crash_signals": crash_lines[-20:],
        "ui": ui,
        "performance": perf,
        "status": "ERROR" if crash_lines else ("PASS" if shot.returncode == 0 and ui["status"] == "PASS" else "ERROR"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--apk", type=Path, required=True, help="APK proporcionada por el usuario o compilada de fuente")
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--boot-wait-seconds", type=int, default=12, help="Legacy minimum wait retained for compatibility")
    parser.add_argument("--per-mod-wait-seconds", type=int, default=8, help="Legacy minimum wait retained for compatibility")
    parser.add_argument("--package-start-timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    root = args.root.resolve()
    apk = args.apk.resolve()
    if not apk.is_file():
        raise SystemExit(f"ERROR: no existe la APK indicada: {apk}")
    require_adb(args.serial)

    output = root / "qa-lab" / "rebuild-v272" / "native-mobile-smoke-v272"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    source_root = root / "mods"
    persistent_mod = root / "qa-lab" / "rebuild-v272" / "persistent-mods" / "normalized" / "optimods"
    if not persistent_mod.is_dir():
        raise SystemExit(f"ERROR: falta el optimizador persistente normalizado: {persistent_mod}")

    report: dict[str, Any] = {
        "scope": "NATIVE_ANDROID_SMOKE_V272",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "package": PACKAGE,
        "serial": args.serial,
        "apk": str(apk),
        "remote_mod_root": REMOTE_MOD_ROOT,
        "status": "ERRORS_FOUND",
        "limitations": [
            "Confirma instalación, arranque por proceso, transferencia de mod, screenshot, UI dump, memoria, gfxinfo y señales de crash.",
            "Todavía no navega automáticamente por Freeplay/Story/PlayState; los dumps UI quedan como evidencia para construir selectores específicos del build.",
            "La latencia táctil individual requiere calibración/playtest humano.",
        ],
        "mods": [],
    }

    install = run_adb(args.serial, "install", "-r", str(apk), timeout=600)
    report["install"] = {"returncode": install.returncode, "stdout": install.stdout[-2000:], "stderr": install.stderr[-2000:]}
    if install.returncode != 0:
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    package_path = run_adb(args.serial, "shell", "pm", "path", PACKAGE)
    report["package_path"] = {"returncode": package_path.returncode, "stdout": package_path.stdout.strip(), "stderr": package_path.stderr.strip()}
    if package_path.returncode != 0 or not package_path.stdout.strip():
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    persistent_push = push_persistent_mod(args.serial, persistent_mod)
    report["persistent_lab_mod"] = {
        "local_path": str(persistent_mod),
        "remote_path": f"{REMOTE_MOD_ROOT}/optimods",
        "push": persistent_push,
        "uninstall_policy": "PERSIST_UNTIL_USER_EXPLICITLY_REQUESTS_REMOVAL",
    }
    if persistent_push.get("status") != "PASS":
        report["status"] = "ERRORS_FOUND"
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    run_adb(args.serial, "shell", "am", "force-stop", PACKAGE)
    launch = run_adb(args.serial, "shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1", timeout=120)
    report["initial_launch"] = {"returncode": launch.returncode, "stdout": launch.stdout[-2000:], "stderr": launch.stderr[-2000:]}
    report["initial_ready"] = wait_for_package_ready(args.serial, args.package_start_timeout_seconds)
    report["initial_capture"] = capture(args.serial, output, "00_initial")

    for index, song in enumerate(SONGS, start=1):
        mod = source_root / f"esperon-dano-{song}"
        row: dict[str, Any] = {"song": song, "mod": mod.name}
        if not mod.is_dir():
            row.update({"status": "ERROR", "error": f"missing source {mod}"})
            report["mods"].append(row)
            continue
        row["push"] = push_mod(args.serial, mod)
        if row["push"].get("status") != "PASS":
            row["status"] = "ERROR"
            report["mods"].append(row)
            continue
        run_adb(args.serial, "shell", "am", "force-stop", PACKAGE)
        launch = run_adb(args.serial, "shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1", timeout=120)
        row["launch"] = {"returncode": launch.returncode, "stdout": launch.stdout[-1000:], "stderr": launch.stderr[-1000:]}
        row["ready"] = wait_for_package_ready(args.serial, args.package_start_timeout_seconds)
        row["capture"] = capture(args.serial, output, f"{index:02d}_{song}")
        row["status"] = "PASS" if row["launch"]["returncode"] == 0 and row["ready"]["status"] == "PASS" and row["capture"]["status"] == "PASS" else "ERROR"
        report["mods"].append(row)

    report["passed"] = sum(row.get("status") == "PASS" for row in report["mods"])
    report["expected"] = len(SONGS)
    report["status"] = "PASS" if report["passed"] == report["expected"] and not report["initial_capture"].get("crash_signals") else "ERRORS_FOUND"
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "passed": report["passed"], "expected": report["expected"], "output": str(output / "report.json")}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
