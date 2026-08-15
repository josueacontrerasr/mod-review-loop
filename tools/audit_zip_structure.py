#!/usr/bin/env python3
"""Compara la estructura interna de ZIP de referencia y ZIP de mods V-Slice."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect(path: Path) -> dict:
    result = {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path), "error": None}
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name and not name.startswith("__MACOSX/")]
            roots = sorted({name.split("/", 1)[0] for name in names})
            manifest_paths = sorted(name for name in names if name.endswith("/_polymod_meta.json") or name == "_polymod_meta.json")
            direct_manifests = sorted(name for name in manifest_paths if len(name.split("/")) == 2)
            top_files = sorted(name for name in names if "/" not in name)
            forbidden_fragments = [".git/", "__MACOSX/", "node_modules/", "qa-lab/", "dist/", "artifacts/"]
            forbidden = sorted(name for name in names if any(fragment in name for fragment in forbidden_fragments))
            result.update({
                "entries": len(names),
                "roots": roots,
                "root_count": len(roots),
                "manifest_paths": manifest_paths,
                "direct_manifest_paths": direct_manifests,
                "top_level_files": top_files,
                "forbidden_work_files": forbidden,
                "single_root": len(roots) == 1,
                "manifest_at_root": len(direct_manifests) == 1,
                "structure_status": "PASS" if len(roots) == 1 and len(direct_manifests) == 1 and not forbidden else "REVIEW_REQUIRED",
            })
            for manifest_path in direct_manifests[:1]:
                manifest = json.loads(archive.read(manifest_path).decode("utf-8"))
                result["manifest"] = {
                    "path": manifest_path,
                    "id": manifest.get("id"),
                    "title": manifest.get("title"),
                    "api_version": manifest.get("api_version"),
                    "mod_version": manifest.get("mod_version"),
                }
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result["error"] = str(exc)
        result["structure_status"] = "ERROR"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--reference", action="append", default=[])
    parser.add_argument("--delivery-dir", default="Mods .zip terminados")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    references = [Path(item).resolve() for item in args.reference]
    delivery = root / args.delivery_dir
    final_zips = sorted(path for path in delivery.glob("Mod-*-V*.zip") if not path.name.startswith("Mod-Esperon-Coleccion-V"))
    collection = sorted(delivery.glob("Mod-Esperon-Coleccion-V*.zip"))
    payload = {
        "scope": "ZIP_STRUCTURE_REFERENCE_COMPARISON",
        "target": "FNF Mobile V-Slice 0.8.6",
        "references": [inspect(path) for path in references],
        "esperon_individual_zips": [inspect(path) for path in final_zips],
        "esperon_collection_zips": [inspect(path) for path in collection],
        "coverage": {"reference_zips": len(references), "individual_zips": len(final_zips), "collection_zips": len(collection)},
        "status": "PASS" if len(references) == 3 and len(final_zips) == 20 and all(item.get("structure_status") == "PASS" for item in [inspect(path) for path in final_zips]) else "REVIEW_REQUIRED",
        "limitations": ["La comparación estática no sustituye la extracción y carga en FNF Mobile del dispositivo."],
    }
    output = root / "qa-lab" / "session-zip-structure" / "official-reference-comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"references": len(references), "individual_zips": len(final_zips), "collection_zips": len(collection), "status": payload["status"]}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
