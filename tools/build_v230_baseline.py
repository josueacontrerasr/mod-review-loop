from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

SONG_PREFIX = "esperon-dano-"
EXPECTED_DIFFICULTIES = ["easy", "normal", "hard"]
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa-lab" / "rebuild-v230"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def probe_audio(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False}
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=sample_rate,channels,codec_name",
        "-of", "json", str(path),
    ]
    try:
        raw = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
        payload = json.loads(raw)
    except Exception as exc:
        return {"exists": True, "sha256": sha256(path), "probe_error": str(exc)}
    fmt = payload.get("format", {})
    streams = payload.get("streams", [])
    stream = streams[0] if streams else {}
    return {
        "exists": True,
        "sha256": sha256(path),
        "duration_seconds": float(fmt["duration"]) if fmt.get("duration") else None,
        "sample_rate": int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        "channels": int(stream["channels"]) if stream.get("channels") else None,
        "codec": stream.get("codec_name"),
    }


def image_info(path: Path) -> dict:
    try:
        with Image.open(path) as im:
            rgba = im.convert("RGBA")
            alpha = rgba.getchannel("A")
            amin, amax = alpha.getextrema()
            return {
                "exists": True,
                "format": im.format,
                "size": list(im.size),
                "has_alpha": "A" in im.getbands(),
                "alpha_min": amin,
                "alpha_max": amax,
                "sha256": sha256(path),
            }
    except Exception as exc:
        return {"exists": True, "image_error": str(exc), "sha256": sha256(path)}


def xml_info(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False}
    try:
        root = ET.parse(path).getroot()
        frames = [x.attrib.get("name", "") for x in root.findall(".//SubTexture")]
        return {"exists": True, "frames": frames, "frame_count": len(frames)}
    except Exception as exc:
        return {"exists": True, "xml_error": str(exc)}


def chart_info(chart: dict) -> tuple[list[str], list[str], dict]:
    issues: list[str] = []
    notes = chart.get("notes", {})
    if chart.get("version") != "2.0.0":
        issues.append("chart_version_not_2.0.0")
    if list(notes) != EXPECTED_DIFFICULTIES:
        issues.append("difficulty_keys_or_order")
    summary = {}
    for difficulty in EXPECTED_DIFFICULTIES:
        items = notes.get(difficulty)
        if not isinstance(items, list):
            issues.append(f"{difficulty}_missing_or_not_list")
            continue
        pairs = []
        malformed = 0
        for note in items:
            try:
                pairs.append((round(float(note["t"]), 3), int(note["d"])))
            except Exception:
                malformed += 1
        if malformed:
            issues.append(f"{difficulty}_malformed_notes")
        if pairs != sorted(pairs):
            issues.append(f"{difficulty}_not_sorted")
        if len(pairs) != len(set(pairs)):
            issues.append(f"{difficulty}_duplicates")
        if any(t < 0 or d < 4 or d > 7 for t, d in pairs):
            issues.append(f"{difficulty}_domain")
        summary[difficulty] = {
            "count": len(pairs),
            "first_ms": pairs[0][0] if pairs else None,
            "last_ms": pairs[-1][0] if pairs else None,
            "hold_count": sum(1 for note in items if float(note.get("l", 0) or 0) > 0),
            "scroll_speed": chart.get("scrollSpeed", {}).get(difficulty),
        }
    return issues, sorted(set(notes).difference(EXPECTED_DIFFICULTIES)), summary


