#!/usr/bin/env python3
"""Validador de assets visuales V2 para mods V-Slice personalizados."""
from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = ("left", "down", "up", "right")
TITLE = {"left": "Left", "down": "Down", "up": "Up", "right": "Right"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path, errors: list[str]) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON inválido: {path.relative_to(ROOT)} ({exc})")
        return {}


def mod_report(mod: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    slug = mod.name.removeprefix("esperon-dano-")
    style_id = f"esperon-{slug}-notes"
    metadata_paths = list((mod / "data/songs").glob("*/*-metadata.json"))
    chart_paths = list((mod / "data/songs").glob("*/*-chart.json"))
    inst_paths = list((mod / "songs").rglob("Inst.ogg"))
    if len(metadata_paths) != 1 or len(chart_paths) != 1 or len(inst_paths) != 1:
        errors.append("No se resolvió la terna metadata/chart/Inst.ogg")
        return {"mod": mod.name, "status": "ERROR", "errors": errors, "warnings": warnings}
    metadata = load(metadata_paths[0], errors)
    if metadata.get("playData", {}).get("noteStyle") != style_id:
        errors.append("Metadata no referencia el note style propio")
    style_path = mod / "data/notestyles" / f"{style_id}.json"
    style = load(style_path, errors) if style_path.is_file() else {}
    if style.get("fallback") != "funkin":
        errors.append("El note style debe conservar fallback='funkin'")
    assets = style.get("assets", {}) if isinstance(style.get("assets"), dict) else {}
    expected_note_path = f"shared:notes/{style_id}-notes"
    expected_strum_path = f"shared:notes/{style_id}-strumline"
    if assets.get("note", {}).get("assetPath") != expected_note_path:
        errors.append("Asset note no apunta al atlas propio")
    if assets.get("noteStrumline", {}).get("assetPath") != expected_strum_path:
        errors.append("Asset noteStrumline no apunta al atlas propio")
    for asset_name in (f"{style_id}-notes", f"{style_id}-strumline"):
        png = mod / "images/notes" / f"{asset_name}.png"
        xml = png.with_suffix(".xml")
        if not png.is_file() or not xml.is_file():
            errors.append(f"Atlas ausente: images/notes/{asset_name}")
            continue
        try:
            root = ET.parse(xml).getroot()
            frame_names = {node.attrib.get("name") for node in root.findall("SubTexture")}
            if asset_name.endswith("-notes"):
                required = {f"note{TITLE[d]}" for d in DIRECTIONS}
            else:
                required = {f"{state}{TITLE[d]}0" for state in ("static", "press", "confirm") for d in DIRECTIONS}
            if not required.issubset(frame_names):
                errors.append(f"Prefijos de atlas incompletos: {asset_name}")
        except Exception as exc:
            errors.append(f"XML inválido: {xml.relative_to(mod)} ({exc})")
    for label in ("sick", "good", "bad", "shit", *[f"num{i}" for i in range(10)]):
        if not (mod / "images/ui" / style_id / f"{label}.png").is_file():
            errors.append(f"Asset HUD ausente: {label}.png")
    integrity_path = mod / "visual-v2-integrity.json"
    integrity = load(integrity_path, errors) if integrity_path.is_file() else {}
    if integrity.get("status") != "PASS_NO_MUSICAL_DATA_CHANGED":
        errors.append("No existe evidencia de integridad visual-only")
    protected = integrity.get("protected_after", {})
    if protected.get("chart_sha256") != sha256(chart_paths[0]):
        errors.append("El chart cambió después de la integración visual")
    if protected.get("inst_sha256") != sha256(inst_paths[0]):
        errors.append("El instrumental cambió después de la integración visual")
    if load(mod / "_polymod_meta.json", errors).get("mod_version") != "1.1.0":
        errors.append("La versión del manifiesto no es 1.1.0")
    if (mod / "sync-report.json").is_file():
        warnings.append("Audio Sync Test y playtest móvil siguen pendientes; la actualización fue visual-only.")
    return {"mod": mod.name, "status": "PASS" if not errors else "ERROR", "errors": errors, "warnings": warnings}


def main() -> int:
    global ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--mod", help="ID de un único mod para validación controlada")
    parser.add_argument("--output", help="Ruta JSON del reporte; por defecto artifacts/reports/visual-v2-validation.json")
    args = parser.parse_args()
    ROOT = Path(args.root).resolve()
    if args.mod:
        selected = ROOT / "mods" / args.mod
        if not selected.is_dir():
            raise SystemExit(f"Mod no encontrado: {selected}")
        paths = [selected]
    else:
        paths = [path for path in sorted((ROOT / "mods").glob("esperon-dano-*")) if path.is_dir()]
    reports = [mod_report(path) for path in paths]
    output = Path(args.output).resolve() if args.output else ROOT / "artifacts" / "reports" / "visual-v2-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"scope": "VISUAL_V2_AND_MUSICAL_INTEGRITY", "reports": reports}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = sum(len(item["errors"]) for item in reports)
    print(json.dumps({"mods": len(reports), "errors": errors, "status": "PASS" if errors == 0 else "ERROR"}, ensure_ascii=False))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
