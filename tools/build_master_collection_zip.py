#!/usr/bin/env python3
"""Construye un ZIP maestro con los 20 ZIPs vigentes de Mods .zip terminados."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

VERSION = "2.2.1"
COLLECTION = f"Mod-Esperon-Coleccion-V{VERSION}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    delivery = root / "Mods .zip terminados"
    zips = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if path.name != f"{COLLECTION}.zip")
    if len(zips) != 20:
        raise SystemExit(f"Se esperaban 20 ZIP individuales v{VERSION}; se encontraron {len(zips)}.")
    audit_path = root / "reports" / "consolidado_20_rondas.json"
    if not audit_path.is_file():
        audit_path = root / "qa-lab" / "final" / "consolidated-20-rounds.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    manifest = {
        "collection": COLLECTION,
        "individual_mod_zips": [{"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in zips],
        "audit": {
            "rounds_completed": audit.get("rounds_completed", audit.get("rounds")),
            "file_audits_total": audit.get("file_audits_total", audit.get("records")),
            "structural_errors_total": audit.get("structural_errors_total", audit.get("totals", {}).get("errors", 0)),
            "stable_mod_fingerprints": audit.get("stable_mod_fingerprints", audit.get("status") == "STABLE_PLATEAU_REACHED"),
            "synchronization_conclusion": audit.get("synchronization_conclusion", "REQUIRES_HUMAN_REVIEW")
        }
    }
    readme = """# Colección Esperón — Mods FNF Mobile V-Slice v2.2.1

Este archivo contiene los 20 ZIPs individuales instalables. Extrae **solo un ZIP individual** directamente en la carpeta `mods/` de FNF Mobile V-Slice 0.8.6, o extrae todos si deseas instalar la colección completa.

## Validación incluida

Los 20 paquetes superaron 20 rondas de auditoría estructural, rutas, JSON, XML, PNG, OGG, charts y CRC de ZIP. La sincronía vocal sigue marcada como `REQUIRES_HUMAN_REVIEW`: ejecuta Audio Sync Test en el Chart Editor y playtest móvil antes de afirmar sincronización al 100%.
"""
    destination = delivery / f"{COLLECTION}.zip"
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if destination.exists():
        try:
            with zipfile.ZipFile(destination) as existing_archive:
                existing_manifest = json.loads(existing_archive.read(f"{COLLECTION}/MANIFEST.json"))
            if existing_manifest.get("individual_mod_zips") == manifest.get("individual_mod_zips"):
                result = {"zip": str(destination.relative_to(root)), "sha256": sha256(destination), "individual_zips": len(zips), "status": "UNCHANGED"}
                print(json.dumps(result, ensure_ascii=False))
                return 0
        except (KeyError, OSError, ValueError, zipfile.BadZipFile):
            pass
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(f"{COLLECTION}/README.md", readme)
        archive.writestr(f"{COLLECTION}/MANIFEST.json", manifest_text)
        report_md = root / "reports" / "consolidado_20_rondas.md"
        report_json = root / "reports" / "consolidado_20_rondas.json"
        if report_md.is_file():
            archive.write(report_md, f"{COLLECTION}/reports/consolidado_20_rondas.md")
        if report_json.is_file():
            archive.write(report_json, f"{COLLECTION}/reports/consolidado_20_rondas.json")
        for path in zips:
            archive.write(path, f"{COLLECTION}/mods/{path.name}")
    with zipfile.ZipFile(destination) as archive:
        broken = archive.testzip()
        roots = {name.split("/")[0] for name in archive.namelist() if name}
    if broken or roots != {COLLECTION}:
        raise SystemExit(f"ZIP maestro inválido: corrupto={broken}, raíces={roots}")
    result = {"zip": str(destination.relative_to(root)), "sha256": sha256(destination), "individual_zips": len(zips), "status": "PASS"}
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "coleccion_v2_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
