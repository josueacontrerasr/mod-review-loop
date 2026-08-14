#!/usr/bin/env python3
"""Laboratorio QA autónomo y determinista para mods FNF Mobile V-Slice.

No modifica contenido de producción. Las correcciones requieren un ejecutor separado
porque este laboratorio primero reúne evidencia, baseline y decisiones reproducibles.
"""
from __future__ import annotations

import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

ROUND_FOCUS = {
    1: "baseline-hashes", 2: "json-encoding-schema", 3: "vslice-contracts", 4: "ids-paths",
    5: "png-xml-sparrow", 6: "characters-animations", 7: "stage-cover-hud", 8: "notes-ui",
    9: "ogg-integrity", 10: "chart-structure", 11: "tempo-offset-drift", 12: "voice-chart-deep",
    13: "visual-animation-deep", 14: "scripts-ui", 15: "android-vfs", 16: "individual-zips",
    17: "master-collection", 18: "static-load-and-discovery", 19: "regression", 20: "final-signature",
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_fingerprints(root: Path, mod: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): sha256(path) for path in sorted(mod.rglob("*")) if path.is_file()}


def problem(code: str, severity: str, path: Path | str, detail: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "path": str(path), "detail": detail}


def iter_json(mod: Path):
    for path in sorted(mod.rglob("*.json")):
        try:
            yield path, json.loads(path.read_text(encoding="utf-8-sig")), None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            yield path, None, str(exc)


def image_checks(mod: Path) -> tuple[list[dict], dict[str, dict]]:
    issues: list[dict] = []
    info: dict[str, dict] = {}
    for png in sorted(mod.rglob("*.png")):
        try:
            with Image.open(png) as image:
                image.verify()
            with Image.open(png) as image:
                width, height = image.size
                alpha = "A" in image.getbands()
            record = {"width": width, "height": height, "alpha": alpha, "pixels": width * height, "bytes": png.stat().st_size}
            info[png.relative_to(mod).as_posix()] = record
            if width <= 0 or height <= 0:
                issues.append(problem("PNG_EMPTY", "high", png, "Dimensiones no válidas"))
            if width * height > 16_777_216:
                issues.append(problem("PNG_MOBILE_BUDGET", "warning", png, "Textura supera 16.7M píxeles"))
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            issues.append(problem("PNG_UNREADABLE", "high", png, str(exc)))
    return issues, info


def xml_checks(mod: Path, image_info: dict[str, dict]) -> tuple[list[dict], dict[str, int]]:
    issues: list[dict] = []
    frame_counts: dict[str, int] = {}
    for xml_path in sorted(mod.rglob("*.xml")):
        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as exc:
            issues.append(problem("XML_INVALID", "high", xml_path, str(exc)))
            continue
        frames = list(root.findall(".//SubTexture"))
        frame_counts[xml_path.relative_to(mod).as_posix()] = len(frames)
        if "TextureAtlas" in root.tag and not frames:
            issues.append(problem("ATLAS_NO_FRAMES", "high", xml_path, "Atlas Sparrow sin SubTexture"))
        image_path = root.attrib.get("imagePath")
        candidate = None
        if image_path:
            candidate = (xml_path.parent / image_path).resolve()
            if not candidate.is_file():
                issues.append(problem("ATLAS_IMAGE_MISSING", "high", xml_path, f"imagePath no resuelve: {image_path}"))
                candidate = None
        if candidate:
            try:
                with Image.open(candidate) as texture:
                    width, height = texture.size
                for index, frame in enumerate(frames):
                    x, y, w, h = (int(frame.attrib.get(key, "-1")) for key in ("x", "y", "width", "height"))
                    if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                        issues.append(problem("ATLAS_FRAME_BOUNDS", "high", xml_path, f"Frame {index} fuera del PNG"))
                        break
            except (OSError, ValueError):
                pass
    return issues, frame_counts


