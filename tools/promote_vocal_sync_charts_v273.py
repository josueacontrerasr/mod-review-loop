#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-candidates"
CANON = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-candidates-canonical"
BACKUP = ROOT / "qa-lab/rebuild-v273/playstate-fix/production-before-v273"
EXPECTED_GENERATED = "Friday Night Funkin' - 0.8.6; V2.7.3 calibrated vocal onsets, syllable-accurate holds and player lanes d=0..3"


def main() -> int:
    rows = []
    for mod in sorted((ROOT / "mods").glob("esperon-dano-*")):
        charts = sorted(mod.glob("data/songs/*/*-chart.json"))
        if len(charts) != 1:
            raise SystemExit(f"{mod}: expected one chart, found {len(charts)}")
        production = charts[0]
        song = production.parent.name
        candidate_dir = SOURCE / song
        candidate_path = candidate_dir / "candidate-chart.json"
        if not candidate_path.is_file():
            raise SystemExit(f"missing candidate {song}")
        old = json.loads(production.read_text(encoding="utf-8"))
        backup_path = BACKUP / f"{song}-chart-before-v273.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(production, backup_path)
        chart = json.loads(candidate_path.read_text(encoding="utf-8"))
        chart["generatedBy"] = EXPECTED_GENERATED
        for key in ("_candidate", "candidateMetadata", "analysisEvidence", "densityReductionEvidence", "vocalSyncEvidence"):
            chart.pop(key, None)
        production.write_text(json.dumps(chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        canonical = CANON / song
        canonical.mkdir(parents=True, exist_ok=True)
        for name in ("candidate-chart.json", "syllable-alignment.json", "vocal-sync-report.json"):
            source = candidate_dir / name
            if source.is_file():
                shutil.copy2(source, canonical / name)
        rows.append({
            "song": song,
            "production_chart": str(production.relative_to(ROOT)),
            "backup": str(backup_path.relative_to(ROOT)),
            "notes": {key: len(value) for key, value in chart["notes"].items()},
            "old_notes": {key: len(value) for key, value in old.get("notes", {}).items()},
        })
    report = {
        "scope": "V273_CALIBRATED_VOCAL_ONSET_CHART_PROMOTION",
        "status": "PASS" if len(rows) == 21 else "FAIL",
        "songs": len(rows),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "V2.7.3 calibrated audio_onset_ms candidates from verified vocal stems; no 500/1000 ms deletion; holds from measured sustained vocal intervals; free player-lane reassignment only for sub-12ms collisions",
        "generatedBy": EXPECTED_GENERATED,
        "backup": str(BACKUP.relative_to(ROOT)),
        "rows": rows,
    }
    output = ROOT / "qa-lab/rebuild-v273/playstate-fix/vocal-sync-promotion-v273.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "songs": len(rows), "output": str(output)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
