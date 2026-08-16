#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "qa-lab" / "rebuild-v266" / "playstate-fix" / "syllable-candidates-small"
AUDIO_ANALYSIS_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "phase2-vocal-onsets"
OUT_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "playstate-fix" / "syllable-candidates-small"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFS = ("easy", "normal", "hard")
MAPPING = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
MIN_SYLLABLE_SPACING_MS = 28.0
HOLD_MIN_MS = 180.0
HOLD_RELEASE_MARGIN_MS = 30.0
MAX_HOLD_MS = 1800.0


def mapped_direction(vowel: str, fallback: int) -> int:
    return MAPPING.get(str(vowel or "").lower(), fallback % 4)


def balance_directions(syllables: list[dict[str, Any]]) -> tuple[list[int], int]:
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
            if direction == directions[-1]:
                direction = (direction + 1) % 4
            if direction != primary:
                balanced += 1
        directions.append(direction)
        previous_primary = primary
    return directions, balanced


def make_note(item: dict[str, Any], direction: int, subdivision: bool = False) -> dict[str, Any]:
    note: dict[str, Any] = {"t": round(float(item["start_ms"]), 3), "d": int(direction)}
    hold = 0.0 if subdivision else float(item.get("hold_ms", 0.0) or 0.0)
    if hold >= 120.0:
        note["l"] = round(hold, 3)
    return note


def build_notes(syllables: list[dict[str, Any]], directions: list[int], difficulty: str) -> list[dict[str, Any]]:
    if difficulty == "easy":
        selected = [(index, item, False) for index, item in enumerate(syllables) if index % 2 == 0 or item.get("kind", "").startswith("interjection") or float(item.get("hold_ms", 0.0) or 0.0) >= 200.0]
    elif difficulty == "hard":
        selected = []
        for index, item in enumerate(syllables):
            selected.append((index, item, False))
            hold = float(item.get("hold_ms", 0.0) or 0.0)
            if hold >= 180.0:
                extra = dict(item)
                extra["start_ms"] = round(float(item["start_ms"]) + min(hold * 0.5, hold - 40.0), 3)
                extra["hold_ms"] = 0.0
                extra["kind"] = "hard_vocal_subdivision"
                selected.append((index, extra, True))
    else:
        selected = [(index, item, False) for index, item in enumerate(syllables)]
    notes: list[dict[str, Any]] = []
    occupied: set[tuple[float, int]] = set()
    for index, item, subdivision in selected:
        direction = directions[index]
        note = make_note(item, direction, subdivision)
        while (round(float(note["t"]), 3), int(note["d"])) in occupied:
            item = dict(item)
            item["start_ms"] = round(float(item["start_ms"]) + 0.5, 3)
            note = make_note(item, direction, subdivision)
        occupied.add((round(float(note["t"]), 3), int(note["d"])))
        notes.append(note)
    return sorted(notes, key=lambda note: (float(note["t"]), int(note["d"])))