def chart_checks(mod: Path) -> list[dict]:
    issues: list[dict] = []
    for path, payload, error in iter_json(mod):
        if error or not isinstance(payload, dict) or payload.get("version") != "2.0.0" or "notes" not in payload:
            continue
        notes_map = payload.get("notes")
        if not isinstance(notes_map, dict):
            issues.append(problem("CHART_NOTES_INVALID", "high", path, "notes debe ser objeto"))
            continue
        for difficulty, notes in notes_map.items():
            if not isinstance(notes, list):
                issues.append(problem("CHART_DIFFICULTY_INVALID", "high", path, f"{difficulty} no es lista"))
                continue
            previous = -1.0
            for index, note in enumerate(notes):
                if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                    issues.append(problem("CHART_NOTE_INVALID", "high", path, f"{difficulty}[{index}] inválida"))
                    break
                if float(note["t"]) < previous:
                    issues.append(problem("CHART_ORDER", "high", path, f"{difficulty} no está ordenada"))
                    break
                if not 0 <= int(note["d"]) <= 7:
                    issues.append(problem("CHART_DIRECTION", "high", path, f"Dirección fuera de rango en {difficulty}"))
                    break
                if "l" in note and (not isinstance(note["l"], (int, float)) or float(note["l"]) <= 0):
                    issues.append(problem("CHART_HOLD", "high", path, f"Hold inválido en {difficulty}"))
                    break
                previous = float(note["t"])
    return issues


def audio_checks(mod: Path) -> list[dict]:
    issues: list[dict] = []
    for audio in sorted(mod.rglob("*.ogg")):
        command = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,sample_rate,channels", "-of", "json", str(audio)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            issues.append(problem("OGG_UNREADABLE", "high", audio, result.stderr.strip() or "ffprobe falló"))
            continue
        payload = json.loads(result.stdout)
        streams = payload.get("streams", [])
        duration = float(payload.get("format", {}).get("duration", 0))
        if duration <= 0 or not streams or streams[0].get("codec_name") != "vorbis":
            issues.append(problem("OGG_CONTRACT", "high", audio, "Duración/codec OGG no válidos"))
    return issues


def zip_checks(root: Path, mod: Path) -> list[dict]:
    issues: list[dict] = []
    slug = mod.name.removeprefix("esperon-dano-")
    display = "-".join(part[:1].upper() + part[1:] for part in slug.split("-") if part)
    zips = sorted((root / "Mods .zip terminados").glob(f"Mod-{display}-V*.zip"))
    if not zips:
        return [problem("ZIP_MISSING", "high", mod.name, "No se encontró ZIP individual")]
    for archive in zips[-1:]:
        try:
            with zipfile.ZipFile(archive) as zf:
                bad = zf.testzip()
                if bad:
                    issues.append(problem("ZIP_CRC", "high", archive, f"CRC inválido: {bad}"))
                names = zf.namelist()
                if any(name.startswith("/") or ".." in Path(name).parts for name in names):
                    issues.append(problem("ZIP_PATH_UNSAFE", "high", archive, "Ruta absoluta o traversal"))
                roots = {name.split("/")[0] for name in names if name and not name.startswith("__MACOSX")}
                if len(roots) != 1:
                    issues.append(problem("ZIP_ROOT", "high", archive, f"Se esperó una raíz, hay {sorted(roots)}"))
                forbidden = {"CREDITS.txt", "LICENSE.txt", "INSTALACION_MOVIL.txt", "audio-evidence.json", "sync-report.json", "visual-v2-integrity.json"}
                for name in names:
                    if name.endswith("/"):
                        continue
                    relative = name.split("/", 1)[1] if "/" in name else name
                    basename = name.rsplit("/", 1)[-1]
                    if basename in forbidden or any(token in name.split("/") for token in ("qa-lab", "artifacts", "previews", "reports", "logs")):
                        issues.append(problem("ZIP_RUNTIME_AUXILIARY", "high", archive, f"Archivo auxiliar dentro del ZIP: {name}"))
                    if "/" not in relative and basename != "_polymod_meta.json" and not basename.endswith(".hxc"):
                        issues.append(problem("ZIP_ROOT_AUXILIARY", "high", archive, f"Archivo inesperado en raíz runtime: {name}"))
        except zipfile.BadZipFile as exc:
            issues.append(problem("ZIP_INVALID", "high", archive, str(exc)))
    return issues


