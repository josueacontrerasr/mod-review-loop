#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small/cortamos-y-volvemos"
align = json.loads((base / "syllable-alignment.json").read_text(encoding="utf-8"))
chart = json.loads((base / "candidate-chart.json").read_text(encoding="utf-8"))
lo, hi = 29900.0, 30050.0
mapping = {"a": 0, "e": 2, "i": 3, "o": 1, "u": 1}
result = {"syllables": [], "notes": {}}
for item in align["syllables"]:
    if lo <= float(item["start_ms"]) <= hi or lo <= float(item.get("vocal_end_ms", 0.0)) <= hi:
        result["syllables"].append({k: item.get(k) for k in ("text", "vowel", "start_ms", "vocal_end_ms", "hold_ms", "vocal_end_source")})
for diff, notes in chart["notes"].items():
    result["notes"][diff] = [note for note in notes if lo <= float(note["t"]) <= hi]
out = ROOT / "qa-lab/rebuild-v266/cortamos-window-v266.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
