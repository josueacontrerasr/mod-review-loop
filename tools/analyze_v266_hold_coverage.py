#!/usr/bin/env python3
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_IN = ROOT / "qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small"
rows = []
all_durations = []
all_holds = []
for path in sorted(ROOT_IN.glob("*/syllable-alignment.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    syllables = data.get("syllables", [])
    durations = [float(item.get("duration_ms", 0.0)) for item in syllables]
    holds = [float(item.get("hold_ms", 0.0)) for item in syllables if float(item.get("hold_ms", 0.0)) > 0]
    all_durations.extend(durations)
    all_holds.extend(holds)
    rows.append({
        "song": path.parent.name,
        "syllables": len(syllables),
        "holds": len(holds),
        "hold_ratio": round(len(holds) / len(syllables), 4) if syllables else 0.0,
        "max_duration_ms": round(max(durations, default=0.0), 3),
        "p95_duration_ms": round(statistics.quantiles(durations, n=20)[18], 3) if len(durations) >= 20 else round(max(durations, default=0.0), 3),
        "tail_extended": sum(1 for item in syllables if item.get("vocal_end_source") == "word-boundary+rms-tail"),
    })
result = {
    "songs": len(rows),
    "total_syllables": len(all_durations),
    "total_holds": len(all_holds),
    "hold_ratio": round(len(all_holds) / len(all_durations), 4) if all_durations else 0.0,
    "max_duration_ms": round(max(all_durations, default=0.0), 3),
    "p95_duration_ms": round(statistics.quantiles(all_durations, n=20)[18], 3) if len(all_durations) >= 20 else round(max(all_durations, default=0.0), 3),
    "rows": rows,
}
out = ROOT / "qa-lab/rebuild-v266/hold-coverage-before-v266.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: result[k] for k in ("songs", "total_syllables", "total_holds", "hold_ratio", "max_duration_ms", "p95_duration_ms")}, ensure_ascii=False))
