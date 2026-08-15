#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small"
rows = []
mapping = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
for path in sorted(base.glob("*/candidate-chart.json")):
    song = path.parent.name
    chart = json.loads(path.read_text(encoding="utf-8"))
    syll = json.loads((path.parent / "syllable-alignment.json").read_text(encoding="utf-8"))["syllables"]
    for diff, notes in chart["notes"].items():
        for index, note in enumerate(notes):
            t = float(note["t"])
            candidate = next((s for s in syll if abs(float(s["start_ms"]) - t) <= 1.0), None)
            if candidate is None:
                candidate = next((s for s in syll if float(s["start_ms"]) <= t <= float(s.get("vocal_end_ms", s["start_ms"])) + 20.0), None)
            vowel = str(candidate.get("vowel", "")) if candidate else ""
            expected = mapping.get(vowel)
            if expected is not None and int(note["d"]) != expected:
                rows.append({"song": song, "difficulty": diff, "index": index, "time": t, "actual": int(note["d"]), "expected": expected, "vowel": vowel, "matched_text": candidate.get("text") if candidate else None, "matched_start": candidate.get("start_ms") if candidate else None, "matched_end": candidate.get("vocal_end_ms") if candidate else None})
out = ROOT / "qa-lab/rebuild-v266/mapping-errors-v266.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"count": len(rows), "first": rows[:12]}, ensure_ascii=False))
