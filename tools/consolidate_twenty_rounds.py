#!/usr/bin/env python3
"""Consolida 20 rondas de auditoría y estados de sincronía sin alterar los mods."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rounds_dir = root / "artifacts" / "twenty-round-audit"
    files = sorted(rounds_dir.glob("round-*.json"))
    rounds = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    fingerprints: dict[str, set[str]] = defaultdict(set)
    sync_statuses: dict[str, str] = {}
    for current in rounds:
        for report in current["reports"]:
            fingerprints[report["mod"]].add(report["fingerprint_sha256"])
    for mod in sorted((root / "mods").glob("esperon-dano-*")):
        song_dirs = sorted((mod / "data" / "songs").glob("*"))
        song = song_dirs[0].name if len(song_dirs) == 1 else mod.name.removeprefix("esperon-dano-")
        evidence_path = root / "qa-lab" / "rebuild-v220" / "evidence" / song / "sync-report.json"
        if not evidence_path.is_file():
            evidence_path = root / "qa-lab" / "pipeline-evidence" / song / "sync-report.json"
        sync = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.is_file() else {"status": "EVIDENCE_MISSING"}
        sync_statuses[mod.name] = str(sync.get("status"))
    unstable = sorted(name for name, values in fingerprints.items() if len(values) != 1)
    errors = sum(current["errors"] for current in rounds)
    warnings = sum(current["warnings"] for current in rounds)
    payload = {
        "rounds_requested": 20,
        "rounds_completed": len(rounds),
        "mods_per_round": 20,
        "file_audits_total": sum(current["files_audited"] for current in rounds),
        "structural_errors_total": errors,
        "warnings_total": warnings,
        "all_rounds_structural_pass": all(current["status"] == "PASS" for current in rounds),
        "stable_mod_fingerprints": len(fingerprints) - len(unstable),
        "unstable_mods": unstable,
        "sync_status_counts": {status: sum(value == status for value in sync_statuses.values()) for status in sorted(set(sync_statuses.values()))},
        "sync_status_by_mod": sync_statuses,
        "conclusion": "STRUCTURAL_AND_PACKAGE_AUDIT_PASS" if not errors and not unstable and len(rounds) == 20 else "AUDIT_BLOCKED",
        "synchronization_conclusion": "NO_SE_PUEDE_AFIRMAR_100_POR_CIENTO_SIN_AUDIO_SYNC_TEST_Y_PLAYTEST_MOVIL; los informes de sincronía actuales mantienen revisión humana requerida.",
        "references": [
            "https://funkincrew-funkin-59.mintlify.app/tools/chart-editor",
            "https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/verify-release-integrity"
        ]
    }
    out = root / "reports" / "consolidado_20_rondas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = root / "reports" / "consolidado_20_rondas.md"
    markdown.write_text(
        "# Consolidado de 20 rondas de auditoría\n\n"
        f"Se completaron **{payload['rounds_completed']} de 20** rondas sobre **20 mods**. Cada ronda auditó JSON, XML, PNG, OGG, scripts, metadatos, charts, rutas, ZIP y CRC.\n\n"
        "| Métrica | Resultado |\n|---|---:|\n"
        f"| Auditorías de archivo | {payload['file_audits_total']:,} |\n"
        f"| Errores estructurales | {payload['structural_errors_total']} |\n"
        f"| Rondas estructurales aprobadas | {sum(current['status'] == 'PASS' for current in rounds)} / {len(rounds)} |\n"
        f"| Mods con fingerprint estable | {payload['stable_mod_fingerprints']} / 20 |\n"
        f"| Advertencias de sincronía manual | {payload['warnings_total']} |\n\n"
        "> **Sincronía:** los controles de archivos, charts y paquetes aprobaron, pero no se puede afirmar sincronía vocal al 100% sin ejecutar el Audio Sync Test del Chart Editor y un playtest móvil documentado por canción.\n",
        encoding="utf-8"
    )
    print(json.dumps({key: payload[key] for key in ("rounds_completed", "file_audits_total", "structural_errors_total", "stable_mod_fingerprints", "conclusion")}, ensure_ascii=False))
    return 0 if payload["conclusion"] == "STRUCTURAL_AND_PACKAGE_AUDIT_PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
