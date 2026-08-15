#!/usr/bin/env python3
"""Consolida evidencia de stems vocales y candidatos sin promover charts."""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    entries = []
    for manifest_path in sorted((root / "sync-candidates" / "input-manifests").glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        song = manifest["song"]
        evidence_path = root / "sync-candidates" / "vocal-stems" / song / "stem-evidence.json"
        report_path = root / "sync-candidates" / "results" / song / "sync-candidate-report.json"
        errors = []
        warnings = []
        stem_status = "NOT_AVAILABLE"
        if not evidence_path.is_file():
            errors.append("falta evidencia del stem")
            evidence = {}
        else:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            stem = root / evidence["vocal_stem"]["path"]
            if not stem.is_file():
                # WAVs are intentionally excluded from the repository; retain a reproducible evidence-only state.
                warnings.append("stem no materializado localmente; se conserva SHA-256 publicado")
                stem_status = "EVIDENCE_ONLY"
            elif sha256(stem) != evidence["vocal_stem"]["sha256"]:
                errors.append("hash del stem no coincide")
                stem_status = "HASH_MISMATCH"
            else:
                stem_status = "HASH_VERIFIED"
        if not report_path.is_file():
            errors.append("falta reporte vocal")
            report = {}
        else:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("analysis_mode") != "VOCAL_STEM":
                errors.append("reporte no basado en stem vocal")
            if report.get("status") != "MANUAL_REVIEW_REQUIRED":
                errors.append("estado de promoción inseguro")
            if report.get("audio", {}).get("sha256") != manifest["final_audio"]["sha256"]:
                errors.append("hash del OGG final no coincide")
            if evidence and report.get("analysis_audio", {}).get("sha256") != evidence.get("vocal_stem", {}).get("sha256"):
                errors.append("el reporte no referencia el stem verificado")
        entries.append({
            "song": song,
            "status": "PASS" if not errors else "ERROR",
            "errors": errors,
            "warnings": warnings,
            "stem_status": stem_status,
            "candidate_base_notes": report.get("counts", {}).get("candidate_base_notes"),
            "vocal_stem_sha256": evidence.get("vocal_stem", {}).get("sha256"),
        })
    note_counts = [entry["candidate_base_notes"] for entry in entries if isinstance(entry["candidate_base_notes"], int)]
    payload = {
        "scope": "VOCAL_STEM_CANDIDATE_CONSOLIDATION",
        "status": ("ERRORS_FOUND" if any(entry["status"] != "PASS" for entry in entries) else ("PASS" if all(entry["stem_status"] == "HASH_VERIFIED" for entry in entries) else "PASS_EVIDENCE_ONLY")),
        "songs": len(entries),
        "passed": sum(entry["status"] == "PASS" for entry in entries),
        "analysis_mode": "VOCAL_STEM",
        "promotion_status": "ALL_MANUAL_REVIEW_REQUIRED",
        "candidate_note_statistics": {
            "min": min(note_counts) if note_counts else None,
            "max": max(note_counts) if note_counts else None,
            "mean": round(statistics.mean(note_counts), 3) if note_counts else None,
        },
        "entries": entries,
        "limitations": [
            "Demucs separa fuentes estimadas; no identifica automáticamente personaje/strumline.",
            "No se han ejecutado Audio Sync Test ni playtest móvil oficiales desde este entorno.",
            "Ningún candidato sobrescribió un chart de producción."
        ]
    }
    output = root / "sync-candidates" / "vocal-stem-consolidation.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("status", "songs", "passed", "analysis_mode", "promotion_status")}, ensure_ascii=False))
    return 0 if payload["status"] in ("PASS", "PASS_EVIDENCE_ONLY") else 1

if __name__ == "__main__":
    raise SystemExit(main())
