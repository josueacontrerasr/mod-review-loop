#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIGN_ROOT = ROOT / "qa-lab/rebuild-v271/playstate-fix/alignment-source"
OUT_ROOT = ROOT / "qa-lab/rebuild-v271/playstate-fix/density-candidates"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")
PLAYER_LANES = {0, 1, 2, 3}
COLLISION_TOLERANCE_MS = 1.0
DENSE_500_MS = 500.0
DENSE_1000_MS = 1000.0
HOLD_MIN_MS = 120.0
HOLD_RELEASE_MARGIN_MS = 10.0
MAX_HOLD_MS = 1800.0
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.1 density-aware vocal clusters, retimed holds and player lanes d=0..3"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def group_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted((dict(note) for note in notes), key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1))))
    groups: list[dict[str, Any]] = []
    for note in ordered:
        t = float(note.get("t", 0.0))
        if not groups or t - float(groups[-1]["last_t"]) > COLLISION_TOLERANCE_MS:
            groups.append({"start_t": round(t, 3), "last_t": t, "notes": [note]})
        else:
            groups[-1]["last_t"] = t
            groups[-1]["notes"].append(note)
    for group in groups:
        group["end_t"] = round(max(float(note.get("t", 0.0)) + float(note.get("l", 0.0) or 0.0) for note in group["notes"]), 3)
        group["raw_count"] = len(group["notes"])
        group["lanes"] = sorted({int(note.get("d", -1)) for note in group["notes"]})
    return groups


