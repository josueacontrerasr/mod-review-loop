#!/usr/bin/env python3
"""Comprueba que los paquetes v2.1.0 contienen los assets Freeplay V-Slice requeridos."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

VERSION = "2.1.2"


def require(entries: set[str], path: str, errors: list[str]) -> None:
    if path not in entries:
        errors.append(f"falta {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--delivery-dir", default="Mods .zip terminados")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    delivery = root / args.delivery_dir
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if path.name != f"Mod-Esperon-Coleccion-V{VERSION}.zip")
    reports = []
    for package in packages:
        display_song = package.name.removesuffix(f"-V{VERSION}.zip").removeprefix("Mod-")
        song = display_song.lower()
        mod_id = f"esperon-dano-{song}"
        album_id = f"esperon-{song}"
        prefix = f"{mod_id}/"
        errors: list[str] = []
        with zipfile.ZipFile(package) as archive:
            names = set(archive.namelist())
            require(names, prefix + "_polymod_meta.json", errors)
            require(names, prefix + f"data/ui/freeplay/albums/{album_id}.json", errors)
            require(names, prefix + f"images/freeplay/albums/{album_id}-art.png", errors)
            require(names, prefix + f"images/freeplay/albums/{album_id}-title.png", errors)
            require(names, prefix + f"data/songs/{song}/{song}-metadata.json", errors)
            if not errors:
                manifest = json.loads(archive.read(prefix + "_polymod_meta.json"))
                album = json.loads(archive.read(prefix + f"data/ui/freeplay/albums/{album_id}.json"))
                metadata = json.loads(archive.read(prefix + f"data/songs/{song}/{song}-metadata.json"))
                if manifest.get("api_version") != "0.8.6":
                    errors.append("api_version no es 0.8.6")
                if manifest.get("mod_version") != VERSION:
                    errors.append(f"mod_version no es {VERSION}")
                if album.get("version") != "1.0.3":
                    errors.append("album no usa esquema 1.0.3")
                if metadata.get("album") != album_id:
                    errors.append("metadata no enlaza el álbum Freeplay")
        reports.append({"package": package.name, "song": song, "status": "PASS" if not errors else "ERROR", "errors": errors})

    collection = delivery / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    collection_errors: list[str] = []
    if not collection.is_file():
        collection_errors.append("falta colección")
    else:
        with zipfile.ZipFile(collection) as archive:
            contents = set(archive.namelist())
            collection_root = f"Mod-Esperon-Coleccion-V{VERSION}"
            for package in packages:
                require(contents, f"{collection_root}/mods/{package.name}", collection_errors)

    payload = {
        "scope": "VSLICE_086_FREEPLAY_ARCHIVE_VERIFICATION",
        "version": VERSION,
        "delivery_folder": delivery.relative_to(root).as_posix(),
        "packages": len(packages),
        "passed": sum(report["status"] == "PASS" for report in reports),
        "collection": collection.name,
        "collection_errors": collection_errors,
        "reports": reports,
        "status": "PASS" if len(packages) == 20 and not collection_errors and all(report["status"] == "PASS" for report in reports) else "ERRORS_FOUND",
    }
    output = root / "qa-lab" / "session-30min" / "v2.1.2-archive-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("packages", "passed", "collection", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
