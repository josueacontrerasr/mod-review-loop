#!/usr/bin/env python3
"""Validate the persistent lab-only Optimod installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

EXPECTED_SHA256 = "f33ac62838eee9a74b19b27b6703071d98e24b68067026eb7608601ea323a09e"
PACKAGE = "me.funkin.fnf"
SIM_ROOT = Path("qa-lab/mobile-sim/storage/emulated/0/Android/obb") / PACKAGE / "mods"
DANGEROUS = re.compile(r"(^/|(^|/)\.\.?(/|$)|\.exe$|\.dll$|\.so$|\.sh$|\.bat$|\.cmd$|\.ps1$|\.apk$|\.jar$)", re.I)
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()

    report_path = root / "qa-lab/rebuild-v272/persistent-mods/persistent-lab-mod-v272.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    archive = root / report["source_archive"]
    normalized = root / report["normalized_path"]
    installed = root / report["installed_simulation_path"]
    manifest = json.loads((installed / "_polymod_meta.json").read_text(encoding="utf-8"))

    checks: dict[str, bool] = {}
    checks["original_archive_hash"] = archive.is_file() and sha256(archive) == EXPECTED_SHA256
    checks["original_report_hash_matches"] = report["source_archive_sha256"] == EXPECTED_SHA256
    checks["normalized_exists"] = normalized.is_dir()
    checks["installed_exists"] = installed.is_dir()
    checks["manifest_at_root"] = (installed / "_polymod_meta.json").is_file()
    checks["api_rule_086"] = manifest.get("api_version") == "0.8.6"
    checks["lab_only_flag"] = manifest.get("lab_only") is True
    checks["uninstall_policy_persistent"] = report.get("uninstall_policy") == "PERSIST_UNTIL_USER_EXPLICITLY_REQUESTS_REMOVAL"
    checks["outside_esperon_runtime"] = report.get("excluded_from_esperon_runtime_zips") is True
    checks["legacy_character_imports_removed"] = not any(
        "import funkin.play.character.CharacterType;" in path.read_text(encoding="utf-8")
        for path in installed.rglob("*.hxc")
    )

    dangerous = []
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if DANGEROUS.search(info.filename.replace("\\", "/")):
                dangerous.append(info.filename)
    checks["archive_safe_paths"] = not dangerous

    expected_mods = [SIM_ROOT / f"esperon-dano-{song}" for song in SONGS]
    checks["all_esperon_mods_preserved"] = all(path.is_dir() for path in expected_mods)
    checks["optimizer_persistent_in_simulation"] = (SIM_ROOT / "optimods" / "_polymod_meta.json").is_file()

    runtime_zips = sorted((root / "Mods .zip terminados").glob("*.zip"))
    optimizer_zip_hits = []
    for path in runtime_zips:
        with zipfile.ZipFile(path) as zf:
            optimizer_zip_hits.extend([name for name in zf.namelist() if "/optimods/" in f"/{name}" or name.startswith("optimods/")])
    checks["optimizer_absent_from_runtime_zips"] = not optimizer_zip_hits

    result = {
        "scope": "PERSISTENT_LAB_MOD_GATE_V272",
        "target_version": "0.8.6",
        "package_name": PACKAGE,
        "mod_id": "optimods",
        "checks": checks,
        "dangerous_archive_paths": dangerous,
        "optimizer_runtime_zip_hits": optimizer_zip_hits,
        "status": "PASS" if all(checks.values()) else "ERRORS_FOUND",
    }
    output = root / "qa-lab/rebuild-v272/persistent-mods/persistent-lab-mod-gate-v272.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "passed": sum(checks.values()), "total": len(checks), "output": str(output)}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
