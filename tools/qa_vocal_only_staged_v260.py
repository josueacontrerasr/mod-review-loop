#!/usr/bin/env python3
"""QA 20x20 sobre un árbol staging vocal-only."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def one(root: Path, song: str, round_no: int) -> dict:
    mod = root / "mods" / f"esperon-dano-{song}"
    issues: list[str] = []
    files = [path for path in mod.rglob("*") if path.is_file()]
    for path in files:
        try:
            if path.suffix.lower() == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".xml":
                ET.parse(path)
            elif path.suffix.lower() in (".png", ".jpg", ".jpeg"):
                with Image.open(path) as image:
                    image.verify()
            elif path.suffix.lower() == ".ogg" and path.read_bytes()[:4] != b"OggS":
                issues.append(f"bad_ogg:{path.relative_to(mod)}")
        except Exception as exc:
            issues.append(f"parse:{path.relative_to(mod)}:{exc}")
    try:
        manifest = json.loads((mod / "_polymod_meta.json").read_text(encoding="utf-8"))
        if manifest.get("api_version") != "0.8.6":
            issues.append("api_version")
        song_dir = next((mod / "data" / "songs").iterdir())
        metadata = json.loads((song_dir / f"{song}-metadata.json").read_text(encoding="utf-8"))
        chart = json.loads((song_dir / f"{song}-chart.json").read_text(encoding="utf-8"))
        if metadata.get("version") != "2.2.4":
            issues.append("metadata_version")
        if chart.get("version") != "2.0.0":
            issues.append("chart_version")
        if set(chart.get("notes", {})) != {"easy", "normal", "hard"}:
            issues.append("difficulty_set")
        counts = [len(chart["notes"][difficulty]) for difficulty in ("easy", "normal", "hard")]
        if not (counts[0] < counts[1] < counts[2]):
            issues.append(f"density={counts}")
        if not (chart.get("scrollSpeed", {}).get("easy", 0) < chart.get("scrollSpeed", {}).get("normal", 0) < chart.get("scrollSpeed", {}).get("hard", 0)):
            issues.append("scroll_speed")
        for difficulty, notes in chart.get("notes", {}).items():
            keys = [(float(note.get("t", -1)), int(note.get("d", -1))) for note in notes]
            if keys != sorted(keys) or len(keys) != len(set(keys)):
                issues.append(f"chart_{difficulty}_order_duplicates")
            if any(timestamp < 0 or lane not in (0, 1, 2, 3) for timestamp, lane in keys):
                issues.append(f"chart_{difficulty}_lanes")
        if not (mod / "songs" / song / "Inst.ogg").is_file() or not list((mod / "songs" / song).glob("Voices-*.ogg")):
            issues.append("audio")
    except Exception as exc:
        issues.append(f"contract:{exc}")
    return {"song": song, "round": round_no, "files": len(files), "issues": issues, "status": "PASS" if not issues else "ERROR"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--rounds", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    rows = []
    for round_no in range(1, args.rounds + 1):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            round_rows = list(pool.map(lambda song: one(root, song, round_no), SONGS))
        rows.extend(round_rows)
    payload = {"scope": "VOCAL_ONLY_STAGING_QA_20X20_V260", "target_version": "0.8.6", "rounds": args.rounds, "mods_per_round": len(SONGS), "records": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "errors": sum(row["status"] == "ERROR" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows}
    output = (args.output if args.output is not None else root / "qa-lab" / "rebuild-v260" / "vocal-only" / "stage-qa-20x20-v260.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rounds": payload["rounds"], "mods_per_round": payload["mods_per_round"], "records": payload["records"], "passed": payload["passed"], "errors": payload["errors"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