def rebuild_song(song: str) -> dict[str, Any]:
    source = SRC_ROOT / song / "syllable-alignment.json"
    analysis = AUDIO_ANALYSIS_ROOT / f"{song}.json"
    alignment = json.loads(source.read_text(encoding="utf-8"))
    acoustic = json.loads(analysis.read_text(encoding="utf-8"))
    acoustic_rows = acoustic.get("rows", [])
    syllables = []
    start_shift: list[float] = []
    old_hold_count = 0
    new_hold_count = 0
    for index, old in enumerate(alignment.get("syllables", [])):
        row = acoustic_rows[index] if index < len(acoustic_rows) else {}
        old_start = float(old.get("start_ms", 0.0))
        audio_start = float(row.get("audio_onset_ms", old_start))
        item = dict(old)
        item["start_ms"] = round(audio_start, 3)
        item["audio_onset_ms"] = round(audio_start, 3)
        item["onset_delta_chart_minus_audio_ms"] = round(old_start - audio_start, 3)
        item["vocal_end_ms"] = round(float(row.get("audio_end_ms", old.get("vocal_end_ms", old_start + 45.0))), 3)
        item["audio_end_ms"] = item["vocal_end_ms"]
        item["vocal_end_source"] = "v267-rms-vad-last-active"
        item["source"] = "cached-whisper+rms-vad-onset-end-v267"
        old_hold_count += int(float(old.get("hold_ms", 0.0) or 0.0) >= 120.0)
        syllables.append(item)
        start_shift.append(round(audio_start - old_start, 3))
    syllables.sort(key=lambda item: float(item.get("start_ms", 0.0)))
    # Resolve acoustic overlaps deterministically while preserving the first
    # measured onset. This prevents a late syllable from being pushed into the
    # previous note's time because of a stale Whisper collision.
    for index, item in enumerate(syllables):
        if index and float(item["start_ms"]) < float(syllables[index - 1]["start_ms"]) + MIN_SYLLABLE_SPACING_MS:
            item["start_ms"] = round(float(syllables[index - 1]["start_ms"]) + MIN_SYLLABLE_SPACING_MS, 3)
        next_start = float(syllables[index + 1]["start_ms"]) if index + 1 < len(syllables) else float(acoustic.get("duration_ms", 0.0))
        end = min(float(item.get("vocal_end_ms", item["start_ms"] + 45.0)), next_start - HOLD_RELEASE_MARGIN_MS, float(item["start_ms"]) + MAX_HOLD_MS)
        end = max(float(item["start_ms"]) + 45.0, end)
        duration = round(max(0.0, end - float(item["start_ms"])), 3)
        item["vocal_end_ms"] = round(end, 3)
        item["duration_ms"] = duration
        item["hold_ms"] = round(max(0.0, duration - HOLD_RELEASE_MARGIN_MS), 3) if duration >= HOLD_MIN_MS else 0.0
        item["hold_policy"] = "measured-rms-vad-with-next-attack-boundary" if item["hold_ms"] else "tap-short-or-ambiguous"
        if item["hold_ms"]:
            item["kind"] = "interjection_hold" if item.get("kind", "").startswith("interjection") else "sustained_syllable"
        new_hold_count += int(item["hold_ms"] >= 120.0)
    directions, balanced_count = balance_directions(syllables)
    for item, direction in zip(syllables, directions):
        item["primary_direction"] = mapped_direction(str(item.get("vowel", "")), 0)
        item["direction"] = direction
        item["direction_policy"] = "vowel-mapping" if direction == item["primary_direction"] else "repetition-balance"
    charts = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": {difficulty: build_notes(syllables, directions, difficulty) for difficulty in DIFFS},
        "generatedBy": "Friday Night Funkin' - 0.8.6; V2.6.7 vocal RMS-VAD retimed holds and repetition-balanced player lanes d=0..3",
    }
    destination = OUT_ROOT / song
    destination.mkdir(parents=True, exist_ok=True)
    alignment["version"] = "V2.6.7"
    alignment["syllables"] = syllables
    alignment["chart_policy"] = "one vocal attack per syllable; RMS-VAD endings; holds bounded by next attack; repetition balance only for repeated vowel runs"
    (destination / "syllable-alignment.json").write_text(json.dumps(alignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destination / "candidate-chart.json").write_text(json.dumps(charts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "scope": "VOCAL_SYLLABLE_RMS_VAD_RETIMED_VOWEL_BALANCED_CANDIDATE_V267",
        "status": "MANUAL_REVIEW_REQUIRED",
        "song": song,
        "voice": alignment.get("voice"),
        "voice_sha256": alignment.get("voice_sha256"),
        "syllables": len(syllables),
        "old_hold_count": old_hold_count,
        "new_hold_count": new_hold_count,
        "hold_count_delta": new_hold_count - old_hold_count,
        "repetition_balance_notes": balanced_count,
        "start_shift_median_ms": sorted(start_shift)[len(start_shift) // 2] if start_shift else 0.0,
        "start_shift_p95_abs_ms": sorted(abs(value) for value in start_shift)[int(max(0, len(start_shift) * 0.95 - 1))] if start_shift else 0.0,
        "notes": {difficulty: len(charts["notes"][difficulty]) for difficulty in DIFFS},
        "policy": [
            "Player notes use d=0..3.",
            "A=0, E=2, I=3, O/U=1 as primary direction mapping.",
            "Repeated same-vowel attacks use deterministic repetition balance after the first attack.",
            "Holds use RMS-VAD end evidence, 30 ms release margin and next-attack boundary.",
            "Hard subdivisions inherit their parent direction and vocal interval.",
            "Production is not modified by this candidate build.",
        ],
    }
    (destination / "candidate-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        reports = list(pool.map(rebuild_song, SONGS))
    summary = {
        "scope": "WIDE_RESEARCH_V267_RMS_VAD_RETIMED_BALANCED_CANDIDATES",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_release": "esperon-vslice-086-v2.6.6",
        "target_version": "2.6.7",
        "songs": len(reports),
        "parallel_workers": 8,
        "old_holds": sum(int(report["old_hold_count"]) for report in reports),
        "new_holds": sum(int(report["new_hold_count"]) for report in reports),
        "repetition_balance_notes": sum(int(report["repetition_balance_notes"]) for report in reports),
        "reports": sorted(reports, key=lambda row: row["song"]),
        "production_untouched": True,
    }
    output = OUT_ROOT / "batch-summary-v267.json"
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scope": summary["scope"], "songs": summary["songs"], "old_holds": summary["old_holds"], "new_holds": summary["new_holds"], "balanced": summary["repetition_balance_notes"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
