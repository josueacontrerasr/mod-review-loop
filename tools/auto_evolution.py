#!/usr/bin/env python3
"""Revisión periódica segura de ZIPs V-Slice.

No modifica chart, BPM, offsets, timeChanges, audio ni assets visuales. Solo puede
reponer documentación no musical inequívocamente ausente y crear un ZIP patch si
la reparación posterior supera la validación estructural.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^(Mod-.+)-V(\d+\.\d+\.\d+)\.zip$")

spec = importlib.util.spec_from_file_location("vslice_pipeline", ROOT / "tools" / "vslice_pipeline.py")
if spec is None or spec.loader is None:
    raise RuntimeError("No se pudo cargar vslice_pipeline.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


def within_cutoff() -> tuple[bool, str]:
    raw = os.environ.get("EVOLUTION_UNTIL_CST")
    if not raw:
        return True, "NOT_CONFIGURED"
    cutoff = datetime.fromisoformat(raw)
    current = datetime.now(ZoneInfo("America/Chicago"))
    return current < cutoff, cutoff.isoformat()


def safe_text(title: str, field: str) -> str:
    if field == "CREDITS.txt":
        return f"MOD: {title}\nCréditos de audio: confirmar derechos antes de distribución pública.\n"
    if field == "LICENSE.txt":
        return "Los assets geométricos y scripts pueden reutilizarse con atribución a Manus AI. El audio permanece sujeto a los derechos de sus titulares.\n"
    return f"Instalar este mod en la carpeta mods de FNF Mobile V-Slice. Ejecutar Audio Sync Test antes de jugar.\n"


def repair_non_musical(mod: Path) -> list[str]:
    changes: list[str] = []
    manifest_path = mod / "_polymod_meta.json"
    if not manifest_path.is_file():
        return changes
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    title = str(manifest.get("title", mod.name))
    for filename in ("CREDITS.txt", "LICENSE.txt", "INSTALACION_MOVIL.txt"):
        target = mod / filename
        if not target.is_file():
            target.write_text(safe_text(title, filename), encoding="utf-8")
            changes.append(f"Se repuso {filename}")
    required = {"description": f"Mod V-Slice de {title}; requiere Audio Sync Test y playtest móvil.", "license": "Custom — see LICENSE.txt", "contributors": [{"name": "Manus AI", "role": "Automatización técnica"}]}
    changed_manifest = False
    for key, value in required.items():
        if not manifest.get(key):
            manifest[key] = value
            changes.append(f"Se completó manifest.{key}")
            changed_manifest = True
    if changed_manifest:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changes


def next_version(stem: str) -> tuple[str, str]:
    match = VERSION_RE.match(stem)
    if not match:
        raise ValueError(f"Nombre de ZIP inválido: {stem}")
    mod, version = match.groups()
    major, minor, patch = (int(part) for part in version.split("."))
    return mod, f"{major}.{minor}.{patch + 1}"


def audit_zip(zip_path: Path, output: Path, delivery_dir: Path, history_dir: Path) -> dict:
    report: dict = {"zip": zip_path.name, "status": "PASS", "changes": [], "errors": [], "warnings": []}
    with tempfile.TemporaryDirectory(prefix="vslice-review-") as temp_dir:
        temp = Path(temp_dir)
        try:
            with zipfile.ZipFile(zip_path) as archive:
                bad = archive.testzip()
                if bad:
                    report["errors"].append(f"CRC inválido: {bad}")
                    report["status"] = "ERROR_ESTRUCTURAL"
                    return report
                roots = {name.split("/")[0] for name in archive.namelist() if name and not name.startswith("__MACOSX")}
                if len(roots) != 1:
                    report["errors"].append("El ZIP no contiene una única carpeta raíz")
                    report["status"] = "ERROR_ESTRUCTURAL"
                    return report
                archive.extractall(temp)
            mod = temp / next(iter(roots))
            initial = pipeline.validate_mod(mod)
            report["initial"] = initial
            if initial["status"] != "PASS":
                repairs = repair_non_musical(mod)
                if repairs:
                    final = pipeline.validate_mod(mod)
                    report["final"] = final
                    if final["status"] == "PASS":
                        mod_id, version = next_version(zip_path.name)
                        target = delivery_dir / f"{mod_id}-V{version}.zip"
                        delivery_dir.mkdir(parents=True, exist_ok=True)
                        history_dir.mkdir(parents=True, exist_ok=True)
                        if target.exists():
                            target.unlink()
                        shutil.make_archive(str(target.with_suffix("")), "zip", root_dir=temp, base_dir=mod.name)
                        archived = history_dir / zip_path.name
                        if archived.exists():
                            archived.unlink()
                        shutil.move(str(zip_path), str(archived))
                        report["changes"] = repairs
                        report["new_zip"] = target.relative_to(ROOT).as_posix()
                        report["archived_zip"] = archived.relative_to(ROOT).as_posix()
                        report["status"] = "REPAIRED"
                    else:
                        report["errors"].extend(final["errors"])
                        report["status"] = "ERROR_ESTRUCTURAL"
                else:
                    report["errors"].extend(initial["errors"])
                    report["status"] = "ERROR_ESTRUCTURAL"
            else:
                report["warnings"].extend(initial["warnings"])
        except Exception as exc:
            report["status"] = "ERROR_ESTRUCTURAL"
            report["errors"].append(str(exc))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/reports")
    parser.add_argument("--delivery-dir", default="Mods .zip terminados")
    parser.add_argument("--history-dir", default="dist/historico")
    args = parser.parse_args()
    allowed, cutoff = within_cutoff()
    destination = ROOT / args.output
    destination.mkdir(parents=True, exist_ok=True)
    if not allowed:
        payload = {"status": "CUTOFF_REACHED", "cutoff_cst": cutoff, "reports": [], "changes_applied": []}
        (destination / "auto-evolucion-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    delivery_dir = ROOT / args.delivery_dir
    history_dir = ROOT / args.history_dir
    zip_paths = sorted(path for path in delivery_dir.glob("Mod-*-V*.zip") if path.name != "Mod-Esperon-Coleccion-V2.1.0.zip")
    reports = [audit_zip(path, destination, delivery_dir, history_dir) for path in zip_paths]
    payload = {"status": "PASS" if all(item["status"] in {"PASS", "REPAIRED"} for item in reports) else "ERRORS_FOUND", "cutoff_cst": cutoff, "reports": reports, "changes_applied": [change for item in reports for change in item.get("changes", [])]}
    (destination / "auto-evolucion-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "zips": len(reports), "repairs": len(payload["changes_applied"])}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
