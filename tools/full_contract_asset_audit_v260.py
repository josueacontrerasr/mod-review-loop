#!/usr/bin/env python3
"""Auditor paralelo de contratos, assets, descubrimiento y scripts V-Slice 0.8.6."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def load(path: Path, errors: list[dict[str, str]], label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            errors.append({"code": "JSON_ROOT", "path": str(path), "detail": label})
            return {}
        return value
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append({"code": "JSON_INVALID", "path": str(path), "detail": f"{label}: {exc}"})
        return {}


def resolve_image(mod: Path, asset: str, prefer_shared: bool = False) -> tuple[Path, Path]:
    relative = str(asset).removeprefix("shared:")
    root = mod / "shared" / "images" if (str(asset).startswith("shared:") or prefer_shared) else mod / "images"
    base = root / relative
    return base.with_suffix(".png"), base.with_suffix(".xml")


def inspect_png(path: Path, errors: list[dict[str, str]], label: str) -> dict[str, Any]:
    if not path.is_file():
        errors.append({"code": "PNG_MISSING", "path": str(path), "detail": label})
        return {}
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
            extrema = image.getextrema()
        if width <= 0 or height <= 0:
            errors.append({"code": "PNG_DIMENSIONS", "path": str(path), "detail": label})
        if width * height > 16_777_216:
            errors.append({"code": "PNG_MOBILE_BUDGET", "path": str(path), "detail": f"{width}x{height}"})
        return {"path": str(path), "width": width, "height": height, "mode": mode, "has_alpha": "A" in mode, "extrema": str(extrema), "bytes": path.stat().st_size}
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        errors.append({"code": "PNG_INVALID", "path": str(path), "detail": f"{label}: {exc}"})
        return {}


def inspect_xml(path: Path, errors: list[dict[str, str]], label: str, image_candidates: list[Path]) -> dict[str, Any]:
    if not path.is_file():
        errors.append({"code": "XML_MISSING", "path": str(path), "detail": label})
        return {}
    try:
        root = ET.parse(path).getroot()
        frames = root.findall(".//SubTexture")
        image_path = root.attrib.get("imagePath")
        image = None
        if image_path:
            for candidate in (path.parent / image_path, *image_candidates):
                if candidate.is_file():
                    image = candidate
                    break
        bounds_errors = 0
        if image:
            with Image.open(image) as texture:
                width, height = texture.size
            for frame in frames:
                try:
                    x = int(frame.attrib.get("x", "-1")); y = int(frame.attrib.get("y", "-1"))
                    w = int(frame.attrib.get("width", "-1")); h = int(frame.attrib.get("height", "-1"))
                    if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                        bounds_errors += 1
                except ValueError:
                    bounds_errors += 1
        elif frames:
            errors.append({"code": "XML_ATLAS_IMAGE_UNRESOLVED", "path": str(path), "detail": label})
        if bounds_errors:
            errors.append({"code": "XML_FRAME_BOUNDS", "path": str(path), "detail": f"{bounds_errors} frames"})
        if not frames and root.tag.endswith("TextureAtlas"):
            errors.append({"code": "XML_NO_FRAMES", "path": str(path), "detail": label})
        return {"path": str(path), "frame_count": len(frames), "image_path": image_path, "bounds_errors": bounds_errors, "frame_names": [frame.attrib.get("name", "") for frame in frames[:20]]}
    except (OSError, ET.ParseError, ValueError) as exc:
        errors.append({"code": "XML_INVALID", "path": str(path), "detail": f"{label}: {exc}"})
        return {}


def audit_one(root: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    assets: dict[str, Any] = {"png": [], "xml": [], "characters": {}, "stages": {}, "note_style": {}, "album": {}}
    manifest = load(mod / "_polymod_meta.json", errors, "Polymod manifest")
    if manifest.get("api_version") != "0.8.6":
        errors.append({"code": "API_VERSION", "path": str(mod / "_polymod_meta.json"), "detail": str(manifest.get("api_version"))})
    json_files = sorted(mod.rglob("*.json"))
    for path in json_files:
        load(path, errors, "runtime JSON")
    for path in sorted(mod.rglob("*.png")):
        assets["png"].append(inspect_png(path, errors, "runtime PNG"))
    for path in sorted(mod.rglob("*.xml")):
        assets["xml"].append(inspect_xml(path, errors, "runtime XML", [path.with_suffix(".png"), mod / "shared" / "images" / path.relative_to(mod)]))
    song_dir = mod / "data" / "songs" / song
    metadata = load(song_dir / f"{song}-metadata.json", errors, "metadata")
    chart = load(song_dir / f"{song}-chart.json", errors, "chart")
    song_manifest = load(song_dir / "manifest.json", errors, "song manifest")
    if metadata.get("version") != "2.2.4":
        errors.append({"code": "METADATA_VERSION", "path": str(song_dir), "detail": str(metadata.get("version"))})
    if chart.get("version") != "2.0.0":
        errors.append({"code": "CHART_VERSION", "path": str(song_dir), "detail": str(chart.get("version"))})
    if song_manifest.get("songId") != song:
        errors.append({"code": "SONG_ID", "path": str(song_dir / "manifest.json"), "detail": str(song_manifest.get("songId"))})
    play = metadata.get("playData", {}) if isinstance(metadata.get("playData"), dict) else {}
    characters = play.get("characters", {}) if isinstance(play.get("characters"), dict) else {}
    for role in ("player", "opponent"):
        cid = characters.get(role)
        path = mod / "data" / "characters" / f"{cid}.json"
        data = load(path, errors, f"{role} character")
        asset = data.get("assetPath")
        if not isinstance(asset, str):
            errors.append({"code": "CHARACTER_ASSET_PATH", "path": str(path), "detail": role})
            continue
        png, xml = resolve_image(mod, asset, prefer_shared=True)
        assets["characters"][role] = {"id": cid, "asset": asset, "png": inspect_png(png, errors, role), "xml": inspect_xml(xml, errors, role, [png])}
        frame_names = set(assets["characters"][role]["xml"].get("frame_names", []))
        prefixes = [str(item.get("prefix")) for item in data.get("animations", []) if isinstance(item, dict) and item.get("prefix")]
        missing = [prefix for prefix in prefixes if not any(name == prefix or name.startswith(prefix + "0") for name in frame_names)]
        if missing:
            errors.append({"code": "CHARACTER_ANIMATION_PREFIX", "path": str(xml), "detail": ",".join(missing)})
    stage_id = play.get("stage")
    stage_path = mod / "data" / "stages" / f"{stage_id}.json"
    stage = load(stage_path, errors, "stage")
    if stage.get("directory") != "shared":
        errors.append({"code": "STAGE_DIRECTORY", "path": str(stage_path), "detail": str(stage.get("directory"))})
    for index, prop in enumerate(stage.get("props", []) if isinstance(stage.get("props"), list) else []):
        if not isinstance(prop, dict) or not isinstance(prop.get("assetPath"), str):
            errors.append({"code": "STAGE_PROP_PATH", "path": str(stage_path), "detail": str(index)})
            continue
        png, xml = resolve_image(mod, prop["assetPath"], prefer_shared=True)
        assets["stages"][str(index)] = {"asset": prop["assetPath"], "png": inspect_png(png, errors, "stage prop"), "xml": inspect_xml(xml, errors, "stage prop", [png]) if xml.is_file() else None}
    style_id = play.get("noteStyle")
    style_path = mod / "data" / "notestyles" / f"{style_id}.json"
    style = load(style_path, errors, "note style")
    if style.get("version") != "1.0.0" or style.get("fallback") != "funkin":
        errors.append({"code": "NOTE_STYLE_CONTRACT", "path": str(style_path), "detail": "version/fallback"})
    for group in ("note", "noteStrumline"):
        asset = style.get("assets", {}).get(group, {}).get("assetPath") if isinstance(style.get("assets"), dict) else None
        if not isinstance(asset, str):
            errors.append({"code": "NOTE_STYLE_ASSET", "path": str(style_path), "detail": group})
            continue
        png, xml = resolve_image(mod, asset)
        assets["note_style"][group] = {"asset": asset, "png": inspect_png(png, errors, group), "xml": inspect_xml(xml, errors, group, [png])}
    album_id = play.get("album")
    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
    album = load(album_path, errors, "album")
    for key in ("albumArtAsset", "albumTitleAsset"):
        asset = album.get(key)
        if not isinstance(asset, str) or not asset.startswith("freeplay/albumRoll/"):
            errors.append({"code": "ALBUM_PATH", "path": str(album_path), "detail": f"{key}:{asset}"})
            continue
        png, xml = resolve_image(mod, asset)
        assets["album"][key] = {"asset": asset, "png": inspect_png(png, errors, key), "xml": inspect_xml(xml, errors, key, [png]) if xml.is_file() else None}
        if key == "albumTitleAsset":
            frames = set(assets["album"][key].get("xml", {}).get("frame_names", []))
            if frames and not {"idle0000", "switch0000"}.issubset(frames):
                errors.append({"code": "ALBUM_TITLE_PREFIX", "path": str(xml), "detail": "idle0000/switch0000"})
    levels = sorted((mod / "data" / "levels").glob("*.json"))
    linked = False
    for path in levels:
        level = load(path, errors, "level")
        linked = linked or song in (level.get("songs", []) or [])
        title_asset = level.get("titleAsset")
        if isinstance(title_asset, str) and not (mod / "images" / f"{title_asset}.png").is_file() and not (mod / "images" / title_asset).is_file():
            errors.append({"code": "LEVEL_TITLE_ASSET", "path": str(path), "detail": title_asset})
        for prop in level.get("props", []) if isinstance(level.get("props"), list) else []:
            if not isinstance(prop, dict) or not isinstance(prop.get("assetPath"), str):
                errors.append({"code": "LEVEL_PROP", "path": str(path), "detail": "invalid assetPath"})
                continue
            asset_path = mod / "images" / prop["assetPath"]
            if not asset_path.is_file() and not asset_path.with_suffix(".png").is_file():
                errors.append({"code": "LEVEL_PROP_ASSET", "path": str(path), "detail": prop["assetPath"]})
    if not linked:
        errors.append({"code": "LEVEL_LINK", "path": str(mod / "data" / "levels"), "detail": song})
    scripts: list[dict[str, Any]] = []
    for path in sorted((mod / "scripts").glob("*.hxc")) if (mod / "scripts").is_dir() else []:
        text = path.read_text(encoding="utf-8", errors="replace")
        import_ok = bool(re.search(r"import\s+funkin\.modding\.module\.Module", text))
        extends_ok = bool(re.search(r"extends\s+Module", text))
        timing_refs = bool(re.search(r"songOffset|timeChanges|\bchart\b|Inst\.ogg|Voices-", text, re.IGNORECASE))
        scripts.append({"path": str(path.relative_to(mod)), "import_module_ok": import_ok, "extends_module_ok": extends_ok, "timing_references": timing_refs})
        if not import_ok or not extends_ok:
            errors.append({"code": "HSCRIPT_MODULE", "path": str(path), "detail": "import/extends Module"})
        if timing_refs:
            warnings.append({"code": "HSCRIPT_TIMING_REFERENCE", "path": str(path), "detail": "Revisión manual requerida"})
    if not scripts:
        warnings.append({"code": "NO_HSCRIPT", "path": str(mod / "scripts"), "detail": "No es error si el mod no necesita scripting"})
    warnings.append({"code": "NATIVE_RENDERER_NOT_RUN", "path": str(mod), "detail": "La apariencia exacta requiere renderer/playtest"})
    return {
        "song": song,
        "mod": mod.name,
        "status": "PASS" if not errors else "ERROR",
        "errors": errors,
        "warnings": warnings,
        "json_file_count": len(json_files),
        "png_file_count": len(assets["png"]),
        "xml_file_count": len(assets["xml"]),
        "characters": assets["characters"],
        "stages": assets["stages"],
        "note_style": assets["note_style"],
        "album": assets["album"],
        "scripts": scripts,
        "discovery": {"level_count": len(levels), "song_linked": linked},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = sorted(executor.map(lambda song: audit_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "FULL_CONTRACT_ASSET_AUDIT_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "warnings": sum(len(row["warnings"]) for row in rows),
        "status": "PASS_WITH_RENDERER_LIMITATION" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "policy": "No se modifican assets, metadata, scripts ni ZIPs durante esta auditoría.",
    }
    output = root / "qa-lab" / "rebuild-v260" / "full-contract-asset-audit-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "warnings": payload["warnings"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS_WITH_RENDERER_LIMITATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
