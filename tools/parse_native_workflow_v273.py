#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit(f"PyYAML unavailable: {exc}")

root = Path(__file__).resolve().parents[1]
path = root / ".github/workflows/native-android-mobile-smoke-v273.yml"
data = yaml.safe_load(path.read_text(encoding="utf-8"))
if not isinstance(data, dict) or "jobs" not in data or "native-smoke" not in data["jobs"]:
    raise SystemExit("workflow structure missing jobs.native-smoke")
job = data["jobs"]["native-smoke"]
steps = job.get("steps", [])
names = [step.get("name", "") for step in steps if isinstance(step, dict)]
required = {
    "Stage official Android mods and persistent lab optimizer",
    "Run FNF in accelerated Android Emulator",
    "Upload native Android evidence",
}
missing = sorted(required - set(names))
if missing:
    raise SystemExit(f"missing workflow steps: {missing}")
print(json.dumps({"status": "PASS", "jobs": list(data["jobs"]), "steps": len(steps), "workflow": str(path)}, ensure_ascii=False))
