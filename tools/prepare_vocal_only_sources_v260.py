#!/usr/bin/env python3
"""Inventario paralelo de fuentes vocales para charts vocal-only V-Slice 0.8.6."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=codec_name,sample_rate,channels,duration", "-of", "json", str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    streams = json.loads(result.stdout).get("streams", [])
    return streams[0] if streams else {}


def inspect_one(root: Path, song: str) -> dict[str, Any]:
    song_dir = root / "mods" / f"esperon-dano-{song}" / "songs" / song
    inst = song_dir / "Inst.ogg"
    voices = sorted(song_dir.glob("Voices-*.ogg"))
    errors: list[str] = []
    if not inst.is_file():
        errors.append("instrumental_missing")
    if len(voices) != 1:
        errors.append(f"vocal_source_count={len(voices)}")
    vocal = voices[0] if voices else song_dir / "Voices-MISSING.ogg"
    inst_probe = probe(inst) if inst.is_file() else {}
    vocal_probe = probe(vocal) if vocal.is_file() else {}
    inst_duration = float(inst_probe.get("duration", 0.0) or 0.0)
    vocal_duration = float(vocal_probe.get("duration", 0.0) or 0.0)
    delta = abs(inst_duration - vocal_duration)
    if delta > 0.75:
        errors.append(f"duration_delta_seconds={delta:.3f}")
    if vocal.is_file() and vocal_probe.get("codec_name") != "vorbis":
        errors.append(f"vocal_codec={vocal_probe.get('codec_name')}")
    return {
        "song": song,
        "status": "PASS" if not errors else "ERROR",
        "errors": errors,
        "source_type": "DISTRIBUTED_VOCAL_OGG" if vocal.is_file() else "MISSING",
        "vocal_path": str(vocal.relative_to(root)) if vocal.is_file() else None,
        "instrumental_path": str(inst.relative_to(root)) if inst.is_file() else None,
        "vocal_sha256": sha256(vocal) if vocal.is_file() else None,
        "instrumental_sha256": sha256(inst) if inst.is_file() else None,
        "vocal_probe": vocal_probe,
        "instrumental_probe": inst_probe,
        "duration_delta_seconds": round(delta, 6),
        "chart_source_policy": "VOCAL_ONLY; Inst.ogg is context-only and cannot generate notes",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: inspect_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "VOCAL_ONLY_SOURCE_INVENTORY_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "policy": "No se usa Inst.ogg para crear notas; solo Voices-*.ogg puede producir anclajes vocales.",
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "source-inventory-v260.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
