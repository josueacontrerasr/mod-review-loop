#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "qa-lab/rebuild-v271/playstate-fix/density-candidates"
BASE_ROOT = ROOT / "mods"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahORA-MISMO".lower(), "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def groups(notes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    result: list[list[dict[str, Any]]] = []
    for note in sorted(notes, key=lambda row: float(row.get("t", 0.0))):
        t = float(note.get("t", 0.0))
        if not result or t - float(result[-1][-1].get("t", 0.0)) > 1.0:
            result.append([note])
        else:
            result[-1].append(note)
    return result


def max_window(notes: list[dict[str, Any]], window_ms: float) -> dict[str, Any]:
    ordered = sorted(notes, key=lambda row: float(row.get("t", 0.0)))
    best = {"raw_notes": 0, "start_ms": 0.0, "end_ms": window_ms}
    left = 0
    for right, note in enumerate(ordered):
        t = float(note.get("t", 0.0))
        while left <= right and t - float(ordered[left].get("t", 0.0)) > window_ms:
            left += 1
        raw = right - left + 1
        if raw > best["raw_notes"]:
            best = {"raw_notes": raw, "start_ms": float(ordered[left].get("t", 0.0)), "end_ms": round(float(ordered[left].get("t", 0.0)) + window_ms, 3)}
    return best


def coverage(notes: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> tuple[int, int]:
    covered = 0
    for syllable in syllables:
        start = float(syllable.get("start_ms", 0.0))
        end = float(syllable.get("vocal_end_ms", start + 40.0))
        if any(float(note.get("t", 0.0)) - 45.0 <= end and float(note.get("t", 0.0)) + float(note.get("l", 0.0) or 0.0) + 45.0 >= start for note in notes):
            covered += 1
    return covered, len(syllables)


def nearest_error(notes: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> dict[str, float]:
    starts = [float(item.get("start_ms", 0.0)) for item in syllables]
    ordered = sorted(notes, key=lambda note: float(note.get("t", 0.0)))
    errors: list[float] = []
    for note in ordered:
        t = float(note.get("t", 0.0))
        inherited = False
        for parent in ordered:
            parent_t = float(parent.get("t", 0.0))
            parent_l = float(parent.get("l", 0.0) or 0.0)
            if parent_l >= 120.0 and parent_t + 1.0 < t <= parent_t + parent_l + 1.0:
                errors.append(0.0)
                inherited = True
                break
        if not inherited and starts:
            errors.append(min(abs(t - start) for start in starts))
    if not errors:
        return {"median_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(errors)
    position = 0.95 * (len(ordered) - 1)
    lo, hi = math.floor(position), math.ceil(position)
    p95 = ordered[lo] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)
    return {"median_ms": round(median(errors), 3), "p95_ms": round(p95, 3), "max_ms": round(max(errors), 3)}


def diff_notes(candidate: list[dict[str, Any]], base: list[dict[str, Any]]) -> dict[str, int]:
    cand_keys = {(round(float(note.get("t", 0.0)), 3), int(note.get("d", -1))) for note in candidate}
    base_keys = {(round(float(note.get("t", 0.0)), 3), int(note.get("d", -1))) for note in base}
    return {"added": len(cand_keys - base_keys), "removed": len(base_keys - cand_keys), "unchanged": len(cand_keys & base_keys)}


def analyze_song(song: str) -> dict[str, Any]:
    candidate = load(CANDIDATE_ROOT / song / "candidate-chart.json")
    alignment = load(CANDIDATE_ROOT / song / "syllable-alignment.json")
    base_path = BASE_ROOT / f"esperon-dano-{song}" / "data/songs" / song / f"{song}-chart.json"
    base = load(base_path)
    syllables = alignment.get("syllables", [])
    row: dict[str, Any] = {"song": song, "warnings": [], "difficulties": {}}
    for difficulty in DIFFS:
        notes = candidate.get("notes", {}).get(difficulty, [])
        base_notes = base.get("notes", {}).get(difficulty, [])
        hold_lengths = [float(note.get("l", 0.0) or 0.0) for note in notes if float(note.get("l", 0.0) or 0.0) > 0]
        lane_counts = {str(lane): sum(1 for note in notes if int(note.get("d", -1)) == lane) for lane in range(4)}
        lane_sequence = [int(note.get("d", -1)) for note in sorted(notes, key=lambda note: float(note.get("t", 0.0)))]
        runs: list[int] = []
        if lane_sequence:
            length = 1
            for previous, current in zip(lane_sequence, lane_sequence[1:]):
                if previous == current:
                    length += 1
                else:
                    runs.append(length)
                    length = 1
            runs.append(length)
        covered, total = coverage(notes, syllables)
        density_500 = max_window(notes, 500.0)
        density_1000 = max_window(notes, 1000.0)
        quality = {
            "notes": len(notes),
            "base_notes": len(base_notes),
            "change": diff_notes(notes, base_notes),
            "holds": len(hold_lengths),
            "hold_ratio": round(len(hold_lengths) / max(1, len(notes)), 4),
            "hold_max_ms": round(max(hold_lengths, default=0.0), 3),
            "hold_p95_ms": round(sorted(hold_lengths)[int(0.95 * (len(hold_lengths) - 1))], 3) if hold_lengths else 0.0,
            "max_notes_500ms": density_500,
            "max_notes_1000ms": density_1000,
            "lane_counts": lane_counts,
            "same_lane_max_run": max(runs, default=0),
            "covered_syllables": covered,
            "syllables": total,
            "coverage_ratio": round(covered / max(1, total), 4),
            "nearest_syllable_error": nearest_error(notes, syllables),
            "samples": {
                "first": sorted(notes, key=lambda note: float(note.get("t", 0.0)))[:3],
                "middle": sorted(notes, key=lambda note: float(note.get("t", 0.0)))[max(0, len(notes) // 2 - 1):len(notes) // 2 + 2],
                "last": sorted(notes, key=lambda note: float(note.get("t", 0.0)))[-3:],
                "densest_500ms": density_500,
                "densest_1000ms": density_1000,
            },
        }
        row["difficulties"][difficulty] = quality
        coverage_threshold = 0.85 if difficulty == "easy" else 0.94
        if quality["coverage_ratio"] < coverage_threshold:
            row["warnings"].append({"difficulty": difficulty, "type": "coverage_below_threshold", "threshold": coverage_threshold, "value": quality["coverage_ratio"]})
        if quality["hold_ratio"] > 0.95:
            row["warnings"].append({"difficulty": difficulty, "type": "very_high_hold_ratio_review", "value": quality["hold_ratio"]})
        if quality["same_lane_max_run"] > 4:
            row["warnings"].append({"difficulty": difficulty, "type": "same_lane_run_review", "value": quality["same_lane_max_run"]})
        if quality["nearest_syllable_error"]["p95_ms"] > 5.0:
            row["warnings"].append({"difficulty": difficulty, "type": "onset_p95_over_5ms", "value": quality["nearest_syllable_error"]["p95_ms"]})
    counts = {difficulty: row["difficulties"][difficulty]["notes"] for difficulty in DIFFS}
    if not (counts["easy"] < counts["normal"] < counts["hard"]):
        row["warnings"].append({"type": "difficulty_progression", "value": counts})
    return row


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(analyze_song, SONGS))
    warnings = [{"song": row["song"], "warnings": row["warnings"]} for row in rows if row["warnings"]]
    output = ROOT / "qa-lab/rebuild-v271/playstate-fix/candidate-quality-v271.json"
    payload = {"scope": "WIDE_RESEARCH_V271_CANDIDATE_QUALITY", "created_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "parallel_workers": 8, "status": "PASS_WITH_REVIEW_WARNINGS" if warnings else "PASS", "warning_song_count": len(warnings), "warnings": warnings, "rows": sorted(rows, key=lambda row: row["song"])}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "songs": payload["songs"], "warning_song_count": payload["warning_song_count"], "warnings": sum(len(row["warnings"]) for row in warnings), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
