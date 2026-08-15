#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
DIFFICULTIES = ("easy", "normal", "hard")


def one(root: Path, song: str) -> dict[str, Any]:
    base = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / song
    activity = json.loads((base / "voice-activity.json").read_text(encoding="utf-8"))
    chart = json.loads((base / "chart-vocal-only.json").read_text(encoding="utf-8"))
    segments = [(float(row["start_ms"]), float(row["end_ms"])) for row in activity.get("segments", [])]
    errors: list[str] = []
    counts: dict[str, int] = {}
    outside: dict[str, int] = {}
    for difficulty in DIFFICULTIES:
        notes = chart.get("notes", {}).get(difficulty, [])
        counts[difficulty] = len(notes)
        outside[difficulty] = sum(1 for note in notes if not any(start - 45.0 <= float(note["t"]) <= end + 45.0 for start, end in segments))
        if outside[difficulty]: errors.append(f"outside_segments:{difficulty}:{outside[difficulty]}")
        for index, note in enumerate(notes):
            if set(note) - {"t", "d", "_source", "_voice_event_id"}: errors.append(f"candidate_metadata_leaked:{difficulty}:{index}")
            if note.get("_source") != "voice": errors.append(f"candidate_source_missing:{difficulty}:{index}")
            if not isinstance(note.get("t"), (int, float)): errors.append(f"bad_time:{difficulty}:{index}")
            if not isinstance(note.get("d"), int) or not 0 <= note["d"] <= 3: errors.append(f"bad_player_lane:{difficulty}:{index}")
    if not (counts["easy"] < counts["normal"] <= counts["hard"]): errors.append(f"density_not_progressive:{counts}")
    if chart.get("sourcePolicy") != "NO_INSTRUMENTAL_NOTES": errors.append("source_policy_missing")
    if chart.get("candidateOnly") is not True: errors.append("candidate_only_missing")
    if activity.get("source_policy") != "VOICE_ONLY; all timestamps derive from Voices-*.ogg": errors.append("activity_policy_missing")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "counts": counts, "outside_segments": outside, "segment_count": len(segments), "sourcePolicy": chart.get("sourcePolicy"), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "VOCAL_ALIGNED_CANDIDATE_GATE_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "total_outside_segment_notes": sum(sum(row["outside_segments"].values()) for row in rows), "rows": rows, "instrumental_used": False}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / "candidate-gate-v261.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "total_outside_segment_notes": payload["total_outside_segment_notes"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
