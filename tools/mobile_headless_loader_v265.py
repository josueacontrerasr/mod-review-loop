#!/usr/bin/env python3
"""Loader headless estático para mods FNF Mobile V-Slice 0.8.6.

No ejecuta HScript ni un APK. Copia cada mod a la ruta Android simulada y comprueba
resolución de manifests, metadata, charts, stages, personajes, note styles, levels,
PNG/XML y audio. Los resultados se guardan fuera de los ZIP runtime.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]


def read_json(path: Path, errors: list[dict[str, str]], label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            errors.append({"level": "ERROR", "code": "JSON_ROOT", "path": str(path), "detail": label})
            return {}
        return payload
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append({"level": "ERROR", "code": "JSON_INVALID", "path": str(path), "detail": f"{label}: {exc}"})
        return {}


def resolve_asset(mod: Path, asset_path: str, prefer_shared: bool = False) -> tuple[Path, Path]:
    normalized = str(asset_path).removeprefix("shared:")
    if str(asset_path).startswith("shared:") or prefer_shared:
        base = mod / "shared" / "images" / normalized
    else:
        base = mod / "images" / normalized
    return base.with_suffix(".png"), base.with_suffix(".xml")


def check_atlas(png: Path, xml: Path, errors: list[dict[str, str]], label: str) -> int:
    if not png.is_file():
        errors.append({"level": "ERROR", "code": "PNG_MISSING", "path": str(png), "detail": label})
        return 0
    if not xml.is_file():
        errors.append({"level": "ERROR", "code": "XML_MISSING", "path": str(xml), "detail": label})
        return 0
    try:
        with png.open("rb") as handle:
            header = handle.read(8)
        if header != b"\x89PNG\r\n\x1a\n":
            errors.append({"level": "ERROR", "code": "PNG_SIGNATURE", "path": str(png), "detail": label})
        root = ET.parse(xml).getroot()
        frames = root.findall(".//SubTexture")
        if not frames:
            errors.append({"level": "ERROR", "code": "ATLAS_EMPTY", "path": str(xml), "detail": label})
        return len(frames)
    except (OSError, ET.ParseError, ValueError) as exc:
        errors.append({"level": "ERROR", "code": "ATLAS_INVALID", "path": str(xml), "detail": f"{label}: {exc}"})
        return 0


def probe_audio(path: Path, errors: list[dict[str, str]], label: str) -> dict[str, Any]:
    if not path.is_file():
        errors.append({"level": "ERROR", "code": "AUDIO_MISSING", "path": str(path), "detail": label})
        return {}
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,channels,sample_rate", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        errors.append({"level": "ERROR", "code": "AUDIO_UNREADABLE", "path": str(path), "detail": result.stderr.strip() or label})
        return {}
    try:
        payload = json.loads(result.stdout)
        duration = float(payload.get("format", {}).get("duration", 0))
        streams = payload.get("streams", [])
        if duration <= 0 or not streams or streams[0].get("codec_name") != "vorbis":
            errors.append({"level": "ERROR", "code": "AUDIO_CONTRACT", "path": str(path), "detail": label})
        return {"duration_seconds": duration, "streams": streams}
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append({"level": "ERROR", "code": "AUDIO_PROBE_JSON", "path": str(path), "detail": str(exc)})
        return {}


def load_one(root: Path, song: str, sim_root: Path) -> dict[str, Any]:
    source = root / "mods" / f"esperon-dano-{song}"
    destination = sim_root / source.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    mod = destination
    meta = read_json(mod / "_polymod_meta.json", errors, "Polymod manifest")
    if meta.get("api_version") != "0.8.6":
        errors.append({"level": "ERROR", "code": "API_VERSION", "path": str(mod / "_polymod_meta.json"), "detail": str(meta.get("api_version"))})
    song_dirs = sorted((mod / "data" / "songs").glob("*"))
    if len(song_dirs) != 1 or song_dirs[0].name != song:
        errors.append({"level": "ERROR", "code": "SONG_DIRECTORY", "path": str(mod / "data" / "songs"), "detail": f"expected {song}"})
        return {"song": song, "mod": source.name, "status": "ERROR", "errors": errors, "warnings": warnings}
    song_dir = song_dirs[0]
    manifest = read_json(song_dir / "manifest.json", errors, "song manifest")
    metadata = read_json(song_dir / f"{song}-metadata.json", errors, "song metadata")
    chart = read_json(song_dir / f"{song}-chart.json", errors, "song chart")
    if manifest.get("songId") != song:
        errors.append({"level": "ERROR", "code": "SONG_ID", "path": str(song_dir / "manifest.json"), "detail": str(manifest.get("songId"))})
    if metadata.get("version") != "2.2.4":
        errors.append({"level": "ERROR", "code": "METADATA_VERSION", "path": str(song_dir), "detail": str(metadata.get("version"))})
    if chart.get("version") != "2.0.0":
        errors.append({"level": "ERROR", "code": "CHART_VERSION", "path": str(song_dir), "detail": str(chart.get("version"))})
    play = metadata.get("playData", {}) if isinstance(metadata.get("playData"), dict) else {}
    if set(play.get("difficulties", [])) != {"easy", "normal", "hard"}:
        errors.append({"level": "ERROR", "code": "DIFFICULTIES", "path": str(song_dir), "detail": "easy/normal/hard"})
    notes = chart.get("notes", {}) if isinstance(chart.get("notes"), dict) else {}
    note_counts: dict[str, int] = {}
    for difficulty in ("easy", "normal", "hard"):
        entries = notes.get(difficulty, [])
        note_counts[difficulty] = len(entries) if isinstance(entries, list) else 0
        previous = -1.0
        if not isinstance(entries, list) or not entries:
            errors.append({"level": "ERROR", "code": "NOTES_EMPTY", "path": str(song_dir), "detail": difficulty})
            continue
        for index, note in enumerate(entries):
            if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                errors.append({"level": "ERROR", "code": "NOTE_INVALID", "path": str(song_dir), "detail": f"{difficulty}[{index}]"})
                break
            timestamp = float(note["t"])
            lane = int(note["d"])
            if timestamp < previous or timestamp < 0 or lane not in (4, 5, 6, 7):
                errors.append({"level": "ERROR", "code": "NOTE_CONTRACT", "path": str(song_dir), "detail": f"{difficulty}[{index}]"})
                break
            previous = timestamp
        if {int(item.get("d", -1)) for item in entries} != {4, 5, 6, 7}:
            errors.append({"level": "ERROR", "code": "LANE_COVERAGE", "path": str(song_dir), "detail": f"{difficulty}: expected d=4,5,6,7"})
    if not (note_counts.get("easy", 0) < note_counts.get("normal", 0) <= note_counts.get("hard", 0)):
        errors.append({"level": "ERROR", "code": "DENSITY_ORDER", "path": str(song_dir), "detail": str(note_counts)})
    characters = play.get("characters", {}) if isinstance(play.get("characters"), dict) else {}
    frame_counts: dict[str, int] = {}
    for role in ("player", "opponent"):
        character_id = characters.get(role)
        char_path = mod / "data" / "characters" / f"{character_id}.json"
        char = read_json(char_path, errors, f"{role} character")
        asset = char.get("assetPath")
        if not isinstance(asset, str):
            errors.append({"level": "ERROR", "code": "CHARACTER_ASSET_PATH", "path": str(char_path), "detail": role})
            continue
        png, xml = resolve_asset(mod, asset, prefer_shared=True)
        frame_counts[role] = check_atlas(png, xml, errors, role)
        prefixes = {str(item.get("prefix")) for item in char.get("animations", []) if isinstance(item, dict)}
        xml_names: set[str] = set()
        if xml.is_file():
            try:
                xml_names = {node.attrib.get("name", "") for node in ET.parse(xml).getroot().findall(".//SubTexture")}
            except ET.ParseError:
                pass
        if prefixes and not all(any(name == prefix or name.startswith(prefix + "0") for name in xml_names) for prefix in prefixes):
            errors.append({"level": "ERROR", "code": "CHARACTER_ANIMATION_PREFIX", "path": str(xml), "detail": role})
    stage_id = play.get("stage")
    stage_path = mod / "data" / "stages" / f"{stage_id}.json"
    stage = read_json(stage_path, errors, "stage")
    if stage.get("directory") != "shared":
        errors.append({"level": "ERROR", "code": "STAGE_DIRECTORY", "path": str(stage_path), "detail": str(stage.get("directory"))})
    for prop in stage.get("props", []) if isinstance(stage.get("props"), list) else []:
        if isinstance(prop, dict) and isinstance(prop.get("assetPath"), str):
            png, _ = resolve_asset(mod, prop["assetPath"], prefer_shared=True)
            if not png.is_file():
                errors.append({"level": "ERROR", "code": "STAGE_ASSET", "path": str(png), "detail": prop["assetPath"]})
    style_id = play.get("noteStyle")
    style_path = mod / "data" / "notestyles" / f"{style_id}.json"
    style = read_json(style_path, errors, "note style")
    if style.get("version") != "1.0.0" or style.get("fallback") != "funkin":
        errors.append({"level": "ERROR", "code": "NOTE_STYLE_CONTRACT", "path": str(style_path), "detail": "version/fallback"})
    for group in ("note", "noteStrumline"):
        asset = style.get("assets", {}).get(group, {}).get("assetPath") if isinstance(style.get("assets"), dict) else None
        if isinstance(asset, str):
            png, xml = resolve_asset(mod, asset)
            check_atlas(png, xml, errors, f"note style {group}")
        else:
            errors.append({"level": "ERROR", "code": "NOTE_STYLE_ASSET_PATH", "path": str(style_path), "detail": group})
    level_paths = sorted((mod / "data" / "levels").glob("*.json"))
    if not level_paths:
        errors.append({"level": "ERROR", "code": "LEVEL_MISSING", "path": str(mod / "data" / "levels"), "detail": song})
    else:
        linked_levels = []
        for path in level_paths:
            level = read_json(path, errors, "level")
            if song not in (level.get("songs", []) or []):
                continue
            linked_levels.append(path)
            title_asset = level.get("titleAsset")
            if not isinstance(title_asset, str) or not title_asset.startswith("storymenu/"):
                errors.append({"level": "ERROR", "code": "LEVEL_TITLE_ASSET", "path": str(path), "detail": str(title_asset)})
            else:
                title_png, _ = resolve_asset(mod, title_asset)
                if not title_png.is_file():
                    errors.append({"level": "ERROR", "code": "LEVEL_TITLE_PNG", "path": str(title_png), "detail": song})
        if not linked_levels:
            errors.append({"level": "ERROR", "code": "LEVEL_LINK", "path": str(mod / "data" / "levels"), "detail": song})
    album_id = play.get("album")
    if album_id != f"esperon-{song}":
        errors.append({"level": "ERROR", "code": "ALBUM_ID", "path": str(song_dir), "detail": str(album_id)})
    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
    album = read_json(album_path, errors, "album")
    for key in ("albumArtAsset", "albumTitleAsset"):
        asset = album.get(key)
        if not isinstance(asset, str) or not asset.startswith("freeplay/albumRoll/"):
            errors.append({"level": "ERROR", "code": "ALBUM_PATH", "path": str(album_path), "detail": f"{key}: {asset}"})
            continue
        png, xml = resolve_asset(mod, asset)
        if not png.is_file():
            errors.append({"level": "ERROR", "code": "ALBUM_PNG", "path": str(png), "detail": key})
        if key == "albumTitleAsset" and not xml.is_file():
            errors.append({"level": "ERROR", "code": "ALBUM_XML", "path": str(xml), "detail": key})
    audio_dir = mod / "songs" / song
    audio = {"inst": probe_audio(audio_dir / "Inst.ogg", errors, "Inst.ogg"), "voices": {}}
    for voice in sorted(audio_dir.glob("Voices-*.ogg")):
        audio["voices"][voice.name] = probe_audio(voice, errors, voice.name)
    if not audio["voices"]:
        errors.append({"level": "ERROR", "code": "VOICES_MISSING", "path": str(audio_dir), "detail": song})
    scripts = []
    for script in sorted((mod / "scripts").glob("*.hxc")) if (mod / "scripts").is_dir() else []:
        text = script.read_text(encoding="utf-8", errors="replace")
        module_ok = bool(re.search(r"import\s+funkin\.modding\.module\.Module", text)) and bool(re.search(r"extends\s+Module", text))
        scripts.append({"path": str(script.relative_to(mod)), "module_import_ok": module_ok})
        if not module_ok:
            errors.append({"level": "ERROR", "code": "HSCRIPT_MODULE", "path": str(script), "detail": "Module import/extends"})
    warnings.append({"level": "WARNING", "code": "NO_NATIVE_ENGINE", "detail": "No se ejecutó un APK o renderer nativo; loader estático únicamente."})
    return {
        "song": song,
        "mod": source.name,
        "status": "PASS" if not errors else "ERROR",
        "errors": errors,
        "warnings": warnings,
        "simulation_path": str(destination.relative_to(root)),
        "note_counts": note_counts,
        "character_frames": frame_counts,
        "scripts": scripts,
        "audio_files": sorted(str(path.relative_to(mod)) for path in (mod / "songs" / song).glob("*.ogg")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    sim_root = root / "qa-lab" / "mobile-sim" / "storage" / "emulated" / "0" / "Android" / "data" / "com.funkin.fnf" / "files" / "mods"
    sim_root.mkdir(parents=True, exist_ok=True)
    jobs = [(root, song, sim_root) for song in SONGS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = sorted(executor.map(lambda job: load_one(*job), jobs), key=lambda row: row["song"])
    payload = {
        "scope": "HEADLESS_MOBILE_VFS_V265",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "simulation_root": str(sim_root.relative_to(root)),
        "mods": len(rows),
        "parallel_workers": max(1, args.workers),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "limitations": [
            "No ejecuta el motor nativo ni HScript; comprueba contratos y resolución estática.",
            "La latencia táctil, caché y renderizado real en Android/iOS requieren playtest del dispositivo.",
        ],
    }
    output = root / "qa-lab" / "rebuild-v265" / "mobile-loader-v265.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods": payload["mods"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
