#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "qa-lab/rebuild-v267/playstate-fix/syllable-candidates-small"
CANON = ROOT / "qa-lab/rebuild-v267/playstate-fix/syllable-candidates"
BACKUP = ROOT / "qa-lab/rebuild-v267/playstate-fix/production-before-v267"
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.6.7 vocal RMS-VAD retimed holds and repetition-balanced player lanes d=0..3"


def main() -> int:
    rows = []
    for mod in sorted((ROOT / "mods").glob("esperon-dano-*")):
        charts = sorted(mod.glob("data/songs/*/*-chart.json"))
        if len(charts) != 1:
            raise SystemExit(f"{mod}: expected one chart, found {len(charts)}")
        production = charts[0]
        song = production.parent.name
        candidate_path = SOURCE / song / "candidate-chart.json"
        if not candidate_path.is_file():
            raise SystemExit(f"missing candidate {song}")
        old = json.loads(production.read_text(encoding="utf-8"))
        backup_path = BACKUP / f"{song}-chart-before-v267.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(production, backup_path)
        chart = json.loads(candidate_path.read_text(encoding="utf-8"))
        chart["generatedBy"] = EXPECTED_GENERATED
        chart.pop("_candidate", None)
        chart.pop("candidateMetadata", None)
        chart.pop("analysisEvidence", None)
        production.write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        canonical = CANON / song
        canonical.mkdir(parents=True, exist_ok=True)
        for name in ("candidate-chart.json", "syllable-alignment.json", "candidate-report.json"):
            shutil.copy2(SOURCE / song / name, canonical / name)
        rows.append({
            "song": song,
            "production_chart": str(production.relative_to(ROOT)),
            "backup": str(backup_path.relative_to(ROOT)),
            "notes": {key: len(value) for key, value in chart["notes"].items()},
            "old_notes": {key: len(value) for key, value in old.get("notes", {}).items()},
        })
    report = {
        "scope": "V267_RMS_VAD_BALANCED_SYLLABLE_CHART_PROMOTION",
        "status": "PASS" if len(rows) == 21 else "FAIL",
        "songs": len(rows),
        "source": "cached Whisper timestamps + RMS-VAD onset/end analysis + repetition balance",
        "generatedBy": EXPECTED_GENERATED,
        "backup": str(BACKUP.relative_to(ROOT)),
        "rows": rows,
    }
    output = ROOT / "qa-lab/rebuild-v267/playstate-fix/syllable-promotion-v267.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "songs": len(rows), "output": str(output)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
