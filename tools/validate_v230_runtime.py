from __future__ import annotations

import concurrent.futures
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def image_info(path: Path):
    if not path.is_file():
        return None
    try:
        with Image.open(path) as im:
            return {"size": list(im.size), "mode": im.mode, "has_alpha": "A" in im.getbands()}
    except Exception as exc:
        return {"error": str(exc)}


def atlas_info(mod: Path, asset: str):
    if not isinstance(asset, str):
        return None, []
    relative = asset.removeprefix("shared:")
    base = mod / "shared" / "images" / relative
    png, xml = base.with_suffix(".png"), base.with_suffix(".xml")
    frames = []
    xml_error = None
    if xml.is_file():
        try:
            frames = [node.attrib.get("name", "") for node in ET.parse(xml).getroot().findall(".//SubTexture")]
        except Exception as exc:
            xml_error = str(exc)
    return {"png": png.is_file(), "xml": xml.is_file(), "frames": frames, "xml_error": xml_error, "png_info": image_info(png), "xml_path": str(xml.relative_to(mod))}, frames


def check_prefix(prefix: str, frames: list[str]) -> bool:
    return bool(prefix) and any(frame == prefix or frame.startswith(prefix + "0") for frame in frames)


def one(root: Path, song: str) -> dict:
    mod = root / "mods" / f"esperon-dano-{song}"
    issues = []
    details = {}
    manifest_path = mod / "_polymod_meta.json"
    if not manifest_path.is_file():
        issues.append("missing_manifest")
    else:
        manifest = read_json(manifest_path)
        if manifest.get("api_version") != "0.8.6":
            issues.append("api_version")
        if manifest.get("mod_version") != "2.3.0":
            issues.append("mod_version")
    song_dirs = list((mod / "data" / "songs").glob("*"))
    if len(song_dirs) != 1:
        issues.append("song_directory_count")
        return {"song": song, "status": "ERROR", "issues": issues}
    song_dir = song_dirs[0]
    meta_path = song_dir / f"{song}-metadata.json"
    chart_path = song_dir / f"{song}-chart.json"
    if not meta_path.is_file() or not chart_path.is_file():
        issues.append("missing_song_json")
        return {"song": song, "status": "ERROR", "issues": issues}
    meta, chart = read_json(meta_path), read_json(chart_path)
    play = meta.get("playData", {})
    if play.get("stage") != f"escenario-{song}":
        issues.append("metadata_stage_mismatch")
    if chart.get("version") != "2.0.0":
        issues.append("chart_version")
    diffs = list(chart.get("notes", {}).keys())
    if set(diffs) != {"easy", "normal", "hard"}:
        issues.append("difficulty_set")
    if not (chart.get("scrollSpeed", {}).get("easy", 0) < chart.get("scrollSpeed", {}).get("normal", 0) < chart.get("scrollSpeed", {}).get("hard", 0)):
        issues.append("scroll_speed_order")
    notes_summary = {}
    for difficulty in ("easy", "normal", "hard"):
        notes = chart.get("notes", {}).get(difficulty, [])
        keys = [(round(float(note.get("t", -1)), 3), int(note.get("d", -1))) for note in notes]
        if keys != sorted(keys):
            issues.append(f"{difficulty}_not_sorted")
        if len(keys) != len(set(keys)):
            issues.append(f"{difficulty}_duplicates")
        if any(t < 0 or d < 4 or d > 7 for t, d in keys):
            issues.append(f"{difficulty}_note_domain")
        if not notes:
            issues.append(f"{difficulty}_empty")
        notes_summary[difficulty] = {"count": len(notes), "first": keys[0][0] if keys else None, "last": keys[-1][0] if keys else None}
    stage_id = play.get("stage")
    stage_path = mod / "data" / "stages" / f"{stage_id}.json"
    stage = read_json(stage_path) if stage_path.is_file() else None
    if not stage:
        issues.append("missing_stage_json")
    else:
        if stage.get("directory") != "shared":
            issues.append("stage_directory")
        if set(stage.get("characters", {})) != {"bf", "dad", "gf"}:
            issues.append("stage_character_map")
        for prop in stage.get("props", []):
            asset = prop.get("assetPath", "")
            if asset.startswith("shared:"):
                issues.append("stage_shared_prefix")
            png = mod / "shared" / "images" / asset
            if not png.with_suffix(".png").is_file():
                issues.append("stage_asset_missing")
    characters = {}
    for role in ("player", "opponent"):
        cid = play.get("characters", {}).get(role)
        char_path = mod / "data" / "characters" / f"{cid}.json"
        char = read_json(char_path) if char_path.is_file() else None
        if not char:
            issues.append(f"missing_{role}_character")
            continue
        asset = char.get("assetPath", "")
        if asset.startswith("shared:"):
            issues.append(f"{role}_shared_prefix")
        info, frames = atlas_info(mod, asset)
        if not info or not info["png"] or not info["xml"] or info.get("xml_error"):
            issues.append(f"{role}_atlas")
        for animation in char.get("animations", []):
            if not check_prefix(animation.get("prefix", ""), frames):
                issues.append(f"{role}_prefix_{animation.get('prefix')}")
        characters[role] = {"id": cid, "frame_count": len(frames), "png": info.get("png") if info else False}
    style_id = play.get("noteStyle")
    style_path = mod / "data" / "notestyles" / f"{style_id}.json"
    style = read_json(style_path) if style_path.is_file() else None
    if not style:
        issues.append("missing_note_style")
    else:
        for group in ("note", "noteStrumline"):
            asset = style.get("assets", {}).get(group, {}).get("assetPath")
            info, frames = atlas_info(mod, asset)
            if not info or not info["png"] or not info["xml"] or info.get("xml_error"):
                issues.append(f"note_{group}_atlas")
            for spec in style.get("assets", {}).get(group, {}).get("data", {}).values():
                if isinstance(spec, dict) and not check_prefix(spec.get("prefix", ""), frames):
                    issues.append(f"note_{group}_prefix_{spec.get('prefix')}")
    album_id = play.get("album")
    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
    album = read_json(album_path) if album_path.is_file() else None
    if not album:
        issues.append("missing_album_json")
    else:
        for key in ("albumArtAsset", "albumTitleAsset"):
            asset = album.get(key)
            base = mod / "images" / asset if isinstance(asset, str) else None
            if not base or not base.with_suffix(".png").is_file():
                issues.append(f"{key}_png")
            if key == "albumTitleAsset":
                xml = base.with_suffix(".xml") if base else None
                if not xml or not xml.is_file():
                    issues.append("album_title_xml")
                else:
                    try:
                        frames = [node.attrib.get("name", "") for node in ET.parse(xml).getroot().findall(".//SubTexture")]
                        if "idle0000" not in frames or "switch0000" not in frames:
                            issues.append("album_title_prefixes")
                    except Exception:
                        issues.append("album_title_xml_invalid")
    audio_dir = mod / "songs" / song
    if not (audio_dir / "Inst.ogg").is_file():
        issues.append("missing_inst")
    if not sorted(audio_dir.glob("Voices-*.ogg")):
        issues.append("missing_voices")
    details.update({"stage": stage_id, "characters": characters, "noteStyle": style_id, "album": album_id, "notes": notes_summary, "audio": {"inst": (audio_dir / "Inst.ogg").is_file(), "voices": [p.name for p in sorted(audio_dir.glob("Voices-*.ogg"))]}})
    return {"song": song, "status": "PASS" if not issues else "ERROR", "issues": issues, **details}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        rows = sorted(list(executor.map(lambda song: one(root, song), SONGS)), key=lambda item: item["song"])
    payload = {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "version": "2.3.0", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "rows": rows, "runtime_limit": "Static contract/resolution check; native mobile playtest still required."}
    output = root / "qa-lab" / "rebuild-v230" / "runtime-contract-v230.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "songs": len(rows), "passed": payload["passed"], "errors": len(rows) - payload["passed"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
