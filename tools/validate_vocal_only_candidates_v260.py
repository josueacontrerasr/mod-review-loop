#!/usr/bin/env python3
"""Valida procedencia estrictamente vocal de los candidatos V260."""
from __future__ import annotations

import argparse
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
    return any(float(segment["start_ms"]) - margin_ms <= time_ms <= float(segment["end_ms"]) + margin_ms for segment in segments)


def validate_song(root: Path, song: str) -> dict[str, Any]:
    base = root / "qa-lab" / "rebuild-v260" / "vocal-only" / song
    errors: list[str] = []
    warnings: list[str] = []
    activity = load(base / "voice-activity.json")
    chart = load(base / "chart-vocal-only.json")
    report = load(base / "candidate-report.json")
    source_inventory = load(root / "qa-lab" / "rebuild-v260" / "vocal-only" / "source-inventory-v260.json")
    source_row = next(row for row in source_inventory["rows"] if row["song"] == song)
    if report.get("source_vocal_sha256") != source_row.get("vocal_sha256"):
        errors.append("source_hash_mismatch")
    if report.get("instrumental_used_for_generation") is not False:
        errors.append("instrumental_generation_flag")
    if chart.get("sourcePolicy") != "NO_INSTRUMENTAL_NOTES":
        errors.append("source_policy_missing")
    notes = chart.get("notes", {})
    segments = activity.get("segments", [])
    row = {"song": song, "status": "PASS", "difficulties": {}, "errors": errors, "warnings": warnings, "instrumental_used_for_generation": False}
    for difficulty in DIFFICULTIES:
        entries = notes.get(difficulty)
        if not isinstance(entries, list):
            errors.append(f"{difficulty}:missing_notes")
            continue
        times = []
        source_errors = 0
        outside = 0
        duplicate_keys: set[tuple[float, int]] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                source_errors += 1
                continue
            time_ms = entry.get("t")
            lane = entry.get("d")
            times.append(float(time_ms) if isinstance(time_ms, (int, float)) else -1.0)
            if entry.get("_source") != "voice" or not isinstance(entry.get("_voice_event_id"), str):
                source_errors += 1
            if any(token in json.dumps(entry, ensure_ascii=False).lower() for token in ("inst.ogg", "instrumental", "rhythm", "full_mix")):
                source_errors += 1
            if not isinstance(time_ms, (int, float)) or not isinstance(lane, int) or lane not in (0, 1, 2, 3):
                source_errors += 1
                continue
            if not in_segment(float(time_ms), segments):
                outside += 1
            key = (round(float(time_ms), 3), lane)
            if key in duplicate_keys:
                source_errors += 1
            duplicate_keys.add(key)
        ordered = times == sorted(times) and all(time >= 0 for time in times)
        if not ordered:
            errors.append(f"{difficulty}:time_order")
        if source_errors:
            errors.append(f"{difficulty}:source_or_note_errors={source_errors}")
        if outside:
            errors.append(f"{difficulty}:outside_vocal_segments={outside}")
        row["difficulties"][difficulty] = {
            "notes": len(entries),
            "source_errors": source_errors,
            "outside_vocal_segments": outside,
            "coverage_within_vocal_segment_percent": round((len(entries) - outside) / len(entries) * 100.0, 3) if entries else 0.0,
            "ordered": ordered,
            "lane_domain": [0, 1, 2, 3],
        }
    counts = [len(notes.get(difficulty, [])) for difficulty in DIFFICULTIES]
    if not (counts[0] < counts[1] < counts[2]):
        errors.append(f"difficulty_density={counts}")
    row["status"] = "PASS" if not errors else "ERROR"
    row["errors"] = errors
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    rows = [validate_song(root, song) for song in SONGS]
    payload = {
        "scope": "VOCAL_ONLY_PROVENANCE_GATE_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "difficulties": len(rows) * len(DIFFICULTIES),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "failed": sum(row["status"] == "ERROR" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "instrumental_used_for_generation": False,
        "rows": rows,
        "policy": "Cualquier nota sin origen voice o fuera de segmento vocal bloquea promoción.",
        "limitations": ["La procedencia vocal del stem no identifica por sí sola sílaba o cantante.", "Audio Sync Test y playtest móvil siguen siendo obligatorios."],
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "provenance-gate-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "difficulties": payload["difficulties"], "passed": payload["passed"], "failed": payload["failed"], "status": payload["status"], "instrumental_used_for_generation": payload["instrumental_used_for_generation"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
