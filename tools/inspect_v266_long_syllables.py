#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small"
items = []
for path in base.glob("*/syllable-alignment.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    for item in data.get("syllables", []):
        items.append({"song": path.parent.name, **item})
items.sort(key=lambda item: float(item.get("duration_ms", 0.0)), reverse=True)
report = {
    "top_50": [
        {key: item.get(key) for key in ("song", "word", "text", "vowel", "start_ms", "vocal_end_ms", "duration_ms", "hold_ms", "vocal_end_source", "confidence")}
        for item in items[:50]
    ],
    "over_3000ms": sum(1 for item in items if float(item.get("duration_ms", 0.0)) > 3000.0),
    "over_1500ms": sum(1 for item in items if float(item.get("duration_ms", 0.0)) > 1500.0),
}
out = ROOT / "qa-lab/rebuild-v266/long-syllables-v266.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"over_3000ms": report["over_3000ms"], "over_1500ms": report["over_1500ms"], "top": report["top_50"][:5]}, ensure_ascii=False))
