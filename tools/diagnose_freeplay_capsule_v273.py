from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_probe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "path": str(path)}
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            bbox = alpha.getbbox()
            colors = len(rgba.resize((64, 64)).getcolors(maxcolors=1_000_000) or [])
            return {
                "exists": True,
                "path": str(path),
                "format": image.format,
                "size": list(image.size),
                "mode": image.mode,
                "alpha_bbox": list(bbox) if bbox else None,
                "nontransparent": bbox is not None,
                "sampled_colors": colors,
                "sha256": sha256(path),
            }
    except Exception as exc:
        return {"exists": True, "path": str(path), "error": str(exc)}


def resolve_asset(mod: Path, asset_key: str) -> dict[str, Any]:
    key = asset_key.removesuffix(".png")
    png = mod / "images" / f"{key}.png"
    xml = mod / "images" / f"{key}.xml"
    return {"key": asset_key, "png": image_probe(png), "xml_exists": xml.is_file(), "xml_path": str(xml)}


def audit_song(root: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    errors: list[str] = []
    song_dir = mod / "data" / "songs" / song
    metadata_path = song_dir / f"{song}-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    play = metadata.get("playData", {})
    album_id = play.get("album")

    levels = []
    for level_path in sorted((mod / "data" / "levels").glob("*.json")):
        level = json.loads(level_path.read_text(encoding="utf-8"))
        songs = level.get("songs", [])
        if song in songs:
            asset_key = level.get("titleAsset", "")
            title = resolve_asset(mod, asset_key) if asset_key else {"key": asset_key, "png": {"exists": False}, "xml_exists": False}
            row = {
                "id": level_path.stem,
                "path": str(level_path.relative_to(mod)),
                "visible": level.get("visible"),
                "songs": songs,
                "titleAsset": title,
            }
            levels.append(row)
            if not title["png"].get("exists") or not title["png"].get("nontransparent"):
                errors.append("titleAsset_png_missing_or_transparent")
            if title["png"].get("size") not in ([900, 220], [512, 256], [512, 512]):
                errors.append(f"titleAsset_unexpected_size:{title['png'].get('size')}")
    if len(levels) != 1:
        errors.append(f"level_link_count:{len(levels)}")

    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
    album: dict[str, Any] = {}
    album_assets: dict[str, Any] = {}
    if not isinstance(album_id, str) or not album_id:
        errors.append("album_id_missing")
    elif not album_path.is_file():
        errors.append("album_json_missing")
    else:
        album = json.loads(album_path.read_text(encoding="utf-8"))
        version = str(album.get("version", ""))
        if not re.fullmatch(r"1\.0\.\d+", version):
            errors.append(f"album_version_not_1.0.x:{version}")
        if album_path.stem != str(album_id):
            errors.append(f"album_filename_id_mismatch:{album_path.stem}!={album_id}")
        expected_art = f"freeplay/albumRoll/{album_id}-art"
        expected_title = f"freeplay/albumRoll/{album_id}-title"
        if album.get("albumArtAsset") != expected_art:
            errors.append(f"albumArtAsset_unexpected:{album.get('albumArtAsset')}")
        if album.get("albumTitleAsset") != expected_title:
            errors.append(f"albumTitleAsset_unexpected:{album.get('albumTitleAsset')}")
        for field in ("albumArtAsset", "albumTitleAsset"):
            key = album.get(field, "")
            album_assets[field] = resolve_asset(mod, key) if key else {"key": key, "png": {"exists": False}, "xml_exists": False}
            if not album_assets[field]["png"].get("exists") or not album_assets[field]["png"].get("nontransparent"):
                errors.append(f"{field}_png_missing_or_transparent")
        if not album_assets.get("albumTitleAsset", {}).get("xml_exists"):
            errors.append("albumTitleAsset_xml_missing")

    return {
        "song": song,
        "mod": mod.name,
        "level_count": len(levels),
        "levels": levels,
        "metadata_album": album_id,
        "album_json": str(album_path.relative_to(mod)) if album_path.is_file() else None,
        "album": album,
        "album_assets": album_assets,
        "errors": errors,
        "status": "PASS" if not errors else "ERRORS_FOUND",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    rows = [audit_song(root, song) for song in SONGS]
    payload = {
        "scope": "FREEPLAY_CAPSULE_AND_ALBUM_DIAGNOSTIC_V273",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "interpretation": "titleAsset/storymenu is audited separately from albumRoll; a passing album audit does not prove the capsule image is the one selected in Freeplay.",
    }
    output = root / "qa-lab" / "rebuild-v273" / "freeplay-capsule-diagnostic-v273.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
