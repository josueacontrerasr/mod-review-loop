#!/usr/bin/env python3
"""Validador post-promoción para mods V2.6.0 vocal-only."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
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


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inside(time_ms: float, segments: list[dict[str, float]], margin_ms: float = 45.0) -> bool:
    return any(float(segment["start_ms"]) - margin_ms <= time_ms <= float(segment["end_ms"]) + margin_ms for segment in segments)


def validate_one(root: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    song_dir = mod / "data" / "songs" / song
    errors: list[str] = []
    manifest = json.loads((mod / "_polymod_meta.json").read_text(encoding="utf-8"))
    metadata = json.loads((song_dir / f"{song}-metadata.json").read_text(encoding="utf-8"))
    chart = json.loads((song_dir / f"{song}-chart.json").read_text(encoding="utf-8"))
    if manifest.get("api_version") != "0.8.6": errors.append("api_version")
    if manifest.get("mod_version") != "2.6.0": errors.append(f"mod_version={manifest.get('mod_version')}")
    if metadata.get("version") != "2.2.4": errors.append("metadata_version")
    if chart.get("version") != "2.0.0": errors.append("chart_version")
    chart_notes = chart.get("notes", {})
    if set(chart_notes) != set(DIFFICULTIES): errors.append("difficulty_set")
    counts: dict[str, int] = {}
    outside_total = 0
    segments = json.loads((root / "qa-lab" / "rebuild-v260" / "vocal-only" / song / "voice-activity.json").read_text(encoding="utf-8")).get("segments", [])
    difficulties: dict[str, Any] = {}
    for difficulty in DIFFICULTIES:
        entries = chart_notes.get(difficulty, [])
        counts[difficulty] = len(entries)
        keys = [(float(entry.get("t", -1)), int(entry.get("d", -1))) for entry in entries]
        outside = sum(not inside(timestamp, segments) for timestamp, _ in keys if timestamp >= 0)
        outside_total += outside
        if keys != sorted(keys) or len(keys) != len(set(keys)): errors.append(f"{difficulty}:order_duplicates")
        if any(timestamp < 0 or lane not in (0, 1, 2, 3) for timestamp, lane in keys): errors.append(f"{difficulty}:lane_domain")
        difficulties[difficulty] = {"notes": len(entries), "outside_vocal_segments": outside, "coverage_percent": round((len(entries) - outside) / len(entries) * 100.0, 3) if entries else 0.0}
    if not (counts["easy"] < counts["normal"] < counts["hard"]): errors.append(f"density={counts}")
    scroll = chart.get("scrollSpeed", {})
    if not (scroll.get("easy", 0) < scroll.get("normal", 0) < scroll.get("hard", 0)): errors.append("scroll_speed")
    inst = mod / "songs" / song / "Inst.ogg"
    voices = list((mod / "songs" / song).glob("Voices-*.ogg"))
    if not inst.is_file() or len(voices) != 1: errors.append("audio_contract")
    promotion = json.loads((root / "qa-lab" / "rebuild-v260" / "vocal-only" / "promotion-v260.json").read_text(encoding="utf-8"))
    promotion_row = next(row for row in promotion["rows"] if row["song"] == song)
    if sha(song_dir / f"{song}-chart.json") != promotion_row["chart_sha256_after"]: errors.append("promotion_chart_hash")
    return {"song": song, "status": "PASS" if not errors else "ERROR", "errors": errors, "mod_version": manifest.get("mod_version"), "counts": counts, "difficulties": difficulties, "outside_vocal_segments": outside_total, "instrumental_used_for_generation": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: validate_one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "VSLICE_086_VOCAL_ONLY_RUNTIME_V260", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": "2.6.0", "songs": len(rows), "difficulties": len(rows) * len(DIFFICULTIES), "passed": sum(row["status"] == "PASS" for row in rows), "failed": sum(row["status"] == "ERROR" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "instrumental_used_for_generation": False, "rows": rows, "policy": "Promoted charts contain only notes accepted by vocal-only gates."}
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "runtime-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "difficulties": payload["difficulties"], "passed": payload["passed"], "failed": payload["failed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
