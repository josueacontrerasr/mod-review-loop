#!/usr/bin/env python3
"""Compara producción V2.5.1 contra candidatos vocal-only sin promover nada."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFICULTIES = ("easy", "normal", "hard")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def in_segment(time_ms: float, segments: list[dict[str, float]], margin_ms: float = 45.0) -> bool:
    return any(float(seg["start_ms"]) - margin_ms <= time_ms <= float(seg["end_ms"]) + margin_ms for seg in segments)


def nearest_stats(source: list[float], target: list[float]) -> dict[str, Any]:
    if not source or not target:
        return {"source": len(source), "target": len(target), "matched_120ms": 0, "coverage_percent": 0.0, "mean_ms": None, "max_ms": None}
    distances = [min(abs(value - candidate) for candidate in target) for value in source]
    return {
        "source": len(source), "target": len(target),
        "matched_120ms": sum(distance <= 120.0 for distance in distances),
        "coverage_percent": round(sum(distance <= 120.0 for distance in distances) / len(distances) * 100.0, 3),
        "mean_ms": round(sum(distances) / len(distances), 3),
        "max_ms": round(max(distances), 3),
    }


def inspect_one(root: Path, song: str) -> dict[str, Any]:
    song_dir = root / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song
    production = load(song_dir / f"{song}-chart.json")
    candidate = load(root / "qa-lab" / "rebuild-v260" / "vocal-only" / song / "chart-vocal-only.json")
    activity = load(root / "qa-lab" / "rebuild-v260" / "vocal-only" / song / "voice-activity.json")
    segments = activity.get("segments", [])
    rows: dict[str, Any] = {}
    errors: list[str] = []
    for difficulty in DIFFICULTIES:
        old_entries = production.get("notes", {}).get(difficulty, [])
        new_entries = candidate.get("notes", {}).get(difficulty, [])
        old_times = [float(entry["t"]) for entry in old_entries if isinstance(entry, dict) and isinstance(entry.get("t"), (int, float))]
        new_times = [float(entry["t"]) for entry in new_entries if isinstance(entry, dict) and isinstance(entry.get("t"), (int, float))]
        old_inside = sum(in_segment(value, segments) for value in old_times)
        old_outside = len(old_times) - old_inside
        new_outside = sum(not in_segment(value, segments) for value in new_times)
        if new_outside:
            errors.append(f"{difficulty}:new_outside={new_outside}")
        rows[difficulty] = {
            "production_notes": len(old_times),
            "production_inside_vocal_segment": old_inside,
            "production_outside_vocal_segment": old_outside,
            "candidate_notes": len(new_times),
            "candidate_outside_vocal_segment": new_outside,
            "candidate_vs_production": nearest_stats(new_times, old_times),
            "production_vs_candidate": nearest_stats(old_times, new_times),
            "candidate_density_delta_percent": round((len(new_times) - len(old_times)) / len(old_times) * 100.0, 3) if old_times else None,
        }
    return {"song": song, "status": "PASS" if not errors else "ERROR", "errors": errors, "difficulties": rows, "policy": "Production chart is reference only; candidate has voice provenance."}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: inspect_one(root, song), SONGS), key=lambda row: row["song"])
    total_old = 0
    total_old_outside = 0
    total_new = 0
    for row in rows:
        for value in row["difficulties"].values():
            total_old += value["production_notes"]
            total_old_outside += value["production_outside_vocal_segment"]
            total_new += value["candidate_notes"]
    payload = {
        "scope": "VOCAL_ONLY_PRODUCTION_COMPARISON_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "difficulties": len(rows) * len(DIFFICULTIES),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "totals": {"production_notes": total_old, "production_outside_vocal_segment": total_old_outside, "candidate_notes": total_new, "production_outside_percent": round(total_old_outside / total_old * 100.0, 3) if total_old else 0.0},
        "rows": rows,
        "promotion": "BLOCKED_UNTIL_REVIEW",
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "production-comparison-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "difficulties": payload["difficulties"], "passed": payload["passed"], "status": payload["status"], "totals": payload["totals"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
