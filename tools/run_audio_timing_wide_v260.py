#!/usr/bin/env python3
"""Ejecuta el análisis temporal de los 20 audios finales en paralelo.

El script solo genera evidencia; no modifica audio, charts ni metadata de producción.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def analyze_one(args: tuple[Path, str, Path, Path]) -> dict[str, Any]:
    root, song, analyzer, output_dir = args
    audio = root / "mods" / f"esperon-dano-{song}" / "songs" / song / "Inst.ogg"
    output = output_dir / f"{song}.json"
    command = [sys.executable, str(analyzer), str(audio), "--output", str(output)]
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"song": song, "status": "ERROR", "audio": str(audio.relative_to(root)), "error": str(exc)}
    row: dict[str, Any] = {
        "song": song,
        "status": "PASS" if result.returncode == 0 and output.is_file() else "ERROR",
        "audio": str(audio.relative_to(root)),
        "output": str(output.relative_to(root)) if output.is_file() else None,
        "returncode": result.returncode,
    }
    if result.returncode != 0:
        row["stderr"] = result.stderr.strip()[-2000:]
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    analyzer = Path("/home/ubuntu/skills/fnf-mobile-vslice-mods/scripts/analyze_audio_timing.py")
    if not analyzer.is_file():
        raise SystemExit(f"No existe el analizador requerido: {analyzer}")
    output_dir = root / "qa-lab" / "rebuild-v260" / "audio-timing"
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = [(root, song, analyzer, output_dir) for song in SONGS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = sorted(executor.map(analyze_one, jobs), key=lambda row: row["song"])
    payload = {
        "scope": "WIDE_AUDIO_TIMING_ANALYSIS_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "parallel_workers": max(1, args.workers),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "policy": [
            "El análisis produce candidatos de tempo/onset; no promociona offsets ni modifica charts.",
            "La sincronía vocal definitiva requiere stems vocales identificados, Audio Sync Test y playtest móvil.",
        ],
    }
    output = root / "qa-lab" / "rebuild-v260" / "audio-sync-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {key: payload[key] for key in ("songs", "passed", "status")}
    summary["output"] = str(output)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
