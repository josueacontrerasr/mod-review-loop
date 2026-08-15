#!/usr/bin/env python3
"""Audita referencias de UI/note styles sin modificar los mods."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
reports = []
for mod in sorted((root / "mods").glob("esperon-dano-*")):
    if not mod.is_dir():
        continue
    errors: list[str] = []
    warnings: list[str] = []
    song_dirs = [path for path in (mod / "data" / "songs").iterdir() if path.is_dir()]
    if len(song_dirs) != 1:
        reports.append({"mod": mod.name, "status": "ERROR", "errors": ["Debe existir una carpeta de canción"], "warnings": []})
        continue
    song = song_dirs[0].name
    metadata_path = song_dirs[0] / f"{song}-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    style = metadata.get("playData", {}).get("noteStyle")
    if not isinstance(style, str) or not style:
        errors.append("playData.noteStyle ausente")
        style = ""
    style_path = mod / "data" / "notestyles" / f"{style}.json"
    if not style_path.is_file():
        errors.append(f"Note style no resuelto: {style}")
        style_data = {}
    else:
        style_data = json.loads(style_path.read_text(encoding="utf-8"))
        if style_data.get("version") != "1.0.0":
            warnings.append("Versión de note style distinta de 1.0.0; requiere contraste con contrato V-Slice")
        assets = style_data.get("assets")
        if not isinstance(assets, dict):
            errors.append("Campo assets ausente o inválido")
            assets = {}
        for required in ("note", "noteStrumline"):
            if required not in assets:
                errors.append(f"Asset de note style ausente: {required}")
        raw = style_path.read_text(encoding="utf-8")
        asset_refs = sorted(set(re.findall(r'"assetPath"\s*:\s*"([^"]+)"', raw)))
        for asset in asset_refs:
            relative = asset.removeprefix("shared:")
            candidates = [mod / "images" / f"{relative}.png", mod / "images" / f"{relative}.xml"]
            if not any(candidate.is_file() for candidate in candidates):
                errors.append(f"AssetPath no resuelto: {asset}")
    note_png = mod / "images" / "notes" / f"{style}-notes.png"
    note_xml = note_png.with_suffix(".xml")
    strum_png = mod / "images" / "notes" / f"{style}-strumline.png"
    strum_xml = strum_png.with_suffix(".xml")
    for expected in (note_png, note_xml, strum_png, strum_xml):
        if not expected.is_file():
            errors.append(f"Asset obligatorio ausente: {expected.relative_to(mod)}")
    if note_xml.is_file():
        xml = note_xml.read_text(encoding="utf-8", errors="replace")
        for direction in ("left", "down", "up", "right"):
            if direction not in xml.lower():
                warnings.append(f"Atlas de notas no contiene etiqueta detectable para {direction}")
    hxc_files = sorted((mod / "scripts").glob("*.hxc")) if (mod / "scripts").is_dir() else []
    if len(hxc_files) != 1:
        errors.append(f"Cantidad de scripts HUD inesperada: {len(hxc_files)}")
    else:
        hxc = hxc_files[0].read_text(encoding="utf-8", errors="replace")
        if "onCountdownStart" not in hxc or "healthBar" not in hxc:
            errors.append("El script HUD no aplica una configuración de barra de vida detectable")
        forbidden = ("audio", "bpm", "offset", "timeChanges", "notes")
        for token in forbidden:
            if re.search(rf'(?i)\b{re.escape(token)}\b\s*=', hxc):
                errors.append(f"El script HUD parece modificar contenido musical: {token}")
    reports.append({"mod": mod.name, "status": "PASS" if not errors else "ERROR", "errors": errors, "warnings": warnings, "noteStyle": style})

summary = {
    "mods": len(reports),
    "passed": sum(report["status"] == "PASS" for report in reports),
    "failed": sum(report["status"] != "PASS" for report in reports),
    "warnings": sum(len(report["warnings"]) for report in reports),
    "reports": reports,
}
out = root / "artifacts" / "ui-audit" / "reference-audit.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: summary[key] for key in ("mods", "passed", "failed", "warnings")}, ensure_ascii=False))
raise SystemExit(0 if not summary["failed"] else 1)
