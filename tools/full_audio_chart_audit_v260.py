#!/usr/bin/env python3
"""Auditor paralelo de audio y charts para los 20 mods V-Slice 0.8.6.

Compara charts de producción contra candidatos de onsets generados del audio actual.
No afirma identidad vocal cuando el modo es FULL_MIX_PROXY y no modifica producción.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
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


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_stats(values: list[float], anchors: list[float]) -> dict[str, Any]:
    if not values or not anchors:
        return {"count": len(values), "matched_120ms": 0, "coverage_percent": 0.0, "mean_ms": None, "median_ms": None, "p90_ms": None, "max_ms": None}
    ordered = sorted(anchors)
    distances: list[float] = []
    for value in values:
        index = min(range(len(ordered)), key=lambda item: abs(ordered[item] - value))
        distances.append(abs(ordered[index] - value))
    distances.sort()
    p90 = distances[min(len(distances) - 1, max(0, math.ceil(len(distances) * 0.90) - 1))]
    median = distances[len(distances) // 2]
    return {
        "count": len(values),
        "matched_120ms": sum(distance <= 120.0 for distance in distances),
        "coverage_percent": round(sum(distance <= 120.0 for distance in distances) / len(distances) * 100.0, 3),
        "mean_ms": round(sum(distances) / len(distances), 3),
        "median_ms": round(median, 3),
        "p90_ms": round(p90, 3),
        "max_ms": round(max(distances), 3),
    }


def audit_one(root: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    song_dir = mod / "data" / "songs" / song
    chart_path = song_dir / f"{song}-chart.json"
    meta_path = song_dir / f"{song}-metadata.json"
    candidate_path = root / "sync-candidates" / "results" / song / "candidate-chart.json"
    candidate_report_path = root / "sync-candidates" / "results" / song / "sync-candidate-report.json"
    timing_path = root / "qa-lab" / "rebuild-v260" / "audio-timing" / f"{song}.json"
    errors: list[str] = []
    warnings: list[str] = []
    chart = read(chart_path)
    meta = read(meta_path)
    candidate = read(candidate_path)
    report = read(candidate_report_path)
    timing = read(timing_path)
    notes = chart.get("notes", {})
    candidate_notes = candidate.get("notes", {})
    production_counts: dict[str, int] = {}
    candidate_counts: dict[str, int] = {}
    alignment: dict[str, dict[str, Any]] = {}
    lane_sets: dict[str, list[int]] = {}
    order_ok: dict[str, bool] = {}
    duplicates_ok: dict[str, bool] = {}
    candidate_anchor_times = sorted(float(note["t"]) for note in candidate_notes.get("normal", []) if isinstance(note, dict) and isinstance(note.get("t"), (int, float)))
    for difficulty in DIFFICULTIES:
        entries = notes.get(difficulty, [])
        candidate_entries = candidate_notes.get(difficulty, [])
        production_counts[difficulty] = len(entries) if isinstance(entries, list) else 0
        candidate_counts[difficulty] = len(candidate_entries) if isinstance(candidate_entries, list) else 0
        times = [float(note.get("t")) for note in entries if isinstance(note, dict) and isinstance(note.get("t"), (int, float))]
        lanes = [int(note.get("d")) for note in entries if isinstance(note, dict) and isinstance(note.get("d"), int)]
        keys = [(float(note.get("t", -1)), int(note.get("d", -1))) for note in entries if isinstance(note, dict) and isinstance(note.get("t"), (int, float)) and isinstance(note.get("d"), int)]
        lane_sets[difficulty] = sorted(set(lanes))
        order_ok[difficulty] = len(keys) == len(entries) and keys == sorted(keys) and all(timestamp >= 0 for timestamp, _ in keys)
        duplicates_ok[difficulty] = len(keys) == len(set(keys))
        if not order_ok[difficulty]:
            errors.append(f"{difficulty}:order_or_note_contract")
        if not duplicates_ok[difficulty]:
            errors.append(f"{difficulty}:duplicate_notes")
        if any(lane not in (0, 1, 2, 3) for lane in lanes):
            errors.append(f"{difficulty}:player_lane_domain")
        alignment[difficulty] = nearest_stats(times, candidate_anchor_times)
    if set(notes) != set(DIFFICULTIES):
        errors.append("difficulty_set")
    if not (production_counts["easy"] < production_counts["normal"] < production_counts["hard"]):
        errors.append("production_density_order")
    scroll = chart.get("scrollSpeed", {})
    if not (float(scroll.get("easy", 0)) < float(scroll.get("normal", 0)) < float(scroll.get("hard", 0))):
        errors.append("scroll_speed_order")
    if chart.get("version") != "2.0.0":
        errors.append("chart_version")
    if meta.get("version") != "2.2.4":
        errors.append("metadata_version")
    if report.get("analysis_mode") == "FULL_MIX_PROXY":
        warnings.append("manual_voice_identity_review_required")
    else:
        warnings.append("stem_identity_review_required")
    if report.get("status") != "MANUAL_REVIEW_REQUIRED":
        warnings.append(f"unexpected_candidate_status:{report.get('status')}")
    return {
        "song": song,
        "status": "PASS" if not errors else "ERROR",
        "errors": errors,
        "warnings": warnings,
        "analysis_mode": report.get("analysis_mode"),
        "production_counts": production_counts,
        "candidate_counts": candidate_counts,
        "lane_sets": lane_sets,
        "order_ok": order_ok,
        "duplicates_ok": duplicates_ok,
        "scroll_speed": scroll,
        "time_changes": meta.get("timeChanges", []),
        "audio": {
            "sha256": timing.get("sha256"),
            "duration_seconds": timing.get("probe", {}).get("duration_seconds"),
            "first_detected_attack_ms": timing.get("analysis", {}).get("first_detected_attack_ms"),
            "onset_count": timing.get("analysis", {}).get("onset_count"),
            "bpm_candidates": timing.get("analysis", {}).get("bpm_candidates", []),
        },
        "alignment_to_current_full_mix_candidate_ms": alignment,
        "promotion": "NO_AUTOMATIC_PROMOTION",
        "limitations": [
            "La comparación usa candidatos del audio distribuido actual.",
            "FULL_MIX_PROXY no demuestra que cada onset sea vocal ni identifica personaje/strumline.",
            "Audio Sync Test y playtest móvil siguen siendo necesarios.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = sorted(executor.map(lambda song: audit_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "FULL_AUDIO_CHART_AUDIT_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "songs": len(rows),
        "difficulties": len(rows) * len(DIFFICULTIES),
        "parallel_workers": max(1, args.workers),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "manual_review_required": sum("manual_voice_identity_review_required" in row["warnings"] for row in rows),
        "status": "PASS_WITH_MANUAL_SYNC_REVIEW" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "policy": "No se modifican charts, BPM, offsets ni audio durante esta auditoría.",
    }
    output = root / "qa-lab" / "rebuild-v260" / "full-audio-chart-audit-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "difficulties": payload["difficulties"], "passed": payload["passed"], "manual_review_required": payload["manual_review_required"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS_WITH_MANUAL_SYNC_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
