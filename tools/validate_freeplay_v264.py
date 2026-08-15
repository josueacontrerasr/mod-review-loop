#!/usr/bin/env python3
"""Validate V-Slice 0.8.6 Freeplay album and Story discovery contracts for V2.6.4."""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image


def resolve(root: Path, asset: str, prefer: str | None = None) -> Path:
    if asset.startswith("shared:"):
        base = root / "shared/images" / asset.removeprefix("shared:")
    elif asset.startswith("library:"):
        base = root / "images" / asset.removeprefix("library:")
    else:
        base = root / "images" / asset
    if prefer == "png": return base.with_suffix(".png")
    if prefer == "xml": return base.with_suffix(".xml")
    return base


def inspect_album(mod: Path, errors: list[str], warnings: list[str]) -> dict:
    song = next((mod / "data/songs").iterdir()).name
    metadata = json.loads((mod / f"data/songs/{song}/{song}-metadata.json").read_text())
    album_id = metadata["playData"]["album"]
    path = mod / f"data/ui/freeplay/albums/{album_id}.json"
    data = json.loads(path.read_text())
    art_asset = data.get("albumArtAsset")
    title_asset = data.get("albumTitleAsset")
    art_png = resolve(mod, art_asset, "png")
    title_png = resolve(mod, title_asset, "png")
    title_xml = resolve(mod, title_asset, "xml")
    if not art_png.is_file(): errors.append(f"album art missing: {art_asset}")
    if not title_png.is_file(): errors.append(f"album title PNG missing: {title_asset}")
    title_report = {"asset": title_asset, "png": str(title_png.relative_to(mod)), "xml": str(title_xml.relative_to(mod)), "frames": [], "errors": []}
    if not title_xml.is_file():
        errors.append(f"album title Sparrow XML missing: {title_asset}")
        return {"id": album_id, "art_asset": art_asset, "title": title_report, "status": "ERROR"}
    try:
        with Image.open(title_png) as im: width, height = im.size
        root = ET.parse(title_xml).getroot()
        if root.attrib.get("imagePath") != title_png.name:
            title_report["errors"].append(f"imagePath={root.attrib.get('imagePath')} expected={title_png.name}")
        names = [node.attrib.get("name", "") for node in root.findall(".//SubTexture")]
        title_report["frames"] = names
        if not any(name.startswith("idle0") for name in names): title_report["errors"].append("missing idle0 prefix")
        if not any(name.startswith("switch0") for name in names): title_report["errors"].append("missing switch0 prefix")
        for node in root.findall(".//SubTexture"):
            a = node.attrib
            x, y, w, h = [int(a.get(k, -1)) for k in ("x", "y", "width", "height")]
            if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                title_report["errors"].append(f"title frame out of bounds: {a.get('name')}")
    except Exception as exc:
        title_report["errors"].append(f"title atlas parse failed: {exc}")
    if title_report["errors"]: errors.extend(f"album {album_id}: {item}" for item in title_report["errors"])
    return {"id": album_id, "art_asset": art_asset, "art_png": str(art_png.relative_to(mod)), "title": title_report, "status": "PASS" if not title_report["errors"] and art_png.is_file() else "ERROR"}


