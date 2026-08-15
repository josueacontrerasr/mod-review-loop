#!/usr/bin/env python3
"""Gate independiente de VAD CPU para candidatos vocal-only."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import librosa
import numpy as np

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFICULTIES = ("easy", "normal", "hard")
SR = 16000
FRAME_MS = 20
HOP = SR * FRAME_MS // 1000
HANGOVER_MS = 200
MIN_SEGMENT_MS = 120


def merge_active(active: np.ndarray) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    start: int | None = None
    hangover_frames = max(1, HANGOVER_MS // FRAME_MS)
    silence_run = 0
    for index, flag in enumerate(active):
        if bool(flag):
            if start is None:
                start = index
            silence_run = 0
        elif start is not None:
            silence_run += 1
            if silence_run > hangover_frames:
                end = index - silence_run + 1
                start_ms = start * FRAME_MS
                end_ms = end * FRAME_MS
                if end_ms - start_ms >= MIN_SEGMENT_MS:
                    segments.append((start_ms, end_ms))
                start = None
                silence_run = 0
    if start is not None:
        end = len(active)
        start_ms = start * FRAME_MS
        end_ms = end * FRAME_MS
        if end_ms - start_ms >= MIN_SEGMENT_MS:
            segments.append((start_ms, end_ms))
    return segments


def inside(time_ms: float, segments: list[tuple[float, float]], margin_ms: float = 60.0) -> bool:
    return any(start - margin_ms <= time_ms <= end + margin_ms for start, end in segments)


def validate_one(root: Path, song: str) -> dict[str, Any]:
    voice = next((root / "mods" / f"esperon-dano-{song}" / "songs" / song).glob("Voices-*.ogg"))
    y, _ = librosa.load(voice, sr=SR, mono=True)
    rms = librosa.feature.rms(y=y, frame_length=HOP, hop_length=HOP, center=False)[0]
    sorted_rms = np.sort(rms)
    noise_floor = float(np.median(sorted_rms[: max(1, len(sorted_rms) // 3)]))
    threshold = max(noise_floor * 4.0, float(np.percentile(rms, 35.0)))
    segments = merge_active(rms >= threshold)
    chart = json.loads((root / "qa-lab" / "rebuild-v260" / "vocal-only" / song / "chart-vocal-only.json").read_text(encoding="utf-8"))
    difficulties: dict[str, Any] = {}
    errors: list[str] = []
    for difficulty in DIFFICULTIES:
        entries = chart.get("notes", {}).get(difficulty, [])
        times = [float(entry["t"]) for entry in entries]
        matched = sum(inside(time_ms, segments) for time_ms in times)
        coverage = matched / len(times) * 100.0 if times else 0.0
        if coverage < 90.0:
            errors.append(f"{difficulty}:coverage={coverage:.3f}")
        difficulties[difficulty] = {"notes": len(times), "matched": matched, "coverage_percent": round(coverage, 3)}
    return {"song": song, "status": "PASS" if not errors else "ERROR", "errors": errors, "noise_floor": noise_floor, "threshold": threshold, "segment_count": len(segments), "difficulties": difficulties}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: validate_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "INDEPENDENT_VAD_GATE_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "frame_ms": FRAME_MS,
        "sample_rate": SR,
        "hangover_ms": HANGOVER_MS,
        "songs": len(rows),
        "difficulties": len(rows) * len(DIFFICULTIES),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "failed": sum(row["status"] == "ERROR" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "policy": "Independent CPU VAD is a gate against notes outside vocal activity; it never uses Inst.ogg.",
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "independent-vad-gate-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "difficulties": payload["difficulties"], "passed": payload["passed"], "failed": payload["failed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
