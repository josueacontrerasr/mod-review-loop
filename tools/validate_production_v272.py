#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SONGS = [p.name for p in sorted((ROOT / "mods").glob("esperon-dano-*/data/songs/*")) if p.is_dir()]
DIFFS = ("easy", "normal", "hard")
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.2 syllable-accurate vocal chart player lanes d=0..3"


def direction_errors(notes: list[dict[str, Any]], syllables: list[dict[str, Any]], allowed_balanced: set[float]) -> list[dict[str, Any]]:
    errors = []
    for index, note in enumerate(notes):
        t = float(note.get("t", -1.0))
        matches = [item for item in syllables if abs(float(item.get("start_ms", 0.0)) - t) <= 1.5]
        if not matches:
            continue
        if any(item.get("direction_policy") == "repetition-balance" or (item.get("primary_direction") is not None and int(item.get("primary_direction")) == int(note.get("d", -1))) for item in matches):
            continue
        item = max(matches, key=lambda row: float(row.get("vocal_end_ms", 0.0)))
        policy = item.get("direction_policy", "vowel-mapping")
        if policy == "repetition-balance" or round(t, 3) in allowed_balanced:
            continue
        expected = item.get("primary_direction", item.get("direction"))
        if expected is not None and int(note.get("d", -1)) != int(expected):
            errors.append({"index": index, "t": t, "expected": int(expected), "actual": int(note.get("d", -1)), "text": item.get("text")})
    return errors


def one(song: str) -> dict[str, Any]:
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    chart_path = mod / "data/songs" / song / f"{song}-chart.json"
    evidence_dir = ROOT / "qa-lab/rebuild-v272/playstate-fix/vocal-sync-candidates-canonical" / song
    align_path = evidence_dir / "syllable-alignment.json"
    reduction_path = evidence_dir / "vocal-sync-report.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    align = json.loads(align_path.read_text(encoding="utf-8"))
    reductions = json.loads(reduction_path.read_text(encoding="utf-8")) if reduction_path.is_file() else {"reductions": {}}
    syll = align.get("syllables", [])
    intervals = [(float(item.get("start_ms", 0.0)) - 45.0, float(item.get("vocal_end_ms", 0.0)) + 45.0) for item in syll]
    spans = [(float(item.get("start_ms", 0.0)) - 10.0, float(item.get("vocal_end_ms", 0.0)) + 20.0) for item in syll]
    starts = [float(item.get("start_ms", 0.0)) for item in syll]
    errors: list[str] = []
    counts: dict[str, int] = {}
    outside = 0
    leaked = 0
    bad_lanes = 0
    bad_holds = 0
    unaligned = 0
    vowel_mismatches = 0
    for diff in DIFFS:
        notes = chart.get("notes", {}).get(diff, [])
        counts[diff] = len(notes)
        if not notes or not {int(note.get("d", -1)) for note in notes}.issubset({0, 1, 2, 3}):
            errors.append(f"lane_coverage_not_player_0_3:{diff}")
        allowed_balanced: set[float] = set()
        for reduction in reductions.get("reductions", {}).get(diff, []):
            reason = str(reduction.get("reason", ""))
            if "repetition_balance" in reason or "repetition-balance" in reason or "spaced_directions" in reason or "safe_hard_subdivision" in reason or "dense_gt3" in reason:
                if reduction.get("t") is not None:
                    allowed_balanced.add(round(float(reduction["t"]), 3))
                if reduction.get("subdivision_t") is not None:
                    allowed_balanced.add(round(float(reduction["subdivision_t"]), 3))
                if reduction.get("kept_timestamps"):
                    allowed_balanced.update(round(float(value), 3) for value in reduction["kept_timestamps"])
                if reduction.get("kept_note"):
                    allowed_balanced.add(round(float(reduction["kept_note"].get("t", -1.0)), 3))
        if diff == "easy":
            normal_notes = chart.get("notes", {}).get("normal", [])
            for note in notes:
                t = float(note.get("t", -1.0)); d = int(note.get("d", -1))
                if any(abs(float(parent.get("t", -1.0)) - t) <= 1.5 and int(parent.get("d", -1)) == d for parent in normal_notes):
                    allowed_balanced.add(round(t, 3))
        for index, note in enumerate(notes):
            if set(note) - {"t", "d", "l", "k", "p"}:
                leaked += 1
            if not isinstance(note.get("d"), int) or not 0 <= int(note["d"]) <= 3:
                bad_lanes += 1
            t = float(note.get("t", -1.0))
            length = float(note.get("l", 0.0) or 0.0)
            if not any(start <= t <= end for start, end in intervals):
                outside += 1
            nearest = min((abs(t - start) for start in starts), default=99999.0)
            if nearest > 1.0 and not any(start <= t <= end for start, end in spans):
                unaligned += 1
            if length:
                end = t + length
                covered = [item for item in syll if t - 5.0 <= float(item.get("start_ms", 0.0)) <= end + 50.0]
                allowed_end = max((float(item.get("vocal_end_ms", t)) for item in covered), default=t)
                if end > allowed_end + 50.0:
                    bad_holds += 1
        vowel_mismatches += len(direction_errors(notes, syll, allowed_balanced))
    if outside:
        errors.append(f"notes_outside_syllable_intervals:{outside}")
    if unaligned:
        errors.append(f"notes_not_aligned_to_syllables:{unaligned}")
    if bad_holds:
        errors.append(f"holds_cross_vocal_boundary:{bad_holds}")
    if leaked:
        errors.append(f"candidate_metadata_leaked:{leaked}")
    if bad_lanes:
        errors.append(f"bad_player_lanes:{bad_lanes}")
    if vowel_mismatches:
        errors.append(f"vowel_direction_mismatches:{vowel_mismatches}")
    if not (counts["easy"] < counts["normal"] <= counts["hard"]):
        errors.append(f"density_not_progressive:{counts}")
    if chart.get("generatedBy") != EXPECTED_GENERATED:
        errors.append("chart_generatedBy_invalid")
    if chart.get("candidateOnly") is not None or chart.get("sourcePolicy") is not None:
        errors.append("candidate_fields_leaked")
    return {
        "song": song,
        "status": "PASS" if not errors else "ERRORS_FOUND",
        "counts": counts,
        "outside_syllable_intervals": outside,
        "unaligned_notes": unaligned,
        "bad_holds": bad_holds,
        "vowel_direction_mismatches": vowel_mismatches,
        "candidate_metadata_leaked": leaked,
        "bad_player_lanes": bad_lanes,
        "generatedBy": chart.get("generatedBy"),
        "errors": errors,
    }


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = sorted(pool.map(one, SONGS), key=lambda row: row["song"])
    payload = {
        "scope": "PRODUCTION_VOCAL_SYLLABLE_ACCURATE_GATE_V272",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "mod_version": "2.7.2",
        "songs": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "total_notes_outside_syllable_intervals": sum(row["outside_syllable_intervals"] for row in rows),
        "total_unaligned_notes": sum(row["unaligned_notes"] for row in rows),
        "total_bad_holds": sum(row["bad_holds"] for row in rows),
        "rows": rows,
    }
    output = ROOT / "qa-lab/rebuild-v272/playstate-fix/production-syllable-gate-v272.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "outside": payload["total_notes_outside_syllable_intervals"], "unaligned": payload["total_unaligned_notes"], "bad_holds": payload["total_bad_holds"], "output": str(output)}))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