def map_syllable(t: float, syllables: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not syllables:
        return None
    item = min(syllables, key=lambda row: abs(float(row.get("start_ms", 0.0)) - t))
    return item if abs(float(item.get("start_ms", 0.0)) - t) <= 1.5 else None


def holds_cover_group(group: dict[str, Any], syllables: list[dict[str, Any]]) -> bool:
    start = float(group["start_t"])
    for item in syllables:
        item_start = float(item.get("start_ms", 0.0))
        item_end = float(item.get("vocal_end_ms", item_start))
        if item_start <= start + 1.0 and item_end >= start + HOLD_MIN_MS:
            return True
    return False


def remove_internal_subdivisions(groups: list[dict[str, Any]], syllables: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    active_holds: list[tuple[float, float, int]] = []
    for group in groups:
        t = float(group["start_t"])
        is_subdivision = False
        for start, end, lane in active_holds:
            if start + 1.5 < t <= end + 1.0 and lane in set(group["lanes"]):
                is_subdivision = True
                break
        if is_subdivision:
            group["remove_reason"] = "hard_subdivision_inside_existing_vocal_hold"
            removed.append(group)
            continue
        kept.append(group)
        for note in group["notes"]:
            hold_end = float(note.get("t", t)) + float(note.get("l", 0.0) or 0.0)
            if hold_end >= t + HOLD_MIN_MS:
                active_holds.append((t, hold_end, int(note.get("d", -1))))
        active_holds = [entry for entry in active_holds if entry[1] >= t - 1.0]
    return kept, removed


def window_groups(groups: list[dict[str, Any]], start_index: int, window_ms: float) -> list[dict[str, Any]]:
    start_t = float(groups[start_index]["start_t"])
    return [group for group in groups[start_index:] if float(group["start_t"]) - start_t <= window_ms]


def choose_direction(group: dict[str, Any], syllables: list[dict[str, Any]], fallback: int) -> int:
    for note in group["notes"]:
        syllable = map_syllable(float(note.get("t", 0.0)), syllables)
        if syllable is not None:
            return int(note.get("d", fallback)) if int(note.get("d", -1)) in PLAYER_LANES else fallback % 4
    return int(group["notes"][0].get("d", fallback)) % 4


def representative_note(group: dict[str, Any], cluster: list[dict[str, Any]], syllables: list[dict[str, Any]], fallback: int, reason: str) -> dict[str, Any]:
    first = group["notes"][0]
    start = float(group["start_t"])
    direction = choose_direction(group, syllables, fallback)
    last_end = max(float(item.get("end_t", item.get("start_t", start))) for item in cluster)
    vocal_ends: list[float] = []
    for item in cluster:
        for note in item["notes"]:
            mapped = map_syllable(float(note.get("t", start)), syllables)
            if mapped is not None:
                vocal_ends.append(float(mapped.get("vocal_end_ms", mapped.get("start_ms", start))))
    target_end = max([last_end, *vocal_ends])
    hold = min(MAX_HOLD_MS, max(0.0, target_end - start - HOLD_RELEASE_MARGIN_MS))
    output: dict[str, Any] = {"t": round(start, 3), "d": int(direction)}
    if hold >= HOLD_MIN_MS:
        output["l"] = round(hold, 3)
    return output


def cap_groups(groups: list[dict[str, Any]], syllables: list[dict[str, Any]], window_ms: float, threshold: int, fallback_lane: int, reason: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reductions: list[dict[str, Any]] = []
    groups = list(groups)
    while True:
        violation: tuple[int, int, int] | None = None
        for index, group in enumerate(groups):
            end = index
            while end + 1 < len(groups) and float(groups[end + 1]["start_t"]) - float(group["start_t"]) <= window_ms:
                end += 1
            raw_count = sum(int(groups[pos]["raw_count"]) for pos in range(index, end + 1))
            if raw_count > threshold:
                violation = (index, end, raw_count)
                break
        if violation is None:
            return groups, reductions
        index, end, raw_count = violation
        cluster = groups[index:end + 1]
        if window_ms <= DENSE_500_MS:
            representative = representative_note(cluster[0], cluster, syllables, fallback_lane, reason)
            replacements = [{"start_t": representative["t"], "raw_count": 1, "notes": [representative], "end_t": round(float(representative["t"]) + float(representative.get("l", 0.0) or 0.0), 3), "lanes": [int(representative["d"])]}]
            reductions.append({"reason": reason, "start_ms": cluster[0]["start_t"], "end_ms": cluster[-1]["start_t"], "original_attack_groups": len(cluster), "original_raw_notes": raw_count, "kept_note": representative, "removed_timestamps": [item["start_t"] for item in cluster[1:]]})
            fallback_lane = (int(representative["d"]) + 1) % 4
        else:
            selected_positions = sorted({0, len(cluster) // 2, len(cluster) - 1})
            replacements = []
            for position, cluster_index in enumerate(selected_positions):
                group = cluster[cluster_index]
                note = dict(group["notes"][0])
                note["d"] = (int(note.get("d", fallback_lane)) + position) % 4
                replacements.append({"start_t": group["start_t"], "raw_count": 1, "notes": [note], "end_t": group["end_t"], "lanes": [int(note["d"])]})
            reductions.append({"reason": reason, "start_ms": cluster[0]["start_t"], "end_ms": cluster[-1]["start_t"], "original_attack_groups": len(cluster), "original_raw_notes": raw_count, "kept_timestamps": [item["start_t"] for item in replacements], "removed_timestamps": [item["start_t"] for position, item in enumerate(cluster) if position not in selected_positions]})
        groups = groups[:index] + replacements + groups[end + 1:]


def groups_to_notes(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    notes = sorted((dict(group["notes"][0]) for group in groups), key=lambda note: (float(note["t"]), int(note["d"])))
    occupied: set[tuple[float, int]] = set()
    output: list[dict[str, Any]] = []
    for note in notes:
        key = (round(float(note["t"]), 3), int(note["d"]))
        if key in occupied:
            continue
        occupied.add(key)
        output.append(note)
    return output


def reduce_density(groups: list[dict[str, Any]], syllables: list[dict[str, Any]], difficulty: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups, subdivision_removed = remove_internal_subdivisions(groups, syllables) if difficulty == "hard" else (groups, [])
    reductions: list[dict[str, Any]] = [{"reason": item.get("remove_reason"), "start_ms": item["start_t"], "raw_count": item["raw_count"]} for item in subdivision_removed]
    groups, local_reductions = cap_groups(groups, syllables, DENSE_500_MS, 2, 0, "dense_gt2_in_500ms_collapsed_to_one")
    reductions.extend(local_reductions)
    groups, broad_reductions = cap_groups(groups, syllables, DENSE_1000_MS, 3, 0, "dense_gt3_in_1000ms_reduced_to_three_spaced_directions")
    reductions.extend(broad_reductions)
    groups, final_local_reductions = cap_groups(groups, syllables, DENSE_500_MS, 2, 0, "dense_gt2_in_500ms_collapsed_after_1000ms_balance")
    reductions.extend(final_local_reductions)
    return groups_to_notes(groups), reductions


def add_safe_hard_subdivisions(notes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    additions: list[dict[str, Any]] = []
    ordered = sorted((dict(note) for note in notes), key=lambda note: float(note.get("t", 0.0)))
    occupied = {(round(float(note.get("t", 0.0)), 3), int(note.get("d", -1))) for note in ordered}
    for index, note in enumerate(ordered):
        hold = float(note.get("l", 0.0) or 0.0)
        if hold < 240.0:
            continue
        previous_t = float(ordered[index - 1].get("t", -10**9)) if index else -10**9
        next_t = float(ordered[index + 1].get("t", 10**9)) if index + 1 < len(ordered) else 10**9
        subdivision_t = round(float(note["t"]) + min(hold * 0.5, hold - 60.0), 3)
        if subdivision_t - previous_t < 500.0 or next_t - subdivision_t < 500.0:
            continue
        direction = (int(note.get("d", 0)) + 1) % 4
        key = (subdivision_t, direction)
        if key in occupied:
            continue
        extra = {"t": subdivision_t, "d": direction}
        ordered.append(extra)
        occupied.add(key)
        additions.append({"base_t": float(note["t"]), "subdivision_t": subdivision_t, "d": direction, "reason": "safe_hard_subdivision_inside_isolated_long_vocal_hold"})
    return sorted(ordered, key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1)))), additions


def balance_repeated_lanes(notes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted((dict(note) for note in notes), key=lambda note: (float(note.get("t", 0.0)), int(note.get("d", -1))))
    changes: list[dict[str, Any]] = []
    run_start = 0
    while run_start < len(ordered):
        lane = int(ordered[run_start].get("d", 0))
        run_end = run_start + 1
        while run_end < len(ordered) and int(ordered[run_end].get("d", -1)) == lane:
            run_end += 1
        run_length = run_end - run_start
        if run_length >= 5:
            for position in range(run_start + 1, run_end):
                old_lane = int(ordered[position].get("d", lane))
                new_lane = (lane + (position - run_start)) % 4
                ordered[position]["d"] = new_lane
                changes.append({"t": float(ordered[position].get("t", 0.0)), "from": old_lane, "to": new_lane, "reason": "repetition_balance_after_four_same_lane_attacks"})
        run_start = run_end
    return ordered, changes


def process_song(song: str) -> dict[str, Any]:
    source_chart = ROOT / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
    source_alignment = ALIGN_ROOT / song / "syllable-alignment.json"
    chart = read_json(source_chart)
    alignment = read_json(source_alignment)
    candidate_notes: dict[str, list[dict[str, Any]]] = {}
    reductions: dict[str, list[dict[str, Any]]] = {}
    original_counts: dict[str, int] = {}
    final_counts: dict[str, int] = {}
    normal_source = chart.get("notes", {}).get("normal", [])
    normal_notes, normal_reductions = reduce_density(group_notes(normal_source), alignment.get("syllables", []), "normal")
    normal_notes, normal_balance = balance_repeated_lanes(normal_notes)
    candidate_notes["normal"] = normal_notes
    reductions["normal"] = normal_reductions + normal_balance
    original_counts["normal"] = len(normal_source)
    final_counts["normal"] = len(normal_notes)
    easy_notes = [dict(note) for index, note in enumerate(normal_notes) if index % 2 == 0 or float(note.get("l", 0.0) or 0.0) >= 240.0]
    if len(easy_notes) >= len(normal_notes) and len(normal_notes) > 1:
        easy_notes = [dict(note) for index, note in enumerate(normal_notes) if index % 2 == 0]
    easy_hold_simplifications: list[dict[str, Any]] = []
    for note in easy_notes:
        hold = float(note.get("l", 0.0) or 0.0)
        if 0.0 < hold < 420.0:
            note.pop("l", None)
            easy_hold_simplifications.append({"t": float(note.get("t", 0.0)), "reason": "easy_short_hold_simplified_to_tap", "original_hold_ms": hold})
    easy_notes, easy_balance = balance_repeated_lanes(easy_notes)
    candidate_notes["easy"] = easy_notes
    reductions["easy"] = [{"reason": "easy_derived_from_density_capped_normal", "source_index": index, "kept": index % 2 == 0 or float(note.get("l", 0.0) or 0.0) >= 240.0} for index, note in enumerate(normal_notes) if index % 2 == 1 and not (float(note.get("l", 0.0) or 0.0) >= 240.0)] + easy_hold_simplifications + easy_balance
    original_counts["easy"] = len(chart.get("notes", {}).get("easy", []))
    final_counts["easy"] = len(easy_notes)
    hard_source = chart.get("notes", {}).get("hard", [])
    hard_notes, hard_reductions = reduce_density(group_notes(hard_source), alignment.get("syllables", []), "hard")
    hard_notes, hard_additions = add_safe_hard_subdivisions(hard_notes)
    hard_groups = group_notes(hard_notes)
    hard_groups, post_hard_reductions = cap_groups(hard_groups, alignment.get("syllables", []), DENSE_500_MS, 2, 0, "hard_post_subdivision_dense_gt2_in_500ms")
    hard_groups, post_hard_broad_reductions = cap_groups(hard_groups, alignment.get("syllables", []), DENSE_1000_MS, 3, 0, "hard_post_subdivision_dense_gt3_in_1000ms")
    hard_notes = groups_to_notes(hard_groups)
    hard_notes, hard_balance = balance_repeated_lanes(hard_notes)
    candidate_notes["hard"] = hard_notes
    reductions["hard"] = hard_reductions + hard_additions + post_hard_reductions + post_hard_broad_reductions + hard_balance
    original_counts["hard"] = len(hard_source)
    final_counts["hard"] = len(hard_notes)
    candidate_chart = {
        "version": "2.0.0",
        "scrollSpeed": chart.get("scrollSpeed", {"easy": 0.9, "normal": 1.0, "hard": 1.12}),
        "events": chart.get("events", []),
        "notes": candidate_notes,
        "generatedBy": EXPECTED_GENERATED,
    }
    candidate_alignment = dict(alignment)
    candidate_alignment["version"] = "V2.7.1"
    candidate_alignment["density_policy"] = {
        "dense_500_ms": ">2 attack groups collapsed to one representative arrow/hold",
        "dense_1000_ms": ">3 remaining attack groups reduced to three spaced directions",
        "hard_subdivisions": "removed when inside an existing vocal hold",
        "literal_submillisecond_offsets": "treated as collisions, not independent attacks",
        "production_untouched": True,
    }
    report = {
        "scope": "V271_DENSITY_AWARE_VOCAL_CANDIDATE",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": song,
        "base_chart": str(source_chart.relative_to(ROOT)),
        "base_generatedBy": chart.get("generatedBy"),
        "generatedBy": EXPECTED_GENERATED,
        "original_notes": original_counts,
        "candidate_notes": final_counts,
        "removed_notes": {difficulty: original_counts[difficulty] - final_counts[difficulty] for difficulty in DIFFS},
        "reductions": reductions,
        "total_reduction_events": sum(len(rows) for rows in reductions.values()),
        "candidate_policy": candidate_alignment["density_policy"],
    }
    destination = OUT_ROOT / song
    write_json(destination / "candidate-chart.json", candidate_chart)
    write_json(destination / "syllable-alignment.json", candidate_alignment)
    write_json(destination / "density-reduction-report.json", report)
    return {"song": song, "original_notes": original_counts, "candidate_notes": final_counts, "removed_notes": report["removed_notes"], "reduction_events": report["total_reduction_events"]}


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(process_song, SONGS))
    summary = {
        "scope": "WIDE_RESEARCH_V271_DENSITY_AWARE_CANDIDATES",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.6.7",
        "target_version": "2.7.1",
        "songs": len(rows),
        "parallel_workers": 8,
        "production_untouched": True,
        "original_notes": {difficulty: sum(int(row["original_notes"][difficulty]) for row in rows) for difficulty in DIFFS},
        "candidate_notes": {difficulty: sum(int(row["candidate_notes"][difficulty]) for row in rows) for difficulty in DIFFS},
        "removed_notes": {difficulty: sum(int(row["removed_notes"][difficulty]) for row in rows) for difficulty in DIFFS},
        "reduction_events": sum(int(row["reduction_events"]) for row in rows),
        "rows": sorted(rows, key=lambda row: row["song"]),
    }
    output = OUT_ROOT / "batch-summary-v271.json"
    write_json(output, summary)
    print(json.dumps({"scope": summary["scope"], "songs": summary["songs"], "original_notes": summary["original_notes"], "candidate_notes": summary["candidate_notes"], "removed_notes": summary["removed_notes"], "reduction_events": summary["reduction_events"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
