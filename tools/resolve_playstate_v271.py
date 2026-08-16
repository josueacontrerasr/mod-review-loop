#!/usr/bin/env python3
"""Reproduce la resolución de SongRegistry/PlayState para default en V-Slice 0.8.6."""
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
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
DIFFICULTIES = ("easy", "normal", "hard")


def read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"json:{path.relative_to(path.parents[4])}:{exc}") from exc


def resolve_one(root: Path, song: str, variation: str = "default") -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    data_root = mod / "data" / "songs" / song
    suffix = "" if variation == "default" else f"-{variation}"
    metadata_path = data_root / f"{song}-metadata{suffix}.json"
    chart_path = data_root / f"{song}-chart{suffix}.json"
    errors: list[str] = []
    warnings: list[str] = []
    if not metadata_path.is_file(): errors.append(f"metadata_missing:{metadata_path.relative_to(root)}")
    if not chart_path.is_file(): errors.append(f"chart_missing:{chart_path.relative_to(root)}")
    if errors:
        return {"song": song, "variation": variation, "status": "ERROR", "errors": errors, "metadata_path": str(metadata_path.relative_to(root)), "chart_path": str(chart_path.relative_to(root))}
    metadata = read(metadata_path)
    chart = read(chart_path)
    required_metadata = ("version", "songName", "artist", "playData", "generatedBy", "timeChanges")
    required_chart = ("version", "scrollSpeed", "events", "notes", "generatedBy")
    for key in required_metadata:
        if key not in metadata: errors.append(f"metadata_required_missing:{key}")
    for key in required_chart:
        if key not in chart: errors.append(f"chart_required_missing:{key}")
    if metadata.get("version") != "2.2.4": errors.append(f"metadata_version:{metadata.get('version')}")
    if chart.get("version") != "2.0.0": errors.append(f"chart_version:{chart.get('version')}")
    if chart.get("generatedBy") != "Friday Night Funkin' - 0.8.6; V2.7.1 density-aware vocal clusters, retimed holds and player lanes d=0..3": errors.append("chart_generatedBy_invalid")
    play = metadata.get("playData", {})
    if not isinstance(play, dict):
        errors.append("playData_not_object")
        play = {}
    for key in ("difficulties", "characters", "stage", "noteStyle"):
        if key not in play: errors.append(f"playData_required_missing:{key}")
    variations = play.get("songVariations", [])
    if variations is None: variations = []
    if not isinstance(variations, list): errors.append("songVariations_not_array")
    elif variation != "default" and variation not in variations: errors.append(f"variation_not_declared:{variation}")
    notes = chart.get("notes", {})
    if not isinstance(notes, dict):
        errors.append("notes_not_object")
        notes = {}
    chart_difficulties = sorted(notes.keys())
    metadata_difficulties = sorted(play.get("difficulties", [])) if isinstance(play.get("difficulties", []), list) else []
    if metadata_difficulties != chart_difficulties: errors.append(f"difficulty_mismatch:metadata={metadata_difficulties},chart={chart_difficulties}")
    for difficulty in DIFFICULTIES:
        if difficulty not in notes: errors.append(f"difficulty_missing:{difficulty}")
        elif not isinstance(notes[difficulty], list): errors.append(f"difficulty_not_array:{difficulty}")
        else:
            if {int(note.get("d", -1)) for note in notes[difficulty]} != {0, 1, 2, 3}: errors.append(f"lane_coverage:{difficulty}")
            for index, note in enumerate(notes[difficulty]):
                if not isinstance(note, dict): errors.append(f"note_not_object:{difficulty}[{index}]"); continue
                if "t" not in note: errors.append(f"note_missing_t:{difficulty}[{index}]")
                if "d" not in note: errors.append(f"note_missing_d:{difficulty}[{index}]")
                if "t" in note and not isinstance(note["t"], (int, float)): errors.append(f"note_t_type:{difficulty}[{index}]")
                if "d" in note and (not isinstance(note["d"], int) or note["d"] < 0 or note["d"] > 3): errors.append(f"note_d_type_or_domain:{difficulty}[{index}]")
    manifest_path = data_root / "manifest.json"
    if not manifest_path.is_file(): errors.append(f"song_manifest_missing:{manifest_path.relative_to(root)}")
    else:
        manifest = read(manifest_path)
        if manifest.get("songId") != song: errors.append(f"songId_mismatch:{manifest.get('songId')}")
    return {
        "song": song, "variation": variation, "status": "PASS" if not errors else "ERROR",
        "errors": errors, "warnings": warnings,
        "metadata_path": str(metadata_path.relative_to(root)), "chart_path": str(chart_path.relative_to(root)),
        "metadata_generatedBy": metadata.get("generatedBy"), "chart_generatedBy": chart.get("generatedBy"),
        "metadata_difficulties": metadata_difficulties, "chart_difficulties": chart_difficulties,
        "notes": {difficulty: len(notes.get(difficulty, [])) for difficulty in DIFFICULTIES},
        "variation_resolution": "base filenames for default" if variation == "default" else f"suffix -{variation}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--variations", nargs="+", default=["default"])
    args = parser.parse_args()
    root = args.root.resolve()
    jobs = [(song, variation) for song in SONGS for variation in args.variations]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        song_rows = list(pool.map(lambda job: resolve_one(root, job[0], job[1]), jobs))
    rows = [{**row, "difficulty": difficulty} for row in song_rows for difficulty in DIFFICULTIES]
    payload = {
        "scope": "PLAYSTATE_VARIATION_RESOLVER_V271",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "variations": args.variations,
        "songs": len(SONGS),
        "song_cases": len(song_rows),
        "cases": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "failed": sum(row["status"] == "ERROR" for row in rows),
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND",
        "rows": rows,
        "engine_contract": {"default_metadata": "<id>-metadata.json", "default_chart": "<id>-chart.json", "variation_metadata": "<id>-metadata-<variation>.json", "variation_chart": "<id>-chart-<variation>.json", "required_chart_generatedBy": True},
    }
    output = root / "qa-lab" / "rebuild-v271" / "playstate-fix" / "playstate-resolver-production-v271.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": payload["cases"], "passed": payload["passed"], "failed": payload["failed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
