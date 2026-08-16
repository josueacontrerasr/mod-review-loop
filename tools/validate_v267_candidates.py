#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_DIR = ROOT / "qa-lab" / "rebuild-v267" / "playstate-fix" / "syllable-candidates-small"
DIFFS = ("easy", "normal", "hard")
MAPPING = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.6.7 vocal RMS-VAD retimed holds and repetition-balanced player lanes d=0..3"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def direction_errors(notes: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    anchors = sorted({round(float(item["start_ms"]), 3) for item in syllables})
    expected: dict[float, Counter[int]] = {anchor: Counter() for anchor in anchors}
    actual: dict[float, Counter[int]] = {anchor: Counter() for anchor in anchors}
    for item in syllables:
        anchor = min(anchors, key=lambda value: abs(value - float(item["start_ms"])))
        expected[anchor][int(item.get("direction", -1))] += 1
    errors: list[tuple[Any, ...]] = []
    for index, note in enumerate(notes):
        t = float(note["t"])
        exact = [anchor for anchor in anchors if abs(anchor - t) <= 0.05]
        if exact:
            anchor = min(exact, key=lambda value: abs(value - t))
            actual[anchor][int(note["d"])] += 1
            continue
        # 0.5 ms collision offsets and Hard subdivisions inherit the parent.
        if any(abs(anchor - t) <= 1.0 for anchor in anchors):
            continue
        containing = [item for item in syllables if float(item["start_ms"]) <= t <= float(item.get("vocal_end_ms", item["start_ms"])) + 20.0]
        if containing and int(note["d"]) not in {int(item.get("direction", -1)) for item in containing}:
            errors.append((index, "direction_not_in_containing_vocal_interval", sorted({int(item.get("direction", -1)) for item in containing}), int(note["d"])))
    for anchor, values in actual.items():
        for direction, count in values.items():
            if count > expected[anchor].get(direction, 0):
                errors.append((anchor, "direction_count_exceeds_aligned_attack", direction, count, expected[anchor].get(direction, 0)))
    return errors


def validate_alignment(song: str, align: dict[str, Any], chart: dict[str, Any]) -> list[tuple[Any, ...]]:
    errors: list[tuple[Any, ...]] = []
    syllables = align.get("syllables", [])
    duration = float(align.get("duration_ms", 0.0))
    starts = sorted(float(item.get("start_ms", 0.0)) for item in syllables)
    for index, item in enumerate(syllables):
        vowel = str(item.get("vowel", "")).lower()
        direction = int(item.get("direction", -1))
        primary = MAPPING.get(vowel)
        if direction not in range(0, 4):
            errors.append((song, "syllable_bad_direction", index, direction))
        if primary is not None and direction != primary and item.get("direction_policy") != "repetition-balance":
            errors.append((song, "unexplained_direction_balance", index, vowel, primary, direction))
        if float(item.get("vocal_end_ms", 0.0)) < float(item.get("start_ms", 0.0)) + 45.0:
            errors.append((song, "syllable_end_before_minimum_span", index))
    for diff in DIFFS:
        notes = chart.get("notes", {}).get(diff)
        if not isinstance(notes, list) or not notes:
            errors.append((song, diff, "missing_or_empty_notes"))
            continue
        lane_set = {int(note.get("d", -1)) for note in notes}
        if not lane_set.issubset({0, 1, 2, 3}):
            errors.append((song, diff, "bad_player_lane_domain", sorted(lane_set)))
        if lane_set != {0, 1, 2, 3}:
            errors.append((song, diff, "incomplete_player_lane_coverage", sorted(lane_set)))
        seen: set[tuple[float, int]] = set()
        previous_time = -1.0
        for index, note in enumerate(notes):
            t = float(note.get("t", -1.0))
            direction = int(note.get("d", -1))
            hold = float(note.get("l", 0.0) or 0.0)
            key = (round(t, 3), direction)
            if key in seen:
                errors.append((song, diff, index, "duplicate_t_d", key))
            seen.add(key)
            if t < previous_time:
                errors.append((song, diff, index, "not_sorted", t, previous_time))
            previous_time = t
            if not (0.0 <= t < duration):
                errors.append((song, diff, index, "note_out_of_audio", t, duration))
            if hold < 0 or hold > 1800.0:
                errors.append((song, diff, index, "hold_out_of_bounds", hold))
            if hold:
                item = min(syllables, key=lambda candidate: abs(float(candidate.get("start_ms", 0.0)) - t))
                expected_end = float(item.get("vocal_end_ms", t))
                if t + hold > expected_end + 35.0:
                    errors.append((song, diff, index, "hold_exceeds_measured_vocal_end", t, hold, expected_end))
                next_start = next((start for start in starts if start > t + 1.0), duration)
                if t + hold > next_start - 10.0:
                    errors.append((song, diff, index, "hold_crosses_next_attack", t, hold, next_start))
        errors.extend((song, diff, *error) for error in direction_errors(notes, syllables))
    counts = {diff: len(chart.get("notes", {}).get(diff, [])) for diff in DIFFS}
    if not (counts["easy"] < counts["normal"] <= counts["hard"]):
        errors.append((song, "difficulty_density_progression", counts))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, default=DEFAULT_CANDIDATE_DIR)
    args = parser.parse_args()
    candidate_dir = args.candidate_dir.resolve()
    errors: list[tuple[Any, ...]] = []
    rows: list[dict[str, Any]] = []
    songs = sorted(path for path in candidate_dir.iterdir() if path.is_dir())
    for song_dir in songs:
        align = load(song_dir / "syllable-alignment.json")
        chart = load(song_dir / "candidate-chart.json")
        if chart.get("generatedBy") != EXPECTED_GENERATED:
            errors.append((song_dir.name, "generatedBy_invalid", chart.get("generatedBy")))
        song_errors = validate_alignment(song_dir.name, align, chart)
        errors.extend(song_errors)
        rows.append({
            "song": song_dir.name,
            "syllables": len(align.get("syllables", [])),
            "holds": sum(1 for item in align.get("syllables", []) if float(item.get("hold_ms", 0.0) or 0.0) >= 120.0),
            "balanced": sum(1 for item in align.get("syllables", []) if item.get("direction_policy") == "repetition-balance"),
            "notes": {diff: len(chart.get("notes", {}).get(diff, [])) for diff in DIFFS},
            "errors": sum(1 for error in song_errors if error and error[0] == song_dir.name),
        })
    result = {
        "scope": "V267_RMS_VAD_RETIMED_BALANCED_CANDIDATE_VALIDATION",
        "status": "PASS" if len(songs) == 21 and not errors else "FAIL",
        "songs": len(songs),
        "errors": errors,
        "rows": rows,
        "rules": {
            "player_lanes": "d=0..3",
            "primary_vowel_mapping": MAPPING,
            "balanced_direction_policy": "repetition-balance only",
            "max_hold_ms": 1800.0,
            "hold_end_margin_ms": 35.0,
            "difficulties": list(DIFFS),
        },
    }
    output = candidate_dir.parent / "syllable-candidates-small-validation-v267.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "songs": len(songs), "errors": len(errors), "output": str(output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
