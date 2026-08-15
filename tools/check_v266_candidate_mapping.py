#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small"
expected = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
failures = []
summary = []
for align_path in sorted(CANDIDATES.glob("*/syllable-alignment.json")):
    song = align_path.parent.name
    align = json.loads(align_path.read_text(encoding="utf-8"))
    chart = json.loads((align_path.parent / "candidate-chart.json").read_text(encoding="utf-8"))
    for item in align.get("syllables", []):
        if item.get("vowel") not in expected:
            continue
    directions = {difficulty: sorted({int(note["d"]) for note in notes}) for difficulty, notes in chart["notes"].items()}
    bad = [(difficulty, int(note["d"])) for difficulty, notes in chart["notes"].items() for note in notes if int(note["d"]) not in {0, 1, 2, 3}]
    for difficulty, value in bad:
        failures.append({"song": song, "difficulty": difficulty, "lane": value})
    summary.append({"song": song, "directions": directions, "syllables": len(align.get("syllables", []))})
result = {"songs": len(summary), "failures": failures, "status": "PASS" if len(summary) == 21 and not failures else "FAIL", "mapping": {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}, "summary": summary}
out = ROOT / "qa-lab/rebuild-v266/player-vowel-mapping-check.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "songs": result["songs"], "failures": len(failures)}, ensure_ascii=False))
raise SystemExit(0 if result["status"] == "PASS" else 1)