def audit_mod(mod: Path) -> dict:
    issues: list[str] = []
    song_id = mod.name.removeprefix(SONG_PREFIX)
    song_dirs = sorted((mod / "data" / "songs").iterdir()) if (mod / "data" / "songs").is_dir() else []
    song_dir = song_dirs[0] if song_dirs else None
    if not song_dir:
        return {"mod": mod.name, "song": song_id, "status": "ERROR", "issues": ["missing_song_directory"]}
    meta_path = song_dir / f"{song_id}-metadata.json"
    chart_path = song_dir / f"{song_id}-chart.json"
    if not meta_path.is_file():
        issues.append("missing_metadata")
    if not chart_path.is_file():
        issues.append("missing_chart")
    meta = json_load(meta_path) if meta_path.is_file() else {}
    chart = json_load(chart_path) if chart_path.is_file() else {}
    if meta.get("version") != "2.2.4":
        issues.append("metadata_version_not_2.2.4")
    play = meta.get("playData", {})
    if play.get("difficulties") != EXPECTED_DIFFICULTIES:
        issues.append("metadata_difficulties")
    chart_issues, extra_diffs, chart_summary = chart_info(chart)
    issues.extend(chart_issues)
    if extra_diffs:
        issues.append("unexpected_difficulty_keys")
    if not isinstance(meta.get("timeChanges"), list) or not meta.get("timeChanges"):
        issues.append("missing_time_changes")
    vocal_assignments = play.get("characters", {})
    if not vocal_assignments.get("playerVocals") and not vocal_assignments.get("opponentVocals"):
        issues.append("no_vocal_assignments")

    stage_id = play.get("stage")
    stage_path = mod / "data" / "stages" / f"{stage_id}.json" if stage_id else None
    stage = json_load(stage_path) if stage_path and stage_path.is_file() else {}
    if not stage_path or not stage_path.is_file():
        issues.append("missing_stage_json")
    if stage.get("directory") != "shared":
        issues.append("stage_directory_not_shared")
    if set(stage.get("characters", {})) != {"bf", "dad", "gf"}:
        issues.append("stage_character_map")
    stage_assets = []
    for prop in stage.get("props", []):
        asset = prop.get("assetPath", "")
        stage_assets.append(asset)
        if asset.startswith("shared:"):
            issues.append("stage_shared_prefix_present")
        png = mod / "shared" / "images" / (asset.removeprefix("shared:"))
        if not png.with_suffix(".png").is_file():
            issues.append("stage_asset_missing")

    characters = {}
    for role in ("player", "opponent"):
        cid = play.get("characters", {}).get(role)
        cpath = mod / "data" / "characters" / f"{cid}.json" if cid else None
        cd = json_load(cpath) if cpath and cpath.is_file() else {}
        if not cpath or not cpath.is_file():
            issues.append(f"missing_{role}_character")
            continue
        asset = cd.get("assetPath", "")
        if asset.startswith("shared:"):
            issues.append(f"{role}_shared_prefix_present")
        base = mod / "shared" / "images" / asset.removeprefix("shared:")
        frames = xml_info(base.with_suffix(".xml")).get("frames", [])
        if not base.with_suffix(".png").is_file() or not base.with_suffix(".xml").is_file():
            issues.append(f"{role}_atlas_missing")
        for anim in cd.get("animations", []):
            prefix = anim.get("prefix", "")
            if prefix and not any(frame == prefix or frame.startswith(prefix + "0") for frame in frames):
                issues.append(f"{role}_animation_prefix_{prefix}")
        characters[role] = {
            "id": cid,
            "asset_path": asset,
            "render_type": cd.get("renderType"),
            "frame_count": len(frames),
            "png": image_info(base.with_suffix(".png")),
            "xml": xml_info(base.with_suffix(".xml")),
        }

    note_style_id = play.get("noteStyle")
    style_path = mod / "data" / "notestyles" / f"{note_style_id}.json" if note_style_id else None
    style = json_load(style_path) if style_path and style_path.is_file() else {}
    if not style_path or not style_path.is_file():
        issues.append("missing_note_style")
    visual_assets = {}
    for group, spec in style.get("assets", {}).items():
        if not isinstance(spec, dict) or not spec.get("assetPath"):
            continue
        asset = spec["assetPath"]
        base = mod / "shared" / "images" / asset.removeprefix("shared:")
        visual_assets[group] = {
            "asset_path": asset,
            "png": image_info(base.with_suffix(".png")),
            "xml": xml_info(base.with_suffix(".xml")),
        }
        if group in {"note", "noteStrumline"} and not base.with_suffix(".xml").is_file():
            issues.append(f"note_style_{group}_xml_missing")

    album_id = play.get("album")
    album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json" if album_id else None
    album = json_load(album_path) if album_path and album_path.is_file() else {}
    if not album_path or not album_path.is_file():
        issues.append("missing_album_json")
    album_assets = {}
    for key in ("albumArtAsset", "albumTitleAsset"):
        value = album.get(key)
        base = mod / "images" / value if isinstance(value, str) else None
        album_assets[key] = {
            "asset_path": value,
            "png": image_info(base.with_suffix(".png")) if base else {"exists": False},
            "xml": xml_info(base.with_suffix(".xml")) if base else {"exists": False},
        }
        if not base or not base.with_suffix(".png").is_file():
            issues.append(f"{key}_png_missing")
        if key == "albumTitleAsset":
            frames = album_assets[key]["xml"].get("frames", [])
            if not base or not base.with_suffix(".xml").is_file():
                issues.append("album_title_xml_missing")
            elif not any(f.startswith("idle0") for f in frames) or not any(f.startswith("switch0") for f in frames):
                issues.append("album_title_prefixes")

    audio_dir = mod / "songs" / song_id
    audio = {"instrumental": probe_audio(audio_dir / "Inst.ogg"), "vocals": {p.name: probe_audio(p) for p in sorted(audio_dir.glob("Voices-*.ogg"))}}
    if not audio["instrumental"].get("exists"):
        issues.append("missing_instrumental")
    if not audio["vocals"]:
        issues.append("missing_vocals")

    files = [p for p in mod.rglob("*") if p.is_file()]
    return {
        "mod": mod.name,
        "song": song_id,
        "status": "PASS" if not issues else "ERROR",
        "issues": sorted(set(issues)),
        "file_count": len(files),
        "metadata": {"version": meta.get("version"), "difficulties": play.get("difficulties"), "time_changes": meta.get("timeChanges"), "stage": stage_id, "note_style": note_style_id, "album": album_id},
        "chart": chart_summary,
        "stage": {"id": stage_id, "directory": stage.get("directory"), "characters": stage.get("characters"), "assets": stage_assets},
        "characters": characters,
        "note_style": visual_assets,
        "album": album_assets,
        "audio": audio,
    }


def main() -> None:
    mods = sorted((ROOT / "mods").glob(f"{SONG_PREFIX}*"))
    rows = [audit_mod(mod) for mod in mods if mod.is_dir()]
    payload = {
        "version": "2.3.0-baseline",
        "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "mods": len(rows),
        "status": "PASS" if len(rows) == 20 and all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "baseline-audit-v230.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "mods": len(rows), "pass": sum(r["status"] == "PASS" for r in rows), "output": str(OUT / "baseline-audit-v230.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