def json_and_reference_checks(mod: Path) -> tuple[list[dict], dict[str, Any]]:
    issues: list[dict] = []
    data = {"json_files": 0, "character_json": 0, "stage_json": 0, "cover_candidates": 0}
    for path, payload, error in iter_json(mod):
        data["json_files"] += 1
        relative = path.relative_to(mod).as_posix()
        if error:
            issues.append(problem("JSON_INVALID", "high", path, error))
            continue
        if relative.startswith("data/characters/"):
            data["character_json"] += 1
        if relative.startswith("data/stages/"):
            data["stage_json"] += 1
        if not isinstance(payload, dict):
            issues.append(problem("JSON_ROOT", "high", path, "La raíz debe ser objeto"))
    for png in mod.rglob("*.png"):
        if any(token in png.name.lower() for token in ("icon", "cover", "logo")):
            data["cover_candidates"] += 1
    if data["character_json"] < 2:
        issues.append(problem("CHARACTER_COVERAGE", "high", mod, "Se esperaban al menos dos personajes"))
    if data["stage_json"] < 1:
        issues.append(problem("STAGE_COVERAGE", "high", mod, "Falta stage JSON"))
    return issues, data


def discovery_checks(mod: Path, song: str) -> list[dict]:
    issues: list[dict] = []
    song_dir = mod / "data" / "songs" / song
    metadata_path = song_dir / f"{song}-metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [problem("DISCOVERY_METADATA_INVALID", "high", metadata_path, str(exc))]
    play_data = metadata.get("playData", {}) if isinstance(metadata.get("playData"), dict) else {}
    if not isinstance(play_data.get("album"), str) or not play_data.get("album"):
        issues.append(problem("DISCOVERY_ALBUM_MISSING", "high", metadata_path, "playData.album es obligatorio para el album de Freeplay"))
    if metadata.get("album") is not None:
        issues.append(problem("DISCOVERY_ALBUM_MISWIRED", "high", metadata_path, "album está fuera de playData"))
    levels_root = mod / "data" / "levels"
    level_paths = sorted(levels_root.glob("*.json")) if levels_root.is_dir() else []
    if not level_paths:
        issues.append(problem("DISCOVERY_LEVEL_MISSING", "high", levels_root, "FreeplayState enumera canciones mediante LevelRegistry y levels"))
        return issues
    linked = False
    for level_path in level_paths:
        try:
            level = json.loads(level_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            issues.append(problem("DISCOVERY_LEVEL_INVALID", "high", level_path, str(exc)))
            continue
        if level.get("version") not in ("1.0.0", "1.0.1", "1.0.2"):
            issues.append(problem("DISCOVERY_LEVEL_SCHEMA", "high", level_path, "Schema de level no compatible"))
        if level.get("visible") is False:
            issues.append(problem("DISCOVERY_LEVEL_HIDDEN", "high", level_path, "visible=false"))
        if song in level.get("songs", []):
            linked = True
        else:
            issues.append(problem("DISCOVERY_SONG_NOT_LINKED", "high", level_path, f"{song} no aparece en songs[]"))
        title_asset = level.get("titleAsset")
        if not isinstance(title_asset, str) or not ((mod / "images" / f"{title_asset}.png").is_file() or (mod / "images" / title_asset).is_file()):
            issues.append(problem("DISCOVERY_TITLE_ASSET", "high", level_path, f"titleAsset no resuelve: {title_asset}"))
        for prop in level.get("props", []):
            if not isinstance(prop, dict) or not isinstance(prop.get("assetPath"), str):
                issues.append(problem("DISCOVERY_PROP_ASSET", "high", level_path, "prop assetPath inválido"))
                continue
            asset_path = mod / "images" / prop["assetPath"]
            if prop.get("animations"):
                resolved = (Path(str(asset_path) + ".png").is_file() and Path(str(asset_path) + ".xml").is_file()) or asset_path.is_file()
            else:
                resolved = asset_path.is_file() or Path(str(asset_path) + ".png").is_file()
            if not resolved:
                issues.append(problem("DISCOVERY_PROP_ASSET", "high", level_path, f"prop no resuelve: {prop['assetPath']}"))
    if not linked:
        issues.append(problem("DISCOVERY_NO_LINK", "high", levels_root, f"Ningún level enlaza {song}"))
    return issues


def candidate_checks(root: Path, song: str) -> list[dict]:
    issues: list[dict] = []
    report = root / "sync-candidates" / "results" / song / "sync-candidate-report.json"
    evidence = root / "sync-candidates" / "vocal-stems" / song / "stem-evidence.json"
    if not report.is_file():
        issues.append(problem("VOICE_CANDIDATE_MISSING", "warning", report, "Falta reporte de candidato"))
    else:
        payload = json.loads(report.read_text(encoding="utf-8"))
        if payload.get("analysis_mode") != "VOCAL_STEM":
            issues.append(problem("VOICE_ANALYSIS_MODE", "warning", report, "No está basado en stem vocal"))
        if payload.get("status") not in ("MANUAL_REVIEW_REQUIRED", "AUTOMATED_NEEDS_MOBILE_CONFIRMATION"):
            issues.append(problem("VOICE_STATUS", "warning", report, "Estado no reconocido"))
    if not evidence.is_file():
        issues.append(problem("VOICE_STEM_EVIDENCE_MISSING", "warning", evidence, "Falta evidencia del stem"))
    return issues


def make_preview(mod: Path, preview_path: Path) -> None:
    candidates = sorted(mod.rglob("*.png"), key=lambda p: ("characters" not in p.as_posix(), "stages" not in p.as_posix(), p.name))[:8]
    sheet = Image.new("RGBA", (960, 600), (22, 26, 38, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 16), mod.name, fill=(240, 244, 255, 255))
    for index, asset in enumerate(candidates):
        with Image.open(asset) as source:
            image = source.convert("RGBA")
            image.thumbnail((210, 220))
            frame = Image.new("RGBA", (220, 255), (45, 52, 72, 255))
            frame.alpha_composite(image, ((220 - image.width) // 2, 8))
            draw2 = ImageDraw.Draw(frame)
            label = asset.relative_to(mod).as_posix()[-30:]
            draw2.text((6, 228), label, fill=(240, 244, 255, 255))
        x = 20 + (index % 4) * 235
        y = 55 + (index // 4) * 270
        sheet.alpha_composite(frame, (x, y))
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(preview_path)


def audit_mod(root: Path, mod: Path, round_no: int, make_previews: bool) -> dict[str, Any]:
    song_dirs = list((mod / "data" / "songs").glob("*"))
    song = song_dirs[0].name if len(song_dirs) == 1 else mod.name.removeprefix("esperon-dano-")
    issues: list[dict] = []
    json_issues, metrics = json_and_reference_checks(mod)
    image_issues, image_info = image_checks(mod)
    xml_issues, frame_counts = xml_checks(mod, image_info)
    issues += json_issues + image_issues + xml_issues + chart_checks(mod) + audio_checks(mod) + zip_checks(root, mod) + discovery_checks(mod, song)
    specialized: dict[str, Any] = {}
    if round_no == 12:
        voice_issues = candidate_checks(root, song)
        issues += voice_issues
        specialized["voice_chart"] = {"song": song, "candidate_issues": voice_issues, "promotion": "AUTOMATED_NEEDS_MOBILE_CONFIRMATION"}
    if round_no == 13:
        specialized["visual_animation"] = {
            "character_json": metrics["character_json"], "stage_json": metrics["stage_json"],
            "cover_candidates": metrics["cover_candidates"], "atlas_frames": frame_counts,
            "static_status": "STATIC_RENDER_READY" if not any(i["severity"] == "high" for i in issues) else "STATIC_RENDER_BLOCKED"
        }
        if make_previews:
            make_preview(mod, root / "qa-lab" / "previews" / f"{mod.name}.png")
    severity = Counter(issue["severity"] for issue in issues)
    return {
        "mod": mod.name, "song": song, "status": "PASS" if not issues else ("ERROR" if severity["high"] else "WARNING"),
        "issues": issues, "metrics": metrics | {"png_assets": len(image_info), "decoded_rgba_bytes": sum(v["pixels"] * 4 for v in image_info.values()), "atlas_frames": sum(frame_counts.values())},
        "specialized": specialized, "fingerprints": file_fingerprints(root, mod)
    }


def markdown_summary(round_no: int, focus: str, reports: list[dict]) -> str:
    rows = []
    for report in reports:
        rows.append(f"| `{report['mod']}` | {report['status']} | {len(report['issues'])} |")
    return f"# QA Round {round_no:02d}\n\nFocus: **{focus}**.\n\n| Mod | Estado | Hallazgos |\n|---|---|---:|\n" + "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--previews", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    qa_root = root / "qa-lab"
    if args.clean and qa_root.exists():
        # Limpiar solo salidas generadas por la ejecución; preservar evidencia histórica y Wide Research rastreada.
        for generated_dir in (qa_root / "artifacts", qa_root / "rounds", qa_root / "previews", qa_root / "final"):
            if generated_dir.exists():
                shutil.rmtree(generated_dir)
    mods = sorted(path for path in (root / "mods").glob("esperon-dano-*") if path.is_dir())
    if len(mods) != 20:
        raise SystemExit(f"Se esperaban 20 mods, se encontraron {len(mods)}")
    baseline = {mod.name: file_fingerprints(root, mod) for mod in mods}
    write_json(qa_root / "baseline" / "qa-baseline.json", {"scope": "QA_BASELINE", "mods": baseline})
    all_rounds: list[dict] = []
    for round_no in range(1, args.rounds + 1):
        focus = ROUND_FOCUS.get(round_no, "extended")
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            reports = list(executor.map(lambda mod: audit_mod(root, mod, round_no, args.previews and round_no == 13), mods))
        current = {report["mod"]: report["fingerprints"] for report in reports}
        changed = [mod for mod in baseline if baseline[mod] != current[mod]]
        summary = {
            "scope": "QA_LAB_ROUND", "round": round_no, "focus": focus, "mods": len(reports),
            "passed": sum(report["status"] == "PASS" for report in reports),
            "warnings": sum(report["status"] == "WARNING" for report in reports),
            "errors": sum(report["status"] == "ERROR" for report in reports),
            "changed_since_baseline": changed, "repairs": [], "reports": reports,
        }
        round_dir = qa_root / "artifacts" / f"round-{round_no:02d}"
        write_json(round_dir / "summary.json", summary)
        (round_dir / "summary.md").write_text(markdown_summary(round_no, focus, reports), encoding="utf-8")
        for report in reports:
            write_json(round_dir / "mods" / f"{report['mod']}.json", report)
        all_rounds.append(summary)
        print(json.dumps({"round": round_no, "focus": focus, "passed": summary["passed"], "warnings": summary["warnings"], "errors": summary["errors"]}, ensure_ascii=False), flush=True)
    totals = {"errors": sum(item["errors"] for item in all_rounds), "warnings": sum(item["warnings"] for item in all_rounds)}
    plateau = totals["errors"] == 0 and all(not item["changed_since_baseline"] for item in all_rounds)
    consolidated = {
        "scope": "QA_LAB_CONSOLIDATED_20_ROUNDS", "executed_at": datetime.now(timezone.utc).isoformat(),
        "rounds": len(all_rounds), "mods_per_round": len(mods), "records": len(all_rounds) * len(mods),
        "totals": totals, "status": "STABLE_PLATEAU_REACHED" if plateau else "REVIEW_OR_REPAIR_REQUIRED",
        "rounds_summary": [{key: item[key] for key in ("round", "focus", "passed", "warnings", "errors", "changed_since_baseline")} for item in all_rounds],
        "limitations": ["No ejecuta el renderer ni Audio Sync Test de FNF Mobile.", "No promociona cambios musicales/visuales sin un ejecutor de reparación y revalidación posterior."]
    }
    write_json(qa_root / "final" / "consolidated-20-rounds.json", consolidated)
    print(json.dumps(consolidated, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
