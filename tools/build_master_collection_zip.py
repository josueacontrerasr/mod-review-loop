#!/usr/bin/env python3
"""Construye un ZIP maestro que contiene los 20 ZIPs individuales v2.0.0."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

VERSION = "2.0.0"
COLLECTION = f"esperon-dano-coleccion-v{VERSION}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    zips = sorted((root / "dist").glob("esperon-dano-*-v2.0.0.zip"))
    if len(zips) != 20:
        raise SystemExit(f"Se esperaban 20 ZIP individuales v2.0.0; se encontraron {len(zips)}.")
    audit = json.loads((root / "reports" / "consolidado_20_rondas.json").read_text(encoding="utf-8"))
    manifest = {
        "collection": COLLECTION,
        "individual_mod_zips": [{"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in zips],
        "audit": {
            "rounds_completed": audit["rounds_completed"],
            "file_audits_total": audit["file_audits_total"],
            "structural_errors_total": audit["structural_errors_total"],
            "stable_mod_fingerprints": audit["stable_mod_fingerprints"],
            "synchronization_conclusion": audit["synchronization_conclusion"]
        }
    }
    readme = """# Colección Esperón — Mods FNF Mobile V-Slice v2.0.0

Este archivo contiene los 20 ZIPs individuales instalables. Extrae **solo un ZIP individual** directamente en la carpeta `mods/` de FNF Mobile V-Slice 0.8.6, o extrae todos si deseas instalar la colección completa.

## Validación incluida

Los 20 paquetes superaron 20 rondas de auditoría estructural, rutas, JSON, XML, PNG, OGG, charts y CRC de ZIP. La sincronía vocal sigue marcada como `REQUIRES_HUMAN_REVIEW`: ejecuta Audio Sync Test en el Chart Editor y playtest móvil antes de afirmar sincronización al 100%.
"""
    destination = root / "dist" / f"{COLLECTION}.zip"
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(f"{COLLECTION}/README.md", readme)
        archive.writestr(f"{COLLECTION}/MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        archive.write(root / "reports" / "consolidado_20_rondas.md", f"{COLLECTION}/reports/consolidado_20_rondas.md")
        archive.write(root / "reports" / "consolidado_20_rondas.json", f"{COLLECTION}/reports/consolidado_20_rondas.json")
        for path in zips:
            archive.write(path, f"{COLLECTION}/mods/{path.name}")
    with zipfile.ZipFile(destination) as archive:
        broken = archive.testzip()
        roots = {name.split("/")[0] for name in archive.namelist() if name}
    if broken or roots != {COLLECTION}:
        raise SystemExit(f"ZIP maestro inválido: corrupto={broken}, raíces={roots}")
    result = {"zip": str(destination.relative_to(root)), "sha256": sha256(destination), "individual_zips": len(zips), "status": "PASS"}
    (root / "reports" / "coleccion_v2_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
