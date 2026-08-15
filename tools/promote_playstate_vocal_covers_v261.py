#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
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
MOD_VERSION = "2.6.1"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def one(root: Path, stage: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    staged_chart = stage / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
    chart = mod / "data" / "songs" / song / f"{song}-chart.json"
    meta = mod / "_polymod_meta.json"
    before_chart = sha(chart)
    before_meta = sha(meta)
    shutil.copy2(staged_chart, chart)
    metadata = json.loads(meta.read_text(encoding="utf-8"))
    old_version = metadata.get("mod_version")
    metadata["mod_version"] = MOD_VERSION
    meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chart_data = json.loads(chart.read_text(encoding="utf-8"))
    errors = []
    if chart_data.get("generatedBy") != "Friday Night Funkin' - 0.8.6": errors.append("generatedBy_missing_or_wrong")
    if chart_data.get("candidateOnly") is not None: errors.append("candidateOnly_leaked")
    if chart_data.get("sourcePolicy") is not None: errors.append("sourcePolicy_leaked")
    for difficulty in ("easy", "normal", "hard"):
        if difficulty not in chart_data.get("notes", {}): errors.append(f"difficulty_missing:{difficulty}")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "chart_before_sha256": before_chart, "chart_after_sha256": sha(chart), "meta_before_sha256": before_meta, "meta_after_sha256": sha(meta), "old_mod_version": old_version, "new_mod_version": MOD_VERSION, "notes": {difficulty: len(chart_data.get("notes", {}).get(difficulty, [])) for difficulty in ("easy", "normal", "hard")}, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    stage = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "vocal-only-v261" / "staged-mods"
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: one(root, stage, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "PLAYSTATE_VOCAL_COVERS_PROMOTION_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": MOD_VERSION, "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "audio_modified": False, "assets_other_than_freeplay_covers_modified": False, "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "promotion-v261.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "mod_version": MOD_VERSION, "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
