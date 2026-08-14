#!/usr/bin/env python3
"""Repara imports de HUD HScript sin tocar audio, charts ni timing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_IMPORTS = (
    "import funkin.modding.module.Module;",
    "import funkin.play.PlayState;",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repair_script(path: Path) -> tuple[bool, str, str]:
    before = path.read_text(encoding="utf-8")
    after = before
    missing = [line for line in REQUIRED_IMPORTS if line not in after]
    if missing:
        insertion = "\n".join(missing) + "\n\n"
        first_code = after.find("class ")
        if first_code < 0:
            raise RuntimeError(f"No se encontró declaración class en {path}")
        after = after[:first_code] + insertion + after[first_code:]
        path.write_text(after, encoding="utf-8")
    return bool(missing), sha256(path), sha256(path) if missing else sha256(path)


def main() -> int:
    mods = sorted(path for path in (ROOT / "mods").glob("esperon-dano-*") if path.is_dir())
    entries = []
    for mod in mods:
        chart = next((mod / "data/songs").glob("*/*-chart.json"))
        inst = next((mod / "songs").rglob("Inst.ogg"))
        before_music = {"chart_sha256": sha256(chart), "inst_sha256": sha256(inst)}
        scripts = sorted((mod / "scripts").glob("*.hxc"))
        if len(scripts) != 1:
            raise RuntimeError(f"{mod.name}: se esperaba un HUD .hxc y hay {len(scripts)}")
        script = scripts[0]
        old_script_sha = sha256(script)
        changed, _, _ = repair_script(script)
        new_script_sha = sha256(script)
        after_music = {"chart_sha256": sha256(chart), "inst_sha256": sha256(inst)}
        if before_music != after_music:
            raise RuntimeError(f"Integridad musical violada en {mod.name}")
        text = script.read_text(encoding="utf-8")
        if any(line not in text for line in REQUIRED_IMPORTS):
            raise RuntimeError(f"Imports incompletos en {script}")
        entries.append({
            "mod": mod.name,
            "script": script.relative_to(mod).as_posix(),
            "changed": changed,
            "old_script_sha256": old_script_sha,
            "new_script_sha256": new_script_sha,
            "protected_music": before_music,
            "status": "PASS",
        })
    payload = {
        "scope": "HUD_HSCRIPT_IMPORT_REPAIR",
        "mods": len(mods),
        "changed": sum(item["changed"] for item in entries),
        "required_imports": list(REQUIRED_IMPORTS),
        "entries": entries,
        "status": "PASS" if len(mods) == 20 and all(item["status"] == "PASS" for item in entries) else "ERRORS_FOUND",
        "limitation": "El parseo/runtime final debe confirmarse en FNF Mobile V-Slice 0.8.6.",
    }
    output = ROOT / "qa-lab" / "session-hscript" / "hscript-import-repair.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("mods", "changed", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
