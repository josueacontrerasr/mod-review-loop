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
    mod = root / "mods" / f"esperon-dano-{song}"
    chart_path = mod / "data" / "songs" / song / f"{song}-chart.json"
    activity_path = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / song / "voice-activity.json"
    chart = json.loads(chart_path.read_text(encoding="utf-8"))
    activity = json.loads(activity_path.read_text(encoding="utf-8"))
    segments = [(float(row["start_ms"]), float(row["end_ms"])) for row in activity["segments"]]
    errors: list[str] = []
    counts: dict[str, int] = {}
    outside = 0
    leaked = 0
    bad_lanes = 0
    for diff in DIFFICULTIES:
        notes = chart.get("notes", {}).get(diff, [])
        counts[diff] = len(notes)
        for index, note in enumerate(notes):
            if set(note) - {"t", "d", "l", "k", "p"}: leaked += 1
            if not isinstance(note.get("d"), int) or not 0 <= note["d"] <= 3: bad_lanes += 1
            if not any(start - 45.0 <= float(note.get("t", -1)) <= end + 45.0 for start, end in segments): outside += 1
    if outside: errors.append(f"notes_outside_vocal_segments:{outside}")
    if leaked: errors.append(f"candidate_metadata_leaked:{leaked}")
    if bad_lanes: errors.append(f"bad_player_lanes:{bad_lanes}")
    if not (counts["easy"] < counts["normal"] <= counts["hard"]): errors.append(f"density_not_progressive:{counts}")
    if chart.get("generatedBy") != "Friday Night Funkin' - 0.8.6": errors.append("chart_generatedBy_invalid")
    if chart.get("candidateOnly") is not None or chart.get("sourcePolicy") is not None: errors.append("candidate_fields_leaked")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "counts": counts, "outside_vocal_segments": outside, "candidate_metadata_leaked": leaked, "bad_player_lanes": bad_lanes, "generatedBy": chart.get("generatedBy"), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "PRODUCTION_VOCAL_ONLY_RUNTIME_GATE_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": "2.6.1", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "total_notes_outside_vocal_segments": sum(row["outside_vocal_segments"] for row in rows), "total_candidate_metadata_leaked": sum(row["candidate_metadata_leaked"] for row in rows), "total_bad_player_lanes": sum(row["bad_player_lanes"] for row in rows), "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "production-vocal-gate-v261.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "outside": payload["total_notes_outside_vocal_segments"], "metadata_leaked": payload["total_candidate_metadata_leaked"], "bad_lanes": payload["total_bad_player_lanes"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
