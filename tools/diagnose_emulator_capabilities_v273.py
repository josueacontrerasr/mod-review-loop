#!/usr/bin/env python3
"""Collect reproducible emulator-host capabilities without starting Android."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get("ANDROID_SDK_ROOT", "/home/ubuntu/android-sdk"))
AVD_NAME = "fnf-vslice-086"


def run(*args: str) -> dict[str, Any]:
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=20, check=False)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()[-2000:]}
    except Exception as exc:
        return {"returncode": None, "stdout": "", "stderr": repr(exc)}


def read_first(path: Path) -> str:
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def main() -> int:
    mem = run("free", "-b")
    disk = run("df", "-B1", str(ROOT))
    cpuinfo = read_first(Path("/proc/cpuinfo"))
    kvm = Path("/dev/kvm")
    sdkmanager = SDK / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
    avdmanager = SDK / "cmdline-tools" / "latest" / "bin" / "avdmanager"
    emulator = SDK / "emulator" / "emulator"
    adb = SDK / "platform-tools" / "adb"
    commands = {
        "sdkmanager_version": run(str(sdkmanager), "--sdk_root=" + str(SDK), "--version") if sdkmanager.exists() else None,
        "avd_list": run(str(avdmanager), "list", "avd") if avdmanager.exists() else None,
        "emulator_version": run(str(emulator), "-version") if emulator.exists() else None,
        "adb_devices": run(str(adb), "devices") if adb.exists() else None,
        "gpu_tools": {name: shutil.which(name) for name in ("glxinfo", "vulkaninfo", "Xvfb")},
    }
    result = {
        "scope": "EMULATOR_CAPABILITY_BASELINE_V273",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "host": {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version()},
        "virtualization": {
            "kvm_exists": kvm.exists(),
            "kvm_readable": os.access(kvm, os.R_OK) if kvm.exists() else False,
            "cpu_virtualization_flags": sorted(set(line.split(":", 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith("flags") or line.startswith("Features")))[:2],
            "vmx_or_svm_visible": " vmx " in f" {cpuinfo} " or " svm " in f" {cpuinfo} ",
        },
        "memory": mem,
        "disk": disk,
        "sdk_root": str(SDK),
        "paths": {"sdkmanager": sdkmanager.exists(), "avdmanager": avdmanager.exists(), "emulator": emulator.exists(), "adb": adb.exists()},
        "avd_name": AVD_NAME,
        "commands": commands,
        "repo": {"root": str(ROOT), "branch": run("git", "-C", str(ROOT), "branch", "--show-current"), "head": run("git", "-C", str(ROOT), "rev-parse", "HEAD")},
    }
    out = ROOT / "qa-lab" / "rebuild-v273" / "emulator-v273" / "capability-baseline.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "kvm": result["virtualization"]["kvm_exists"], "vmx_or_svm": result["virtualization"]["vmx_or_svm_visible"], "adb": result["paths"]["adb"], "avd": AVD_NAME}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
