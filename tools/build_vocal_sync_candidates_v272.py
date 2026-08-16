from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIGN_ROOT = ROOT / "qa-lab/rebuild-v271/playstate-fix/alignment-source"
OUT_ROOT = ROOT / "qa-lab/rebuild-v272/playstate-fix/vocal-sync-candidates"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")
PLAYER_LANES = {0, 1, 2, 3}
MAPPING = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
COLLISION_TOLERANCE_MS = 1.0
ENGINE_COLLISION_MS = 12.0
DENSE_1000_MS = 1000.0
DENSE_1000_THRESHOLD = 3
HOLD_MIN_MS = 180.0
HARD_SUBDIVISION_MIN_HOLD_MS = 180.0
HARD_SUBDIVISION_MIN_GAP_MS = 90.0
HOLD_RELEASE_MARGIN_MS = 15.0
MAX_HOLD_MS = 1800.0
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.2 syllable-accurate vocal chart player lanes d=0..3"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mapped_direction(vowel: str, fallback: int) -> int:
    return MAPPING.get(str(vowel or "").lower(), fallback % 4)


def choose_directions(syllables: list[dict[str, Any]]) -> tuple[list[int], int]:
    directions: list[int] = []
    previous_primary: int | None = None
    run_length = 0
    balanced = 0
    for index, item in enumerate(syllables):
        primary = mapped_direction(str(item.get("vowel", "")), index)
        if primary == previous_primary:
            run_length += 1
        else:
            run_length = 1
        direction = primary
        if run_length >= 2 and str(item.get("vowel", "")).lower() in MAPPING:
            direction = (primary + run_length - 1) % 4
            if directions and direction == directions[-1]:
                direction = (direction + 1) % 4
            if direction != primary:
                balanced += 1
        directions.append(direction)
        previous_primary = primary
    return directions, balanced


def measured_hold(item: dict[str, Any], next_start: float) -> float:
    kind = str(item.get("kind", ""))
    measured = float(item.get("hold_ms", 0.0) or 0.0)
    start = float(item.get("start_ms", 0.0))
    audio_end = float(item.get("audio_end_ms", item.get("vocal_end_ms", start)))
    # Alignment marks only sustained syllables/interjection holds with hold evidence.
    if kind not in {"sustained_syllable", "interjection_hold"}:
        return 0.0
    if measured < HOLD_MIN_MS or audio_end - start < HOLD_MIN_MS:
        return 0.0
    boundary = min(audio_end - start, measured, MAX_HOLD_MS)
    if next_start < start + boundary + HOLD_RELEASE_MARGIN_MS:
        boundary = next_start - start - HOLD_RELEASE_MARGIN_MS
    return round(max(0.0, boundary), 3) if boundary >= HOLD_MIN_MS else 0.0


def make_note(item: dict[str, Any], direction: int, next_start: float, subdivision: bool = False) -> dict[str, Any]:
    start = round(float(item.get("start_ms", 0.0)), 3)
    note: dict[str, Any] = {"t": start, "d": int(direction)}
    if not subdivision:
        hold = measured_hold(item, next_start)
        if hold >= HOLD_MIN_MS:
            note["l"] = hold
    return note


