#!/usr/bin/env python3
"""Consolida evidencia de voz/chart sin promover cambios musicales."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    reports = sorted((ROOT / "qa-lab/session-30min/voice-chart").glob("*-review.json"))
    entries = []
    for path in reports:
        data = json.loads(path.read_text(encoding="utf-8"))
        difficulty_rows = {}
        for difficulty, row in data.get("difficulties", {}).items():
            difficulty_rows[difficulty] = {
                "production_notes": row.get("production_notes"),
                "valid_notes": row.get("valid_notes"),
                "candidate_vocal_notes": row.get("candidate_vocal_notes"),
                "invalid_notes": row.get("invalid_notes"),
                "median_nearest_candidate_ms": row.get("median_nearest_candidate_ms"),
                "within_75ms_of_candidate_percent": row.get("within_75ms_of_candidate_percent"),
            }
        high = [issue for issue in data.get("issues", []) if issue.get("severity") == "high"]
        entries.append({
            "song": data.get("song"),
            "mod": data.get("mod"),
            "analysis_mode": data.get("analysis_mode"),
            "stem_sha256": data.get("stem_sha256"),
            "difficulties": difficulty_rows,
            "structural_issues": data.get("issues", []),
            "high_issue_count": len(high),
            "decision": data.get("decision"),
            "mobile_confirmation": data.get("mobile_confirmation"),
        })
    status = "PASS_EVIDENCE_ONLY" if len(entries) == 20 and all(item["high_issue_count"] == 0 for item in entries) else "REVIEW_REQUIRED"
    payload = {
        "scope": "WIDE_RESEARCH_VOCAL_CHART_SYNC_AUDIT",
        "songs": len(entries),
        "passed_structural": sum(item["high_issue_count"] == 0 for item in entries),
        "analysis_mode": "VOCAL_STEM",
        "structural_status": "PASS" if len(entries) == 20 and all(item["high_issue_count"] == 0 for item in entries) else "ERRORS_FOUND",
        "evidence_status": status,
        "promotion_status": "ALL_MANUAL_REVIEW_REQUIRED",
        "engine_confirmation": "REQUIRED: Audio Sync Test y playtest móvil no se ejecutan en el sandbox.",
        "automatic_policy": "No se modifican BPM, offsets, timeChanges ni charts de producción por similitud automática.",
        "entries": entries,
    }
    output = ROOT / "qa-lab/wide-research-v212/vocal-chart-sync-consolidated.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": len(entries), "passed_structural": payload["passed_structural"], "evidence_status": status}, ensure_ascii=False))
    return 0 if payload["structural_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
