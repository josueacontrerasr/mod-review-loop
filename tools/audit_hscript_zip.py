#!/usr/bin/env python3
"""Audita scripts HScript dentro de los ZIP finales sin modificarlos."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

VERSION = "2.1.2"
EXTENDS_RE = re.compile(r"\bclass\s+(\w+)\s+extends\s+([\w.]+)")
IMPORT_RE = re.compile(r"^\s*import\s+([^;]+);", re.MULTILINE)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--delivery-dir", default="Mods .zip terminados")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    delivery = root / args.delivery_dir
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if "Coleccion" not in path.name)
    entries = []
    for package in packages:
        with zipfile.ZipFile(package) as archive:
            scripts = []
            for name in sorted(archive.namelist()):
                if not name.endswith((".hxc", ".hx")):
                    continue
                raw = archive.read(name)
                text = raw.decode("utf-8-sig")
                matches = EXTENDS_RE.findall(text)
                scripts.append({
                    "path": name,
                    "sha256": sha256_bytes(raw),
                    "imports": IMPORT_RE.findall(text),
                    "extends": [{"class": cls, "base": base} for cls, base in matches],
                    "has_playstate_import": "funkin.play.PlayState" in text,
                    "has_module_import": any("Module" in imp for imp in IMPORT_RE.findall(text)),
                    "has_module_superclass": any(base == "Module" for _, base in matches),
                    "parse_shape": "PASS" if len(matches) == 1 else "REVIEW",
                })
        entries.append({"package": package.name, "scripts": scripts})
    hscript_count = sum(len(item["scripts"]) for item in entries)
    module_count = sum(sum(script["has_module_superclass"] for script in item["scripts"]) for item in entries)
    payload = {
        "scope": "HScript_ZIP_INVENTORY",
        "version": VERSION,
        "delivery_folder": delivery.relative_to(root).as_posix(),
        "packages": len(packages),
        "hscript_files": hscript_count,
        "module_superclass_files": module_count,
        "entries": entries,
        "status": "PASS" if len(packages) == 20 and hscript_count == 20 else "REVIEW_REQUIRED",
        "limitations": ["La auditoría de texto no sustituye el parser ni el runtime de FNF Mobile V-Slice 0.8.6."],
    }
    output = root / "qa-lab" / "session-hscript" / "hscript-zip-inventory-v2.1.2.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("packages", "hscript_files", "module_superclass_files", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
