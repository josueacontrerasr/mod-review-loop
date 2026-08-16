#!/usr/bin/env python3
"""Wait for and record Android device readiness for the FNF mobile lab."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE = "me.funkin.fnf"


def adb(serial: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["adb", "-s", serial, *args], capture_output=True, text=True, timeout=timeout, check=False)


def prop(serial: str, name: str) -> str:
    p = adb(serial, "shell", "getprop", name)
    return p.stdout.strip().replace("\r", "") if p.returncode == 0 else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--package", default=PACKAGE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if shutil.which("adb") is None:
        raise SystemExit("adb is not installed")

    started = time.monotonic()
    polls: list[dict[str, Any]] = []
    ready = False
    last: dict[str, Any] = {}
    while time.monotonic() - started < args.timeout_seconds:
        state = adb(args.serial, "get-state")
        boot = prop(args.serial, "sys.boot_completed")
        bootanim = prop(args.serial, "init.svc.bootanim")
        pm = adb(args.serial, "shell", "cmd", "package", "list", "packages", timeout=45)
        last = {
            "adb_state": state.stdout.strip(),
            "adb_returncode": state.returncode,
            "sys_boot_completed": boot,
            "boot_animation": bootanim,
            "package_manager_returncode": pm.returncode,
        }
        polls.append(last.copy())
        if state.returncode == 0 and state.stdout.strip() == "device" and boot == "1" and pm.returncode == 0:
            ready = True
            break
        time.sleep(5)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    screenshot = args.output.with_suffix(".png")
    shot = subprocess.run(["adb", "-s", args.serial, "exec-out", "screencap", "-p"], stdout=screenshot.open("wb"), stderr=subprocess.PIPE, check=False) if ready else None
    # Disable only UI animations; do not wipe data or uninstall any mod.
    settings = []
    if ready:
        for key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
            settings.append({"key": key, "result": adb(args.serial, "shell", "settings", "put", "global", key, "0").returncode})
        settings.append({"key": "screen_size", "value": adb(args.serial, "shell", "wm", "size").stdout.strip()})
        settings.append({"key": "screen_density", "value": adb(args.serial, "shell", "wm", "density").stdout.strip()})

    result = {
        "scope": "ANDROID_DEVICE_HEALTH_V273",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "serial": args.serial,
        "package": args.package,
        "ready": ready,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "last_poll": last,
        "poll_count": len(polls),
        "polls": polls[-12:],
        "device_properties": {name: prop(args.serial, name) if ready else "" for name in ("ro.build.version.release", "ro.build.version.sdk", "ro.product.cpu.abi", "ro.kernel.qemu")},
        "settings": settings,
        "boot_screenshot": str(screenshot) if screenshot else None,
        "boot_screenshot_status": "PASS" if shot and shot.returncode == 0 and screenshot.stat().st_size > 0 else ("NOT_READY" if not ready else "ERROR"),
        "status": "PASS" if ready and shot and shot.returncode == 0 and screenshot.stat().st_size > 0 else "ERRORS_FOUND",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "ready": ready, "elapsed_seconds": result["elapsed_seconds"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
