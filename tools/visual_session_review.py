#!/usr/bin/env python3
"""Revisión visual profunda para sesión de pulido sin mutar assets de producción."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def inspect_png(path: Path) -> dict:
    with Image.open(path) as image:
        width, height = image.size
        bands = image.getbands()
    return {"path": str(path), "width": width, "height": height, "pixels": width * height, "decoded_rgba_bytes": width * height * 4, "alpha": "A" in bands, "source_bytes": path.stat().st_size}


def inspect_xml(path: Path) -> dict:
    root = ET.parse(path).getroot()
    frames = root.findall('.//SubTexture')
    prefixes = sorted({frame.attrib.get('name', '').rstrip('0123456789') for frame in frames if frame.attrib.get('name')})
    return {"path": str(path), "frames": len(frames), "prefixes": prefixes}


def review(root: Path, mod: Path) -> dict:
    pngs, xmls, issues = [], [], []
    for png in sorted(mod.rglob('*.png')):
        try:
            pngs.append(inspect_png(png))
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            issues.append({"code": "PNG_UNREADABLE", "severity": "high", "path": str(png), "detail": str(exc)})
    for xml in sorted(mod.rglob('*.xml')):
        try:
            xml_info = inspect_xml(xml)
            xmls.append(xml_info)
            if xml_info['frames'] == 0:
                issues.append({"code": "ATLAS_NO_FRAMES", "severity": "high", "path": str(xml)})
        except ET.ParseError as exc:
            issues.append({"code": "XML_INVALID", "severity": "high", "path": str(xml), "detail": str(exc)})
    character_pngs = [item for item in pngs if '/shared/images/characters/' in item['path']]
    stage_pngs = [item for item in pngs if '/shared/images/stages/' in item['path']]
    icon_pngs = [item for item in pngs if '/images/icons/' in item['path']]
    ui_pngs = [item for item in pngs if '/shared/images/ui/' in item['path']]
    if len(character_pngs) < 2:
        issues.append({"code": "CHARACTER_ASSET_COVERAGE", "severity": "high", "detail": "Se esperaban dos sprites de personaje"})
    if not stage_pngs:
        issues.append({"code": "STAGE_ASSET_COVERAGE", "severity": "high", "detail": "Falta PNG de escenario"})
    if len(icon_pngs) < 2:
        issues.append({"code": "ICON_COVERAGE", "severity": "high", "detail": "Faltan iconos de personajes"})
    # Sequential geometric atlases should offer at least several frames; detect static characters only when source atlas says so.
    character_atlases = [entry for entry in xmls if '/shared/images/characters/' in entry['path']]
    for atlas in character_atlases:
        if atlas['frames'] < 5:
            issues.append({"code": "ANIMATION_FRAME_COVERAGE", "severity": "warning", "path": atlas['path'], "detail": "Menos de cinco frames en atlas de personaje"})
    decoded = sum(item['decoded_rgba_bytes'] for item in pngs)
    source = sum(item['source_bytes'] for item in pngs)
    budget = {"decoded_rgba_bytes": decoded, "decoded_rgba_mib": round(decoded / 1024 / 1024, 3), "png_source_bytes": source, "png_source_mib": round(source / 1024 / 1024, 3)}
    if decoded > 96 * 1024 * 1024:
        issues.append({"code": "MOBILE_TEXTURE_BUDGET", "severity": "warning", "detail": "Más de 96 MiB RGBA decodificado"})
    return {
        "scope": "ACTIVE_POLISH_VISUAL_REVIEW", "mod": mod.name,
        "status": "PASS" if not issues else ("ERROR" if any(i['severity'] == 'high' for i in issues) else "WARNING"),
        "coverage": {"pngs": len(pngs), "xmls": len(xmls), "character_pngs": len(character_pngs), "stage_pngs": len(stage_pngs), "icon_pngs": len(icon_pngs), "ui_pngs": len(ui_pngs), "character_atlases": len(character_atlases)},
        "budget": budget, "atlases": xmls, "issues": issues,
        "decision": "NO_AUTOMATED_CHANGE" if not issues else "REPAIR_IF_UNIQUE_SOURCE",
        "static_render_status": "STATIC_RENDER_READY" if not any(i['severity'] == 'high' for i in issues) else "STATIC_RENDER_BLOCKED",
        "mobile_confirmation": "REQUIRED"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--mod', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    mod = root / 'mods' / args.mod
    payload = review(root, mod)
    target = root / 'qa-lab' / 'session-30min' / 'visual-animation' / f'{mod.name}-review.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({"mod": mod.name, "status": payload["status"], "issues": len(payload["issues"]), "mib": payload["budget"]["decoded_rgba_mib"]}, ensure_ascii=False))

if __name__ == '__main__':
    main()
