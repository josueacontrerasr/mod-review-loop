#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import json
import shutil
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
GENERATED_BY = "Friday Night Funkin' - 0.8.6"


def one(root: Path, stage: Path, song: str) -> dict[str, Any]:
    staged_path = stage / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
    candidate_path = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / song / "chart-vocal-only.json"
    production_path = root / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
    production = json.loads(production_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    staged = dict(production)
    staged["notes"] = {}
    for difficulty in DIFFICULTIES:
        staged["notes"][difficulty] = [{key: value for key, value in entry.items() if not key.startswith("_")} for entry in candidate.get("notes", {}).get(difficulty, [])]
    staged["version"] = production.get("version", "2.0.0")
    staged["scrollSpeed"] = production.get("scrollSpeed", {"easy": 0.9, "normal": 1.0, "hard": 1.12})
    staged["generatedBy"] = GENERATED_BY
    staged.pop("candidateOnly", None)
    staged.pop("sourcePolicy", None)
    staged_path.write_text(json.dumps(staged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = []
    if staged.get("events") != production.get("events"): errors.append("events_changed")
    if staged.get("timeChanges") != production.get("timeChanges"): errors.append("timeChanges_changed")
    if staged.get("scrollSpeed") != production.get("scrollSpeed"): errors.append("scrollSpeed_changed")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "errors": errors, "notes": {difficulty: len(staged["notes"].get(difficulty, [])) for difficulty in DIFFICULTIES}, "generatedBy": staged.get("generatedBy"), "preserved_events": not errors or "events_changed" not in errors, "preserved_timeChanges": "timeChanges_changed" not in errors, "preserved_scrollSpeed": "scrollSpeed_changed" not in errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    stage = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / "staged-mods"
    if stage.exists(): shutil.rmtree(stage)
    (stage / "mods").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "mods", stage / "mods")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: one(root, stage, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "VOCAL_ONLY_STAGING_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": "2.6.1-candidate", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "production_modified": False, "rows": rows, "policy": "staging only; only notes are replaced; generatedBy is retained for PlayState"}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / "staging-manifest-v261.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "production_modified": payload["production_modified"], "stage": str(stage), "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
