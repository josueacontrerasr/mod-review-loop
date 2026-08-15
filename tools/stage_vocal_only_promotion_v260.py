#!/usr/bin/env python3
"""Aplica candidatos vocal-only a un árbol staging, nunca a producción."""
from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    stage = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "staged-mods"
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(root / "mods", stage / "mods")
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for song in SONGS:
        production_path = stage / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
        candidate_path = root / "qa-lab" / "rebuild-v260" / "vocal-only" / song / "chart-vocal-only.json"
        production = json.loads(production_path.read_text(encoding="utf-8"))
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        staged = dict(production)
        staged["notes"] = {}
        for difficulty in DIFFICULTIES:
            staged["notes"][difficulty] = []
            for entry in candidate.get("notes", {}).get(difficulty, []):
                clean = {key: value for key, value in entry.items() if not key.startswith("_")}
                staged["notes"][difficulty].append(clean)
        staged["version"] = production.get("version", "2.0.0")
        staged["scrollSpeed"] = candidate.get("scrollSpeed", production.get("scrollSpeed", {}))
        staged.pop("candidateOnly", None)
        staged.pop("generatedBy", None)
        staged.pop("sourcePolicy", None)
        production_path.write_text(json.dumps(staged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if staged.get("events") != production.get("events"):
            errors.append(f"{song}:events_changed")
        if staged.get("timeChanges") != production.get("timeChanges"):
            errors.append(f"{song}:timeChanges_changed")
        rows.append({"song": song, "production_chart": str(production_path.relative_to(stage)), "candidate_chart": str(candidate_path.relative_to(root)), "notes": {difficulty: len(staged["notes"].get(difficulty, [])) for difficulty in DIFFICULTIES}, "preserved_events": True, "preserved_timeChanges": True})
    manifest = {"scope": "VOCAL_ONLY_STAGING_V260", "executed_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "status": "PASS" if not errors else "ERRORS_FOUND", "production_modified": False, "rows": rows, "errors": errors, "policy": "Staging only; production mods are untouched."}
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "staging-manifest-v260.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": manifest["songs"], "status": manifest["status"], "production_modified": manifest["production_modified"], "stage": str(stage), "output": str(output)}, ensure_ascii=False))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
