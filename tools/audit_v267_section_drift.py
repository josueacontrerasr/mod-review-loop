#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = ROOT / "qa-lab" / "rebuild-v266" / "playstate-fix" / "syllable-candidates-small"
NEW_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "playstate-fix" / "syllable-candidates-small"
AUDIO_ROOT = ROOT / "qa-lab" / "rebuild-v267" / "phase2-vocal-onsets"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "si-te-vas", "solare",
    "tristella", "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(abs(value) for value in values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return round(ordered[index], 3)


def section(rows: list[dict[str, Any]], start: int, end: int) -> dict[str, Any]:
    old_errors = [float(row.get("chart_start_ms", 0.0)) - float(row.get("audio_onset_ms", 0.0)) for row in rows[start:end]]
    new_errors = [float(row.get("candidate_start_ms", 0.0)) - float(row.get("audio_onset_ms", 0.0)) for row in rows[start:end]]
    end_errors = [float(row.get("candidate_end_ms", 0.0)) - float(row.get("audio_end_ms", 0.0)) for row in rows[start:end]]
    return {
        "count": len(old_errors),
        "old_median_error_ms": round(median(old_errors), 3) if old_errors else 0.0,
        "old_p95_abs_error_ms": pct(old_errors, 0.95),
        "new_median_error_ms": round(median(new_errors), 3) if new_errors else 0.0,
        "new_p95_abs_error_ms": pct(new_errors, 0.95),
        "new_max_abs_error_ms": pct(new_errors, 1.0),
        "candidate_end_p95_abs_error_ms": pct(end_errors, 0.95),
    }


def audit_song(song: str) -> dict[str, Any]:
    old = json.loads((OLD_ROOT / song / "syllable-alignment.json").read_text(encoding="utf-8"))
    new = json.loads((NEW_ROOT / song / "syllable-alignment.json").read_text(encoding="utf-8"))
    audio = json.loads((AUDIO_ROOT / f"{song}.json").read_text(encoding="utf-8"))
    old_items = old.get("syllables", [])
    new_items = new.get("syllables", [])
    audio_rows = audio.get("rows", [])
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(new_items):
        acoustic = audio_rows[index] if index < len(audio_rows) else {}
        old_item = old_items[index] if index < len(old_items) else {}
        rows.append({
            "index": index,
            "chart_start_ms": float(old_item.get("start_ms", 0.0)),
            "candidate_start_ms": float(item.get("start_ms", 0.0)),
            "audio_onset_ms": float(acoustic.get("audio_onset_ms", item.get("start_ms", 0.0))),
            "candidate_end_ms": float(item.get("vocal_end_ms", 0.0)),
            "audio_end_ms": float(acoustic.get("audio_end_ms", item.get("vocal_end_ms", 0.0))),
            "text": item.get("text"),
            "duration_ms": float(item.get("duration_ms", 0.0)),
            "hold_ms": float(item.get("hold_ms", 0.0) or 0.0),
        })
    count = len(rows)
    boundaries = [0, max(1, count // 4), max(1, count // 2), max(1, 3 * count // 4), count]
    sections = {
        "start": section(rows, boundaries[0], boundaries[1]),
        "early_middle": section(rows, boundaries[1], boundaries[2]),
        "late_middle": section(rows, boundaries[2], boundaries[3]),
        "end": section(rows, boundaries[3], boundaries[4]),
    }
    samples = [rows[index] for index in sorted(set([0, max(0, count // 2), max(0, count - 1)]))] if rows else []
    return {
        "song": song,
        "syllables": count,
        "sections": sections,
        "samples": samples,
        "old_global_median_error_ms": round(median([row["chart_start_ms"] - row["audio_onset_ms"] for row in rows]), 3) if rows else 0.0,
        "new_global_median_error_ms": round(median([row["candidate_start_ms"] - row["audio_onset_ms"] for row in rows]), 3) if rows else 0.0,
        "new_global_p95_abs_error_ms": pct([row["candidate_start_ms"] - row["audio_onset_ms"] for row in rows], 0.95),
        "new_end_p95_abs_error_ms": pct([row["candidate_end_ms"] - row["audio_end_ms"] for row in rows], 0.95),
        "long_hold_samples": sorted((row for row in rows if row["hold_ms"] >= 600.0), key=lambda row: row["hold_ms"], reverse=True)[:10],
    }


def main() -> int:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(audit_song, SONGS))
    result = {
        "scope": "WIDE_RESEARCH_V267_SECTION_DRIFT_AND_ANCHOR_AUDIT",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "songs": len(rows),
        "parallel_workers": 8,
        "old_global_median_abs_ms": round(median(abs(row["old_global_median_error_ms"]) for row in rows), 3),
        "new_global_median_abs_ms": round(median(abs(row["new_global_median_error_ms"]) for row in rows), 3),
        "new_global_p95_abs_ms": max(row["new_global_p95_abs_error_ms"] for row in rows),
        "rows": sorted(rows, key=lambda row: row["song"]),
    }
    output = ROOT / "qa-lab" / "rebuild-v267" / "phase5-section-drift-v267.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scope": result["scope"], "songs": result["songs"], "old_global_median_abs_ms": result["old_global_median_abs_ms"], "new_global_median_abs_ms": result["new_global_median_abs_ms"], "new_global_p95_abs_ms": result["new_global_p95_abs_ms"], "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
