#!/usr/bin/env python3
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
DIFFICULTIES = ("easy", "normal", "hard")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def one(root: Path, song: str) -> dict:
    candidate_dir = root / "qa-lab/rebuild-v262/playstate-fix/vocal-only-v262" / song
    candidate = load(candidate_dir / "chart-vocal-only.json")
    production_path = root / "mods" / f"esperon-dano-{song}" / "data/songs" / song / f"{song}-chart.json"
    production = load(production_path)
    compare = {}
    same = True
    for difficulty in DIFFICULTIES:
        candidate_notes = [(float(n["t"]), int(n["d"])) for n in candidate.get("notes", {}).get(difficulty, [])]
        production_notes = [(float(n["t"]), int(n["d"])) for n in production.get("notes", {}).get(difficulty, [])]
        equal = candidate_notes == production_notes
        compare[difficulty] = {"candidate": len(candidate_notes), "production": len(production_notes), "same": equal}
        same = same and equal
    return {"song": song, "same_as_production": same, "production_chart": str(production_path.relative_to(root)), "comparison": compare}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); args = parser.parse_args()
    root = args.root.resolve()
    with ThreadPoolExecutor(max_workers=8) as executor:
        rows = sorted(executor.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "V262_CANDIDATE_PRODUCTION_COMPARISON", "executed_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "same_count": sum(r["same_as_production"] for r in rows), "different_count": sum(not r["same_as_production"] for r in rows), "rows": rows}
    output = root / "qa-lab/rebuild-v262/playstate-fix/candidate-production-comparison-v262.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "same_count": payload["same_count"], "different_count": payload["different_count"], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
