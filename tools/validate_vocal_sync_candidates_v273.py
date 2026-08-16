from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-candidates"
DIFFS = ("easy", "normal", "hard")
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.3 calibrated vocal onsets, syllable-accurate holds and player lanes d=0..3"
ENGINE_COLLISION_MS = 12.0
GROUP_COLLISION_MS = 1.0
MAX_HOLD_MS = 1800.0
HOLD_MIN_MS = 180.0
NORMAL_COVERAGE_MIN = 0.90
HARD_COVERAGE_MIN = 0.90


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def attack_groups(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for note in sorted(notes, key=lambda value: (float(value.get("t", 0.0)), int(value.get("d", -1)))):
        t = float(note.get("t", 0.0))
        if not groups or t - float(groups[-1]["last_t"]) > GROUP_COLLISION_MS:
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
        start = float(syllable.get("audio_onset_ms", syllable.get("start_ms", 0.0)))
        end = float(syllable.get("vocal_end_ms", start + 45.0))
        if any(
            start - 10.0 <= float(note.get("t", 0.0)) <= end + 20.0
            or float(note.get("t", 0.0)) <= start <= float(note.get("t", 0.0)) + float(note.get("l", 0.0) or 0.0)
            for note in notes
        ):
            covered += 1
    return covered, len(syllables)


def nearest_syllable(t: float, syllables: list[dict[str, Any]], tolerance: float = 15.0) -> dict[str, Any] | None:
    if not syllables:
        return None
    item = min(syllables, key=lambda row: abs(float(row.get("audio_onset_ms", row.get("start_ms", 0.0))) - t))
    onset = float(item.get("audio_onset_ms", item.get("start_ms", 0.0)))
    return item if abs(onset - t) <= tolerance else None


def validate_song(song_dir: Path) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    errors: list[tuple[Any, ...]] = []
    chart = load(song_dir / "candidate-chart.json")
    alignment = load(song_dir / "syllable-alignment.json")
    report = load(song_dir / "vocal-sync-report.json")
    syllables = alignment.get("syllables", [])
    duration = float(alignment.get("duration_ms", 0.0))
    if chart.get("generatedBy") != EXPECTED_GENERATED:
        errors.append((song_dir.name, "generatedBy", chart.get("generatedBy")))
    if report.get("generatedBy") != EXPECTED_GENERATED:
        errors.append((song_dir.name, "report_generatedBy", report.get("generatedBy")))
    rows: dict[str, Any] = {}
    for difficulty in DIFFS:
        notes = chart.get("notes", {}).get(difficulty, [])
        if not isinstance(notes, list) or not notes:
            errors.append((song_dir.name, difficulty, "empty_notes"))
            continue
        previous = -1.0
        seen_exact: set[tuple[float, int]] = set()
        lane_times: dict[int, list[float]] = {lane: [] for lane in range(4)}
        note_outside_vocal = 0
        invalid_hold_kinds = 0
        for index, note in enumerate(notes):
            t = float(note.get("t", -1.0))
            d = int(note.get("d", -1))
            hold = float(note.get("l", 0.0) or 0.0)
            key = (round(t, 3), d)
            if key in seen_exact:
                errors.append((song_dir.name, difficulty, index, "duplicate_t_d", key))
            seen_exact.add(key)
            if t < previous:
                errors.append((song_dir.name, difficulty, index, "not_sorted", t, previous))
            previous = t
            if not 0.0 <= t < duration:
                errors.append((song_dir.name, difficulty, index, "note_out_of_audio", t, duration))
            if d not in {0, 1, 2, 3}:
                errors.append((song_dir.name, difficulty, index, "bad_player_lane", d))
            else:
                lane_times[d].append(t)
            if hold < 0.0 or hold > MAX_HOLD_MS:
                errors.append((song_dir.name, difficulty, index, "hold_out_of_bounds", hold))
            syllable = nearest_syllable(t, syllables)
            if syllable is None and difficulty != "hard":
                note_outside_vocal += 1
                errors.append((song_dir.name, difficulty, index, "note_not_near_vocal_attack", t))
            if hold > 0.0:
                if hold < HOLD_MIN_MS:
                    errors.append((song_dir.name, difficulty, index, "hold_below_minimum", hold))
                if syllable is None:
                    errors.append((song_dir.name, difficulty, index, "hold_without_vocal_attack", t, hold))
                else:
                    kind = str(syllable.get("kind", ""))
                    if kind not in {"sustained_syllable", "interjection_hold"}:
                        invalid_hold_kinds += 1
                        errors.append((song_dir.name, difficulty, index, "hold_on_non_sustained_kind", kind, t))
                    start = float(syllable.get("audio_onset_ms", syllable.get("start_ms", t)))
                    audio_end = float(syllable.get("audio_end_ms", syllable.get("vocal_end_ms", start)))
                    allowed_end = min(audio_end, start + MAX_HOLD_MS)
                    if t + hold > allowed_end + 45.0:
                        errors.append((song_dir.name, difficulty, index, "hold_exceeds_vocal_span", t, hold, allowed_end))
        collision_count = 0
        for lane, times in lane_times.items():
            for left, right in zip(times, times[1:]):
                if 0.0 < right - left < ENGINE_COLLISION_MS:
                    collision_count += 1
                    errors.append((song_dir.name, difficulty, "same_lane_under_12ms", lane, left, right, right-left))
        groups = attack_groups(notes)
        dense_500 = dense_cluster_count(groups, 500.0, 2)
        dense_1000 = dense_cluster_count(groups, 1000.0, 3)
        # There is intentionally no dense_500 failure in V2.7.3: 2–3 Spanish syllables
        # in 500 ms are valid separate attacks. The metric remains observable in reports.
        # V2.7.3 reports dense windows but does not delete valid vocal attacks.
        # This prevents the former 500/1000 ms policy from turning syllables into holds.
        covered, total = coverage(notes, syllables)
        coverage_ratio = round(covered / max(1, total), 4)
        min_coverage = NORMAL_COVERAGE_MIN if difficulty == "normal" else HARD_COVERAGE_MIN if difficulty == "hard" else 0.0
        if coverage_ratio < min_coverage:
            errors.append((song_dir.name, difficulty, "coverage_below_minimum", coverage_ratio, min_coverage))
        rows[difficulty] = {
            "notes": len(notes),
            "attack_groups": len(groups),
            "clusters_gt2_in_500ms_observed": dense_500,
            "clusters_gt3_in_1000ms_observed": dense_1000,
            "same_lane_under_12ms": collision_count,
            "holds": sum(1 for note in notes if float(note.get("l", 0.0) or 0.0) > 0),
            "invalid_hold_kinds": invalid_hold_kinds,
            "hold_max_ms": max((float(note.get("l", 0.0) or 0.0) for note in notes), default=0.0),
            "notes_outside_vocal_attack": note_outside_vocal,
            "covered_syllables": covered,
            "syllables": total,
            "coverage_ratio": coverage_ratio,
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
        "scope": "V273_CALIBRATED_VOCAL_ONSET_CANDIDATE_VALIDATION",
        "status": "PASS" if len(rows) == 21 and not all_errors else "FAIL",
        "songs": len(rows),
        "errors": all_errors,
        "rows": rows,
        "rules": {
            "player_lanes": "0..3",
            "dense_500_ms": "observed only; no collapse failure",
            "clusters_gt3_in_1000ms": "observed_only_no_deletion",
            "engine_same_lane_collision_ms": 12.0,
            "max_hold_ms": MAX_HOLD_MS,
            "hold_min_ms": HOLD_MIN_MS,
            "normal_min_coverage": NORMAL_COVERAGE_MIN,
            "hard_min_coverage": HARD_COVERAGE_MIN,
            "difficulty_progression": "easy<normal<hard",
        },
    }
    output = candidate_dir / "batch-validation-v273.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "songs": result["songs"], "errors": len(all_errors), "output": str(output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