def inspect_character(mod: Path, char_id: str, errors: list[str]) -> dict:
    path = mod / f"data/characters/{char_id}.json"
    data = json.loads(path.read_text())
    asset = data.get("assetPath", "")
    png = resolve(mod, asset, "png")
    xml = resolve(mod, asset, "xml")
    report = {"id": char_id, "assetPath": asset, "png": str(png.relative_to(mod)), "xml": str(xml.relative_to(mod)), "frames": [], "errors": []}
    if not png.is_file() or not xml.is_file(): report["errors"].append("Sparrow PNG/XML missing")
    if data.get("renderType") != "sparrow": report["errors"].append(f"renderType={data.get('renderType')}")
    try:
        with Image.open(png) as im: width, height = im.size
        atlas = ET.parse(xml).getroot(); names = [x.attrib.get("name", "") for x in atlas.findall(".//SubTexture")]
        report["frames"] = names
        if atlas.attrib.get("imagePath") != png.name: report["errors"].append("atlas imagePath does not match PNG")
        for node in atlas.findall(".//SubTexture"):
            a=node.attrib; x,y,w,h=[int(a.get(k,-1)) for k in ("x","y","width","height")]
            if min(x,y,w,h)<0 or x+w>width or y+h>height: report["errors"].append(f"frame out of bounds: {a.get('name')}")
        for anim in data.get("animations", []):
            prefix = anim.get("prefix", "")
            if not any(n.startswith(prefix) for n in names): report["errors"].append(f"missing animation prefix: {prefix}")
        if not any(n.startswith("Idle") for n in names): report["errors"].append("missing Idle frames")
    except Exception as exc: report["errors"].append(f"atlas parse failed: {exc}")
    if report["errors"]: errors.extend(f"character {char_id}: {item}" for item in report["errors"])
    return report


def inspect_stage(mod: Path, stage_id: str, errors: list[str]) -> dict:
    path = mod / f"data/stages/{stage_id}.json"; data = json.loads(path.read_text())
    report = {"id": stage_id, "props": [], "errors": []}
    for prop in data.get("props", []):
        asset = prop.get("assetPath", "")
        png = resolve(mod, asset, "png")
        item = {"assetPath": asset, "png": str(png.relative_to(mod)), "errors": []}
        if not png.is_file(): item["errors"].append("static stage PNG missing")
        if len(prop.get("position", [])) != 2: item["errors"].append("position must have 2 values")
        if len(prop.get("scale", [])) != 2 and not isinstance(prop.get("scale"), (int,float)): item["errors"].append("scale invalid")
        if item["errors"]: report["errors"].extend(item["errors"])
        report["props"].append(item)
    if not report["props"]: report["errors"].append("stage has no props")
    if report["errors"]: errors.extend(f"stage {stage_id}: {item}" for item in report["errors"])
    return report


def inspect_mod(mod: Path) -> dict:
    errors: list[str] = []; warnings: list[str] = []
    song = next((mod / "data/songs").iterdir()).name
    meta = json.loads((mod / f"data/songs/{song}/{song}-metadata.json").read_text())
    play = meta.get("playData", {})
    album_report = inspect_album(mod, errors, warnings)
    level_paths = list((mod / "data/levels").glob("*.json"))
    level_links = []
    for path in level_paths:
        data = json.loads(path.read_text())
        if song in data.get("songs", []) and data.get("visible") is not False: level_links.append(path.name)
    if not level_links: errors.append("no visible Story Mode level links song")
    chart = json.loads((mod / f"data/songs/{song}/{song}-chart.json").read_text())
    for diff in play.get("difficulties", []):
        if not chart.get("notes", {}).get(diff): errors.append(f"difficulty empty: {diff}")
    return {"mod": mod.name, "song": song, "status": "PASS" if not errors else "ERROR", "errors": errors, "warnings": warnings, "album": album_report, "story_levels": level_links}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    mods = sorted((root / "mods").glob("esperon-dano-*"))
    reports = [inspect_mod(mod) for mod in mods]
    payload = {"audit": "FREEPLAY_RUNTIME_V264", "target": "FNF Mobile V-Slice 0.8.6", "mods": len(reports), "passed": sum(r["status"] == "PASS" for r in reports), "errors": sum(len(r["errors"]) for r in reports), "status": "PASS" if len(reports) == 21 and all(r["status"] == "PASS" for r in reports) else "ERRORS_FOUND", "reports": reports}
    out = root / "qa-lab/rebuild-v264/freeplay-runtime-audit-v264.json"; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": payload["status"], "mods": payload["mods"], "passed": payload["passed"], "errors": payload["errors"], "output": str(out)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1

if __name__ == "__main__": raise SystemExit(main())
