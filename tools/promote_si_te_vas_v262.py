#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SONG = "si-te-vas"

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); args = parser.parse_args()
    root = args.root.resolve()
    candidate_path = root / "qa-lab/rebuild-v262/playstate-fix/vocal-only-v262" / SONG / "chart-vocal-only.json"
    production_path = root / "mods/esperon-dano-si-te-vas/data/songs/si-te-vas/si-te-vas-chart.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    notes = {}
    for difficulty in ("easy", "normal", "hard"):
        clean = []
        for note in candidate.get("notes", {}).get(difficulty, []):
            clean_note = {"t": round(float(note["t"]), 3), "d": int(note["d"])}
            for key in ("l", "k", "p"):
                if key in note:
                    clean_note[key] = note[key]
            clean.append(clean_note)
        notes[difficulty] = clean
    production = {
        "version": "2.0.0",
        "scrollSpeed": {"easy": 0.9, "normal": 1.0, "hard": 1.12},
        "events": [],
        "notes": notes,
        "generatedBy": "Friday Night Funkin' - 0.8.6",
    }
    production_path.write_text(json.dumps(production, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "song": SONG, "production": str(production_path), "counts": {d: len(notes[d]) for d in notes}, "candidate_fields_removed": True}, ensure_ascii=False))

if __name__ == "__main__":
    main()
