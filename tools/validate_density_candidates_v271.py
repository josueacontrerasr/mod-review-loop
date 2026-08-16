#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "qa-lab/rebuild-v271/playstate-fix/density-candidates"
DIFFS = ("easy", "normal", "hard")
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.1 density-aware vocal clusters, retimed holds and player lanes d=0..3"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def attack_groups(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for note in sorted(notes, key=lambda value: float(value.get("t", 0.0))):
        t = float(note.get("t", 0.0))
        if not groups or t - groups[-1]["last_t"] > 1.0:
            groups.append({"t": t, "last_t": t, "notes": [note]})
        else:
            groups[-1]["last_t"] = t
            groups[-1]["notes"].append(note)
    for group in groups:
        group["size"] = len(group["notes"])
    return groups


def dense_cluster_count(groups: list[dict[str, Any]], window_ms: float, threshold: int) -> int:
    count = 0
    for index, group in enumerate(groups):
        end = index
        while end + 1 < len(groups) and float(groups[end + 1]["t"]) - float(group["t"]) <= window_ms:
            end += 1
        raw_notes = sum(int(groups[pos]["size"]) for pos in range(index, end + 1))
        if raw_notes > threshold:
            count += 1
    return count


def coverage(notes: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> tuple[int, int]:
    covered = 0
    for syllable in syllables:
        start = float(syllable.get("start_ms", 0.0))
        end = float(syllable.get("vocal_end_ms", start + 45.0))
        if any(start - 10.0 <= float(note.get("t", 0.0)) <= end + 20.0 or float(note.get("t", 0.0)) <= start <= float(note.get("t", 0.0)) + float(note.get("l", 0.0) or 0.0) for note in notes):
            covered += 1
    return covered, len(syllables)


def validate_song(song_dir: Path) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    errors: list[tuple[Any, ...]] = []
    chart = load(song_dir / "candidate-chart.json")
    alignment = load(song_dir / "syllable-alignment.json")
    syllables = alignment.get("syllables", [])
    duration = float(alignment.get("duration_ms", 0.0))
    if chart.get("generatedBy") != EXPECTED_GENERATED:
        errors.append((song_dir.name, "generatedBy", chart.get("generatedBy")))
    rows: dict[str, Any] = {}
    for difficulty in DIFFS:
        notes = chart.get("notes", {}).get(difficulty, [])
        if not isinstance(notes, list) or not notes:
            errors.append((song_dir.name, difficulty, "empty_notes"))
            continue
        previous = -1.0
        seen: set[tuple[float, int]] = set()
        for index, note in enumerate(notes):
            t = float(note.get("t", -1.0))
            d = int(note.get("d", -1))
            hold = float(note.get("l", 0.0) or 0.0)
            key = (round(t, 3), d)
            if key in seen:
                errors.append((song_dir.name, difficulty, index, "duplicate_t_d", key))
            seen.add(key)
            if t < previous:
                errors.append((song_dir.name, difficulty, index, "not_sorted", t, previous))
            previous = t
            if not 0.0 <= t < duration:
                errors.append((song_dir.name, difficulty, index, "note_out_of_audio", t, duration))
            if d not in {0, 1, 2, 3}:
                errors.append((song_dir.name, difficulty, index, "bad_player_lane", d))
            if hold < 0.0 or hold > 1800.0:
                errors.append((song_dir.name, difficulty, index, "hold_out_of_bounds", hold))
            if hold:
                covered_syllables = [item for item in syllables if float(item.get("start_ms", 0.0)) - 5.0 <= t + hold and float(item.get("start_ms", 0.0)) + float(item.get("vocal_end_ms", item.get("start_ms", 0.0))) * 0.0 >= -1]
                # The first predicate above selects syllables up to the hold;
                # the next check uses the actual measured endpoint of the group.
                in_span = [item for item in syllables if t - 5.0 <= float(item.get("start_ms", 0.0)) <= t + hold + 20.0]
                allowed_end = max((float(item.get("vocal_end_ms", t)) for item in in_span), default=t + hold)
                if t + hold > allowed_end + 45.0:
                    errors.append((song_dir.name, difficulty, index, "hold_exceeds_vocal_span", t, hold, allowed_end))
        groups = attack_groups(notes)
        dense_500 = dense_cluster_count(groups, 500.0, 2)
        dense_1000 = dense_cluster_count(groups, 1000.0, 3)
        if dense_500:
            errors.append((song_dir.name, difficulty, "clusters_gt2_in_500ms", dense_500))
        if dense_1000:
            errors.append((song_dir.name, difficulty, "clusters_gt3_in_1000ms", dense_1000))
        covered, total = coverage(notes, syllables)
        rows[difficulty] = {
            "notes": len(notes),
            "attack_groups": len(groups),
            "clusters_gt2_in_500ms": dense_500,
            "clusters_gt3_in_1000ms": dense_1000,
            "holds": sum(1 for note in notes if float(note.get("l", 0.0) or 0.0) > 0),
            "hold_max_ms": max((float(note.get("l", 0.0) or 0.0) for note in notes), default=0.0),
            "covered_syllables": covered,
            "syllables": total,
            "coverage_ratio": round(covered / max(1, total), 4),
            "lane_counts": {str(lane): sum(1 for note in notes if int(note.get("d", -1)) == lane) for lane in range(4)},
        }
    counts = {difficulty: len(chart.get("notes", {}).get(difficulty, [])) for difficulty in DIFFS}
    if not (counts["easy"] < counts["normal"] < counts["hard"]):
        errors.append((song_dir.name, "difficulty_progression", counts))
    return errors, {"song": song_dir.name, "difficulties": rows, "errors": len(errors)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    candidate_dir = args.candidate_dir.resolve()
    all_errors: list[tuple[Any, ...]] = []
    rows = []
    for song_dir in sorted(path for path in candidate_dir.iterdir() if path.is_dir()):
        errors, row = validate_song(song_dir)
        all_errors.extend(errors)
        rows.append(row)
    result = {
        "scope": "V271_DENSITY_AWARE_VOCAL_CANDIDATE_VALIDATION",
        "status": "PASS" if len(rows) == 21 and not all_errors else "FAIL",
        "songs": len(rows),
        "errors": all_errors,
        "rows": rows,
        "rules": {"player_lanes": "0..3", "max_clusters_gt2_in_500ms": 0, "max_clusters_gt3_in_1000ms": 0, "max_hold_ms": 1800.0, "difficulty_progression": "easy<normal<hard"},
    }
    output = candidate_dir / "batch-validation-v271.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "songs": result["songs"], "errors": len(all_errors), "output": str(output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
