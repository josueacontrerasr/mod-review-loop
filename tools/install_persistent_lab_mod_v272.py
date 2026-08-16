#!/usr/bin/env python3
"""Install a user-provided lab-only Polymod persistently in the internal simulation.

The original ZIP is preserved byte-for-byte. A normalized copy is installed for
FNF v0.8.6 with the minimum compatibility edits required by Polymod's API rule.
This tool never adds the lab mod to Esperon runtime ZIPs and never executes HScript.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE = "me.funkin.fnf"
MOD_ID = "optimods"
OFFICIAL_RELATIVE_PATH = Path("Android") / "obb" / PACKAGE / "mods"
HXC_IMPORT_REPLACEMENTS = {
    "import funkin.play.character.CharacterType;": "import funkin.play.character.BaseCharacter.CharacterType;",
}
FORBIDDEN_NAMES = re.compile(r"(^/|(^|/)\.\.?(/|$)|\.exe$|\.dll$|\.so$|\.sh$|\.bat$|\.cmd$|\.ps1$|\.apk$|\.jar$)", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    for info in members:
        name = info.filename.replace("\\", "/")
        if FORBIDDEN_NAMES.search(name):
            raise ValueError(f"unsafe archive member: {info.filename}")
    return members


def install(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise FileNotFoundError(archive)

    persistent_root = root / "qa-lab" / "rebuild-v272" / "persistent-mods"
    original_dir = persistent_root / "source"
    original_dir.mkdir(parents=True, exist_ok=True)
    original_copy = original_dir / archive.name
    if not original_copy.exists() or sha256(original_copy) != sha256(archive):
        shutil.copy2(archive, original_copy)
    original_hash = sha256(original_copy)

    audit_root = root / "qa-lab" / "rebuild-v272" / "diable-shaders-audit"
    extracted = audit_root / "original-extracted"
    if extracted.exists():
        shutil.rmtree(extracted)
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(original_copy) as zf:
        members = safe_members(zf)
        zf.extractall(extracted)

    source_mod = extracted / MOD_ID
    manifest_path = source_mod / "_polymod_meta.json"
    if not manifest_path.is_file():
        raise ValueError("expected optimods/_polymod_meta.json at archive root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("api_version") != "0.7.0":
        raise ValueError(f"unexpected source api_version: {manifest.get('api_version')!r}")

    normalized = persistent_root / "normalized" / MOD_ID
    if normalized.exists():
        shutil.rmtree(normalized)
    shutil.copytree(source_mod, normalized)
    normalized_manifest_path = normalized / "_polymod_meta.json"
    normalized_manifest = json.loads(normalized_manifest_path.read_text(encoding="utf-8"))
    normalized_manifest["title"] = "Optimod (FNF V-Slice 0.8.6 Lab)"
    normalized_manifest["description"] = "Lab-persistent shader optimizer; adapted only for the FNF 0.8.x Polymod API."
    normalized_manifest["api_version"] = "0.8.6"
    normalized_manifest["mod_version"] = "1.0.0-lab086"
    normalized_manifest["lab_only"] = True
    normalized_manifest["source_archive_sha256"] = original_hash
    normalized_manifest_path.write_text(json.dumps(normalized_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    replacements: list[dict[str, str]] = []
    for path in sorted(normalized.rglob("*.hxc")):
        text = path.read_text(encoding="utf-8")
        original_text = text
        for old, new in HXC_IMPORT_REPLACEMENTS.items():
            text = text.replace(old, new)
        if text != original_text:
            path.write_text(text, encoding="utf-8")
            replacements.append({"file": str(path.relative_to(normalized)), "change": "CharacterType import updated for v0.8.6"})

    sim_root = root / "qa-lab" / "mobile-sim" / "storage" / "emulated" / "0" / OFFICIAL_RELATIVE_PATH
    sim_root.mkdir(parents=True, exist_ok=True)
    installed = sim_root / MOD_ID
    if installed.exists():
        shutil.rmtree(installed)
    shutil.copytree(normalized, installed)

    result = {
        "scope": "PERSISTENT_LAB_MOD_V272",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "package_name": PACKAGE,
        "mod_id": MOD_ID,
        "source_archive": str(original_copy.relative_to(root)),
        "source_archive_sha256": original_hash,
        "source_archive_members": len(members),
        "normalized_path": str(normalized.relative_to(root)),
        "installed_simulation_path": str(installed.relative_to(root)),
        "official_android_path": f"/sdcard/{OFFICIAL_RELATIVE_PATH.as_posix()}/{MOD_ID}",
        "api_version_original": manifest.get("api_version"),
        "api_version_installed": normalized_manifest.get("api_version"),
        "compatibility_replacements": replacements,
        "manifest_at_root": (installed / "_polymod_meta.json").is_file(),
        "uninstall_policy": "PERSIST_UNTIL_USER_EXPLICITLY_REQUESTS_REMOVAL",
        "excluded_from_esperon_runtime_zips": True,
        "status": "PASS",
    }
    report = persistent_root / "persistent-lab-mod-v272.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report"] = str(report.relative_to(root))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    result = install(args)
    print(json.dumps({k: result[k] for k in ("mod_id", "api_version_original", "api_version_installed", "installed_simulation_path", "status", "report")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
