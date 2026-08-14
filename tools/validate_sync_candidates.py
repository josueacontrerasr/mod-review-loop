#!/usr/bin/env python3
"""Valida candidatos de sincronía y asegura que no se modificaron charts de producción."""
from __future__ import annotations

import hashlib
import json
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
    manifests = sorted((root / "sync-candidates" / "input-manifests").glob("*.json"))
    reports = []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        song = manifest["song"]
        candidate_dir = root / "sync-candidates" / "results" / song
        errors: list[str] = []
        report_path = candidate_dir / "sync-candidate-report.json"
        chart_path = candidate_dir / "candidate-chart.json"
        anchors_path = candidate_dir / "candidate-anchors.json"
        if not all(path.is_file() for path in (report_path, chart_path, anchors_path)):
            errors.append("artefactos candidatos incompletos")
        else:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            chart = json.loads(chart_path.read_text(encoding="utf-8"))
            if report.get("status") != "MANUAL_REVIEW_REQUIRED":
                errors.append("estado candidato no seguro")
            if report.get("audio", {}).get("sha256") != manifest["final_audio"]["sha256"]:
                errors.append("hash de audio del candidato no coincide")
            if chart.get("version") != "2.0.0" or chart.get("candidateOnly") is not True:
                errors.append("chart candidato no declarado correctamente")
            duration_ms = float(report.get("audio", {}).get("duration_ms", 0))
            for difficulty in ("easy", "normal", "hard"):
                notes = chart.get("notes", {}).get(difficulty)
                previous = -1.0
                if not isinstance(notes, list) or not notes:
                    errors.append(f"{difficulty}: sin notas")
                    continue
                for index, note in enumerate(notes):
                    if not isinstance(note, dict) or not isinstance(note.get("t"), (int, float)) or not isinstance(note.get("d"), int):
                        errors.append(f"{difficulty}[{index}]: inválida")
                        continue
                    if note["t"] < previous or note["t"] >= duration_ms or not 0 <= note["d"] <= 7:
                        errors.append(f"{difficulty}[{index}]: tiempo/dirección inválidos")
                    previous = float(note["t"])
        production_chart = root / manifest["chart"]["path"]
        if sha256(production_chart) != manifest["chart"]["sha256"]:
            errors.append("chart de producción cambió desde el manifiesto")
        reports.append({"song": song, "status": "PASS" if not errors else "ERROR", "errors": errors})
    payload = {
        "scope": "SYNC_CANDIDATE_ISOLATION_VALIDATION",
        "songs": len(reports),
        "passed": sum(report["status"] == "PASS" for report in reports),
        "status": "PASS" if all(report["status"] == "PASS" for report in reports) else "ERRORS_FOUND",
        "reports": reports,
        "guarantees": [
            "Los charts candidatos se almacenan fuera de los mods de producción.",
            "Los hashes de los charts de producción coinciden con el manifiesto de entrada.",
            "Todos los candidatos mantienen estado MANUAL_REVIEW_REQUIRED."
        ]
    }
    output = root / "sync-candidates" / "validation.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("songs", "passed", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
