#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "qa-lab" / "rebuild-v267" / "playstate-fix" / "syllable-candidates-small"
SONGS = sorted(path for path in CAND.iterdir() if path.is_dir())
DIFFS = ("easy", "normal", "hard")
MAPPING = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return round(values[index], 3)


def max_run(notes: list[dict[str, Any]]) -> int:
    best = current = 0
    previous = None
    for note in notes:
        lane = int(note.get("d", -1))
        if lane == previous:
            current += 1
        else:
            current = 1
        previous = lane
        best = max(best, current)
    return best


def audit(path: Path) -> dict[str, Any]:
    align = json.loads((path / "syllable-alignment.json").read_text(encoding="utf-8"))
    chart = json.loads((path / "candidate-chart.json").read_text(encoding="utf-8"))
    syllables = align.get("syllables", [])
    durations = [float(item.get("duration_ms", 0.0) or 0.0) for item in syllables]
    holds = [float(item.get("hold_ms", 0.0) or 0.0) for item in syllables if float(item.get("hold_ms", 0.0) or 0.0) >= 120.0]
    balanced = [item for item in syllables if item.get("direction_policy") == "repetition-balance"]
    primary_mismatches = [item for item in balanced if item.get("vowel") in MAPPING and int(item.get("direction", -1)) == MAPPING[item.get("vowel")]]
    notes = chart.get("notes", {}).get("normal", [])
    return {
        "song": path.name,
        "syllables": len(syllables),
        "holds": len(holds),
        "hold_ratio": round(len(holds) / max(1, len(syllables)), 4),
        "hold_median_ms": percentile(holds, 0.5),
        "hold_p95_ms": percentile(holds, 0.95),
        "hold_max_ms": round(max(holds, default=0.0), 3),
        "duration_p95_ms": percentile(durations, 0.95),
        "balanced": len(balanced),
        "balanced_primary_collision": len(primary_mismatches),
        "normal_same_lane_max_run": max_run(notes),
        "normal_notes": len(notes),
        "direction_counts": {str(lane): sum(1 for note in notes if int(note.get("d", -1)) == lane) for lane in range(4)},
        "start_shift_median_ms": round(float(__import__("numpy").median([float(item.get("onset_delta_chart_minus_audio_ms", 0.0)) for item in syllables])), 3) if syllables else 0.0,
        "review": "WARNING_REVIEW" if len(holds) / max(1, len(syllables)) > 0.75 or max_run(notes) > 8 or len(primary_mismatches) else "PASS_AUTO",
    }


def main() -> int:
    rows = [audit(path) for path in SONGS]
    result = {
        "scope": "WIDE_RESEARCH_V267_CANDIDATE_HOLD_AND_LANE_QUALITY",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "songs": len(rows),
        "warnings": sum(row["review"] == "WARNING_REVIEW" for row in rows),
        "rows": rows,
    }
    output = CAND.parent / "candidate-quality-v267.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scope": result["scope"], "songs": result["songs"], "warnings": result["warnings"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
