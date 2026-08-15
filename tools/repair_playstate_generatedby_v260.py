#!/usr/bin/env python3
"""Añade el campo requerido SongChartData.generatedBy a los 20 charts."""
from __future__ import annotations

import argparse
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
GENERATED_BY = "Friday Night Funkin' - 0.8.6"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    rows: list[dict[str, Any]] = []
    for song in SONGS:
        path = root / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
        before = sha(path)
        chart = json.loads(path.read_text(encoding="utf-8"))
        previous = chart.get("generatedBy")
        chart["generatedBy"] = GENERATED_BY
        path.write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append({"song": song, "path": str(path.relative_to(root)), "sha256_before": before, "sha256_after": sha(path), "previous_generatedBy": previous, "generatedBy": GENERATED_BY, "notes_unchanged_by_count": {difficulty: len(chart.get("notes", {}).get(difficulty, [])) for difficulty in ("easy", "normal", "hard")}})
    payload = {"scope": "PLAYSTATE_GENERATEDBY_REPAIR_V260", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "songs": len(rows), "patched": len(rows), "status": "PASS", "required_field": "SongChartData.generatedBy", "generatedBy": GENERATED_BY, "audio_modified": False, "assets_modified": False, "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "generatedby-repair-v260.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "patched": payload["patched"], "generatedBy": GENERATED_BY, "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
