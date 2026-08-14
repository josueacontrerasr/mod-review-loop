#!/usr/bin/env python3
"""Una ronda completa de auditoría por archivo para 20 mods V-Slice y sus ZIPs."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audio_probe(path: Path) -> dict[str, Any]:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path)
    ], text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "ffprobe falló")
    data = json.loads(result.stdout)
    if not data.get("format", {}).get("duration"):
        raise ValueError("duración de audio ausente")
    return data


def audit_file(path: Path) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    rel = path.as_posix()
    try:
        if suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        elif suffix == ".xml":
            ET.parse(path)
        elif suffix == ".png":
            with Image.open(path) as image:
                image.verify()
        elif suffix in {".ogg", ".wav", ".m4a"}:
            audio_probe(path)
        elif suffix in {".txt", ".hxc", ".md"}:
            path.read_text(encoding="utf-8")
        else:
            path.read_bytes()
    except Exception as exc:
        return rel, str(exc)
    return rel, None


def audit_mod(root: Path, mod: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    files = sorted(item for item in mod.rglob("*") if item.is_file())
    file_errors = []
    for path in files:
        _, error = audit_file(path)
        if error:
            file_errors.append(f"{path.relative_to(mod)}: {error}")
    errors.extend(file_errors)
    manifest = json.loads((mod / "_polymod_meta.json").read_text(encoding="utf-8")) if (mod / "_polymod_meta.json").is_file() else {}
    if manifest.get("api_version") != "0.8.6":
        errors.append("api_version no coincide con 0.8.6")
    song_dirs = [item for item in (mod / "data" / "songs").glob("*") if item.is_dir()] if (mod / "data" / "songs").is_dir() else []
    if len(song_dirs) != 1:
        errors.append("debe existir una carpeta de canción")
        song = ""
    else:
        song_dir = song_dirs[0]
        song = song_dir.name
        metadata = json.loads((song_dir / f"{song}-metadata.json").read_text(encoding="utf-8"))
        chart = json.loads((song_dir / f"{song}-chart.json").read_text(encoding="utf-8"))
        if metadata.get("version") != "2.2.4" or chart.get("version") != "2.0.0":
            errors.append("schema de metadata/chart incorrecto")
        play = metadata.get("playData", {})
        for key in ("player", "opponent"):
            character = play.get("characters", {}).get(key)
            if not isinstance(character, str) or not (mod / "data" / "characters" / f"{character}.json").is_file():
                errors.append(f"personaje {key} no resuelto")
        style = play.get("noteStyle")
        if not isinstance(style, str) or not (mod / "data" / "notestyles" / f"{style}.json").is_file():
            errors.append("note style no resuelto")
        if not (mod / "songs" / song / "Inst.ogg").is_file():
            errors.append("Inst.ogg ausente")
        for difficulty in ("easy", "normal", "hard"):
            notes = chart.get("notes", {}).get(difficulty)
            if not isinstance(notes, list) or not notes:
                errors.append(f"{difficulty}: notas ausentes")
                continue
            previous = -1.0
            for index, note in enumerate(notes):
                if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                    errors.append(f"{difficulty}[{index}]: nota inválida")
                    continue
                if note["t"] < previous or not 0 <= note["d"] <= 7:
                    errors.append(f"{difficulty}[{index}]: orden/dirección inválidos")
                previous = float(note["t"])
                if "l" in note and (not isinstance(note["l"], (int, float)) or note["l"] <= 0):
                    errors.append(f"{difficulty}[{index}]: hold inválido")
    sync = mod / "sync-report.json"
    if sync.is_file():
        status = json.loads(sync.read_text(encoding="utf-8")).get("status")
        if status != "PASS":
            warnings.append(f"sync-report={status}; requiere Audio Sync Test/playtest si no existe evidencia manual")
    zip_path = root / "dist" / f"{mod.name}-v2.0.0.zip"
    if not zip_path.is_file():
        errors.append("ZIP v2.0.0 ausente")
    else:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                corrupt = archive.testzip()
                if corrupt:
                    errors.append(f"CRC inválido: {corrupt}")
                roots = {entry.split("/")[0] for entry in archive.namelist() if entry and not entry.startswith("__MACOSX")}
                if roots != {mod.name}:
                    errors.append("ZIP no contiene una única carpeta raíz correcta")
        except Exception as exc:
            errors.append(f"ZIP ilegible: {exc}")
    fingerprint = hashlib.sha256()
    for file in files:
        fingerprint.update(file.relative_to(mod).as_posix().encode())
        fingerprint.update(sha256(file).encode())
    return {
        "mod": mod.name, "song": song, "files_audited": len(files), "fingerprint_sha256": fingerprint.hexdigest(),
        "errors": errors, "warnings": warnings, "status": "PASS" if not errors else "ERROR"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    mods = sorted(path for path in (root / "mods").glob("esperon-dano-*") if path.is_dir())
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        reports = list(executor.map(lambda item: audit_mod(root, item), mods))
    payload = {
        "round": args.round,
        "scope": "ALL_FILES_ALL_20_MODS_AND_V2_ZIPS",
        "mods": len(reports),
        "files_audited": sum(report["files_audited"] for report in reports),
        "errors": sum(len(report["errors"]) for report in reports),
        "warnings": sum(len(report["warnings"]) for report in reports),
        "status": "PASS" if all(report["status"] == "PASS" for report in reports) else "ERRORS_FOUND",
        "reports": reports,
        "limitations": [
            "La auditoría recorre archivos y valida estructura, CRC, JSON, XML, PNG, OGG y charts.",
            "No puede sustituir Audio Sync Test del editor ni un playtest en FNF Mobile V-Slice."
        ]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("round", "mods", "files_audited", "errors", "warnings", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
