#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "tools/diagnose_emulator_capabilities_v273.py",
    ROOT / "tools/android_device_health_v273.py",
    ROOT / "tools/run_native_mobile_smoke_v273.py",
    ROOT / "tools/stage_official_android_mods_v273.py",
    ROOT / "tools/validate_persistent_lab_mod_v273.py",
    ROOT / ".github/workflows/native-android-mobile-smoke-v273.yml",
    ROOT / "docs/mobile-emulator-lab-v273.md",
]


def main() -> int:
    checks: dict[str, bool] = {"required_files": all(p.is_file() for p in REQUIRED)}
    workflow = (ROOT / ".github/workflows/native-android-mobile-smoke-v273.yml").read_text(encoding="utf-8")
    doc = (ROOT / "docs/mobile-emulator-lab-v273.md").read_text(encoding="utf-8")
    checks.update({
        "workflow_dispatch": "workflow_dispatch:" in workflow,
        "kvm_check": "emulator -accel-check" in workflow,
        "current_gpu_mode": "-gpu software" in workflow and "swiftshader_indirect" not in workflow,
        "health_check": "android_device_health_v273.py" in workflow,
        "persistent_gate": "validate_persistent_lab_mod_v273.py" in workflow,
        "package_start_timeout": "--package-start-timeout-seconds 90" in workflow,
        "ui_dump_implemented": "uiautomator" in (ROOT / "tools/run_native_mobile_smoke_v273.py").read_text(encoding="utf-8"),
        "gfxinfo_implemented": "dumpsys\", \"gfxinfo" in (ROOT / "tools/run_native_mobile_smoke_v273.py").read_text(encoding="utf-8"),
        "persistent_policy_documented": "no se desinstala" in doc and "solicitud explícita del usuario" in doc,
        "no_optimizer_runtime_hit": True,
    })
    zip_hits: list[str] = []
    import zipfile
    for archive in sorted((ROOT / "Mods .zip terminados").glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            zip_hits.extend([name for name in zf.namelist() if "optimods" in name.lower()])
    checks["no_optimizer_runtime_hit"] = not zip_hits
    result = {"scope": "EMULATOR_LAB_V273_GATE", "checks": checks, "zip_hits": zip_hits, "status": "PASS" if all(checks.values()) else "ERRORS_FOUND"}
    out = ROOT / "qa-lab/rebuild-v273/emulator-v273/lab-gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": sum(checks.values()), "total": len(checks), "output": str(out)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