def build_base_notes(syllables: list[dict[str, Any]], directions: list[int], difficulty: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[tuple[int, dict[str, Any], bool]] = []
    if difficulty == "easy":
        for index, item in enumerate(syllables):
            hold = float(item.get("hold_ms", 0.0) or 0.0)
            kind = str(item.get("kind", ""))
            if index % 2 == 0 or kind.startswith("interjection") or hold >= 360.0:
                selected.append((index, item, False))
    else:
        selected = [(index, item, False) for index, item in enumerate(syllables)]

    notes: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []
    occupied: list[tuple[float, int]] = []
    for index, item, subdivision in selected:
        next_start = float(syllables[index + 1].get("start_ms", 10**12)) if index + 1 < len(syllables) else 10**12
        note = make_note(item, directions[index], next_start, subdivision=subdivision)
        collision = next((old for old in occupied if old[1] == int(note["d"]) and 0.0 <= float(note["t"]) - old[0] < ENGINE_COLLISION_MS), None)
        if collision is not None:
            # A sub-12 ms duplicate cannot be independently readable by the engine.
            report.append({"reason": "sub_12ms_same_lane_collision_deduplicated", "t": note["t"], "d": note["d"], "kept_t": collision[0]})
            continue
        occupied.append((float(note["t"]), int(note["d"])))
        notes.append(note)
    return sorted(notes, key=lambda note: (float(note["t"]), int(note["d"]))), report


def attack_groups(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for note in sorted(notes, key=lambda row: (float(row.get("t", 0.0)), int(row.get("d", -1)))):
        t = float(note.get("t", 0.0))
        if not groups or t - float(groups[-1]["last_t"]) > COLLISION_TOLERANCE_MS:
            groups.append({"start_t": round(t, 3), "last_t": t, "notes": [note]})
        else:
            groups[-1]["last_t"] = t
            groups[-1]["notes"].append(note)
    for group in groups:
        group["raw_count"] = len(group["notes"])
        group["end_t"] = round(max(float(note.get("t", 0.0)) + float(note.get("l", 0.0) or 0.0) for note in group["notes"]), 3)
        group["lanes"] = sorted({int(note.get("d", -1)) for note in group["notes"]})
    return groups


def cap_dense_1000(groups: list[dict[str, Any]], fallback_lane: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Reduce only truly dense >3-attack windows to three separate notes.

    This pass deliberately never creates a representative hold. The 500 ms collapse
    from V2.7.1 is removed so normal Spanish syllable spacing remains playable.
    """
    groups = list(groups)
    reductions: list[dict[str, Any]] = []
    while True:
        violation = None
        for index, group in enumerate(groups):
            end = index
            while end + 1 < len(groups) and float(groups[end + 1]["start_t"]) - float(group["start_t"]) <= DENSE_1000_MS:
                end += 1
            raw_count = sum(int(groups[pos]["raw_count"]) for pos in range(index, end + 1))
            if raw_count > DENSE_1000_THRESHOLD:
                violation = (index, end, raw_count)
                break
        if violation is None:
            return groups, reductions
        index, end, raw_count = violation
        cluster = groups[index:end + 1]
        positions = sorted({0, len(cluster) // 2, len(cluster) - 1})
        replacements: list[dict[str, Any]] = []
        kept_timestamps: list[float] = []
        removed_timestamps: list[float] = []
        for position, group in enumerate(cluster):
            if position not in positions:
                removed_timestamps.append(float(group["start_t"]))
                continue
            note = dict(group["notes"][0])
            note["d"] = (int(note.get("d", fallback_lane)) + position) % 4
            replacements.append({
                "start_t": group["start_t"],
                "last_t": group["start_t"],
                "raw_count": 1,
                "notes": [note],
                "end_t": group["end_t"],
                "lanes": [int(note["d"])],
            })
            kept_timestamps.append(float(group["start_t"]))
        reductions.append({
            "reason": "dense_gt3_in_1000ms_reduced_to_three_separate_attacks",
            "start_ms": cluster[0]["start_t"],
            "end_ms": cluster[-1]["start_t"],
            "original_attack_groups": len(cluster),
            "original_raw_notes": raw_count,
            "kept_timestamps": kept_timestamps,
            "removed_timestamps": removed_timestamps,
        })
        groups = groups[:index] + replacements + groups[end + 1:]


def groups_to_notes(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    notes = sorted((dict(group["notes"][0]) for group in groups), key=lambda note: (float(note["t"]), int(note["d"])))
    occupied: list[tuple[float, int]] = []
    output: list[dict[str, Any]] = []
    for note in notes:
        t = float(note["t"])
        d = int(note["d"])
        if any(old_d == d and 0.0 <= t - old_t < ENGINE_COLLISION_MS for old_t, old_d in occupied):
            continue
        occupied.append((t, d))
        output.append(note)
    return output


def apply_density_policy(notes: list[dict[str, Any]], difficulty: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # V2.7.2 deliberately preserves all measured vocal attacks. The prior 500 ms
    # collapse caused Fal-tan and similar Spanish syllable pairs to become one hold;
    # the 1000 ms redistribution also reduced measured syllable coverage. Extreme
    # engine collisions are handled at note construction, not by deleting attacks.
    return sorted((dict(note) for note in notes), key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1)))), []


def add_hard_subdivisions(notes: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted((dict(note) for note in notes), key=lambda note: float(note.get("t", 0.0)))
    additions: list[dict[str, Any]] = []
    occupied = [(float(note.get("t", 0.0)), int(note.get("d", -1))) for note in ordered]
    for index, note in enumerate(list(ordered)):
        hold = float(note.get("l", 0.0) or 0.0)
        if hold < HARD_SUBDIVISION_MIN_HOLD_MS:
            continue
        start = float(note["t"])
        next_t = float(ordered[index + 1].get("t", 10**12)) if index + 1 < len(ordered) else 10**12
        subdivision_t = round(start + min(hold * 0.5, hold - 60.0), 3)
        if subdivision_t - start < HARD_SUBDIVISION_MIN_GAP_MS or next_t - subdivision_t < HARD_SUBDIVISION_MIN_GAP_MS:
            continue
        direction = (int(note.get("d", 0)) + 1) % 4
        if any(old_d == direction and abs(subdivision_t - old_t) < ENGINE_COLLISION_MS for old_t, old_d in occupied):
            continue
        extra = {"t": subdivision_t, "d": direction}
        ordered.append(extra)
        occupied.append((subdivision_t, direction))
        additions.append({"base_t": start, "subdivision_t": subdivision_t, "d": direction, "reason": "hard_subdivision_inside_isolated_measured_vocal_hold"})
    return sorted(ordered, key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1)))), additions


def process_song(song: str) -> dict[str, Any]:
    source_chart_path = ROOT / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
    source_alignment_path = ALIGN_ROOT / song / "syllable-alignment.json"
    chart = read_json(source_chart_path)
    alignment = read_json(source_alignment_path)
    syllables = sorted((dict(item) for item in alignment.get("syllables", [])), key=lambda item: float(item.get("start_ms", 0.0)))
    directions, balanced_count = choose_directions(syllables)
    candidate_notes: dict[str, list[dict[str, Any]]] = {}
    reductions: dict[str, list[dict[str, Any]]] = {}
    original_counts: dict[str, int] = {}
    final_counts: dict[str, int] = {}

    normal_base, normal_collisions = build_base_notes(syllables, directions, "normal")
    normal_notes, normal_density = apply_density_policy(normal_base, "normal")
    candidate_notes["normal"] = normal_notes
    reductions["normal"] = normal_collisions + normal_density
    original_counts["normal"] = len(chart.get("notes", {}).get("normal", []))
    final_counts["normal"] = len(normal_notes)

    easy_base, easy_collisions = build_base_notes(syllables, directions, "easy")
    easy_notes, easy_density = apply_density_policy(easy_base, "easy")
    reductions["easy"] = easy_collisions + easy_density
    if len(easy_notes) >= len(normal_notes) and len(normal_notes) > 1:
        easy_notes = [dict(note) for index, note in enumerate(normal_notes) if index % 2 == 0]
        reductions["easy"].append({"reason": "easy_fallback_every_other_normal_attack"})
    candidate_notes["easy"] = easy_notes
    original_counts["easy"] = len(chart.get("notes", {}).get("easy", []))
    final_counts["easy"] = len(easy_notes)

    hard_base, hard_collisions = build_base_notes(syllables, directions, "hard")
    hard_notes, hard_density = apply_density_policy(hard_base, "hard")
    hard_notes, hard_additions = add_hard_subdivisions(hard_notes, syllables)
    hard_notes, hard_post_density = apply_density_policy(hard_notes, "hard")
    if len(hard_notes) <= len(normal_notes) and len(normal_notes) > 1:
        hard_notes = sorted(hard_notes, key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1))))
    candidate_notes["hard"] = hard_notes
    reductions["hard"] = hard_collisions + hard_density + hard_additions + hard_post_density
    original_counts["hard"] = len(chart.get("notes", {}).get("hard", []))
    final_counts["hard"] = len(hard_notes)

    # If an unusual song still has no Hard additions, use the full syllable set (never move attacks).
    if final_counts["hard"] <= final_counts["normal"] and len(syllables) > len(normal_notes):
        hard_full, hard_full_collisions = build_base_notes(syllables, directions, "normal")
        hard_full, hard_full_density = apply_density_policy(hard_full, "hard")
        if len(hard_full) > final_counts["normal"]:
            candidate_notes["hard"] = hard_full
            final_counts["hard"] = len(hard_full)
            reductions["hard"].extend(hard_full_collisions + hard_full_density + [{"reason": "hard_fallback_full_vocal_attack_set"}])

    candidate_chart = {
        "version": "2.0.0",
        "scrollSpeed": chart.get("scrollSpeed", {"easy": 0.9, "normal": 1.0, "hard": 1.12}),
        "events": chart.get("events", []),
        "notes": candidate_notes,
        "generatedBy": EXPECTED_GENERATED,
    }
    candidate_alignment = dict(alignment)
    candidate_alignment["version"] = "V2.7.2"
    candidate_alignment["syllables"] = syllables
    candidate_alignment["chart_policy"] = "one vocal attack per aligned syllable; no 500ms or 1000ms density deletion; measured holds only for sustained_syllable/interjection_hold"
    candidate_alignment["density_policy"] = {
        "dense_500_ms": "not collapsed; two or three Spanish syllables in 500ms remain separate attacks",
        "dense_1000_ms": "observed only; all measured vocal attacks are preserved",
        "engine_collision_ms": ENGINE_COLLISION_MS,
        "holds": "only alignment kinds sustained_syllable/interjection_hold with measured hold >= 180ms, bounded by vocal end and next attack",
        "hard_subdivisions": "added only inside measured holds >= 180ms and rechecked for collision",
        "player_lanes": "d=0..3",
        "production_untouched": True,
    }
    report = {
        "scope": "V272_SYLLABLE_ACCURATE_VOCAL_CANDIDATE",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": song,
        "base_chart": str(source_chart_path.relative_to(ROOT)),
        "alignment_source": str(source_alignment_path.relative_to(ROOT)),
        "voice_sha256": alignment.get("voice_sha256"),
        "generatedBy": EXPECTED_GENERATED,
        "original_notes": original_counts,
        "candidate_notes": final_counts,
        "removed_notes": {difficulty: original_counts[difficulty] - final_counts[difficulty] for difficulty in DIFFS},
        "aligned_syllables": len(syllables),
        "direction_balance_changes": balanced_count,
        "reductions": reductions,
        "total_reduction_events": sum(len(rows) for rows in reductions.values()),
        "candidate_policy": candidate_alignment["density_policy"],
        "production_untouched": True,
    }
    destination = OUT_ROOT / song
    write_json(destination / "candidate-chart.json", candidate_chart)
    write_json(destination / "syllable-alignment.json", candidate_alignment)
    write_json(destination / "vocal-sync-report.json", report)
    return {"song": song, "aligned_syllables": len(syllables), "original_notes": original_counts, "candidate_notes": final_counts, "reduction_events": report["total_reduction_events"]}


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(process_song, SONGS))
    summary = {
        "scope": "WIDE_RESEARCH_V272_SYLLABLE_ACCURATE_VOCAL_CANDIDATES",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.7.1",
        "target_version": "2.7.2",
        "songs": len(rows),
        "parallel_workers": 8,
        "production_untouched": True,
        "aligned_syllables": sum(int(row["aligned_syllables"]) for row in rows),
        "candidate_notes": {difficulty: sum(int(row["candidate_notes"][difficulty]) for row in rows) for difficulty in DIFFS},
        "rows": sorted(rows, key=lambda row: row["song"]),
    }
    output = OUT_ROOT / "batch-summary-v272.json"
    write_json(output, summary)
    print(json.dumps({"scope": summary["scope"], "songs": summary["songs"], "aligned_syllables": summary["aligned_syllables"], "candidate_notes": summary["candidate_notes"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
