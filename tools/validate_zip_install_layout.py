#!/usr/bin/env python3
"""Valida la estructura real de instalación de los ZIP v2.1.2."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

VERSION = "2.1.2"


def require(names: set[str], path: str, errors: list[str]) -> None:
    if path not in names:
        errors.append(f"falta {path}")


def asset_exists(names: set[str], root: str, asset_path: str, errors: list[str]) -> None:
    normalized = asset_path.removeprefix("shared:")
    prefix = "shared/images/" if asset_path.startswith("shared:") else "images/"
    candidates = {root + "/" + prefix + normalized + ".png", root + "/" + prefix + normalized + ".xml", root + "/" + prefix + normalized + ".astc"}
    if not names.intersection(candidates):
        errors.append(f"asset no resuelto: {asset_path}")


def collect_asset_paths(value: object) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "assetPath" and isinstance(child, str):
                paths.append(child)
            else:
                paths.extend(collect_asset_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.extend(collect_asset_paths(child))
    return paths


def validate_package(path: Path) -> dict:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = {name.rstrip("/") for name in archive.namelist() if name and not name.startswith("__MACOSX/")}
        roots = {name.split("/", 1)[0] for name in names}
        if len(roots) != 1:
            errors.append(f"raíces={sorted(roots)}")
            return {"package": path.name, "status": "ERROR", "errors": errors}
        root = next(iter(roots))
        if root != f"esperon-dano-{path.name.removeprefix('Mod-').removesuffix(f'-V{VERSION}.zip').lower()}":
            errors.append(f"raíz inesperada={root}")
        prefix = root + "/"
        require(names, prefix + "_polymod_meta.json", errors)
        require(names, prefix + "CREDITS.txt", errors)
        require(names, prefix + "LICENSE.txt", errors)
        require(names, prefix + "INSTALACION_MOVIL.txt", errors)
        song = root.removeprefix("esperon-dano-")
        song_prefix = prefix + f"data/songs/{song}/"
        require(names, song_prefix + f"{song}-metadata.json", errors)
        require(names, song_prefix + f"{song}-chart.json", errors)
        require(names, song_prefix + "manifest.json", errors)
        require(names, prefix + f"songs/{song}/Inst.ogg", errors)
        icon_count = sum(name.startswith(prefix + "images/icons/") and name.endswith(".png") for name in names)
        if icon_count < 2:
            errors.append(f"iconos={icon_count}")
        for forbidden in ("images/characters/", "images/stages/", "images/notes/", "images/ui/"):
            if any(name.startswith(prefix + forbidden) for name in names):
                errors.append(f"ruta antigua presente: {forbidden}")
        for rel in (f"data/characters/esperon-{song}.json", f"data/characters/rival-{song}.json", f"data/stages/escenario-{song}.json", f"data/notestyles/esperon-{song}-notes.json"):
            data_path = prefix + rel
            require(names, data_path, errors)
            if data_path in names:
                data = json.loads(archive.read(data_path).decode("utf-8"))
                for asset_path in collect_asset_paths(data):
                    asset_exists(names, root, asset_path, errors)
        metadata = json.loads(archive.read(song_prefix + f"{song}-metadata.json").decode("utf-8"))
        chart = json.loads(archive.read(song_prefix + f"{song}-chart.json").decode("utf-8"))
        manifest = json.loads(archive.read(prefix + "_polymod_meta.json").decode("utf-8"))
        song_manifest = json.loads(archive.read(song_prefix + "manifest.json").decode("utf-8"))
        if manifest.get("api_version") != "0.8.6": errors.append("api_version")
        if manifest.get("mod_version") != VERSION: errors.append("mod_version")
        if metadata.get("version") != "2.2.4": errors.append("metadata version")
        if chart.get("version") != "2.0.0": errors.append("chart version")
        if song_manifest.get("songId") != song: errors.append("song manifest id")
    return {"package": path.name, "root": root, "status": "PASS" if not errors else "ERROR", "errors": errors}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    delivery = root / "Mods .zip terminados"
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if "Coleccion" not in path.name)
    reports = [validate_package(path) for path in packages]
    collection = delivery / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    collection_errors: list[str] = []
    if not collection.is_file():
        collection_errors.append("falta colección")
    else:
        with zipfile.ZipFile(collection) as archive:
            names = set(archive.namelist())
            collection_root = f"Mod-Esperon-Coleccion-V{VERSION}"
            for package in packages:
                require(names, f"{collection_root}/mods/{package.name}", collection_errors)
    payload = {"scope": "VSLICE_086_INSTALL_LAYOUT", "version": VERSION, "packages": len(packages), "passed": sum(item["status"] == "PASS" for item in reports), "collection": collection.name, "collection_errors": collection_errors, "reports": reports, "status": "PASS" if len(packages) == 20 and not collection_errors and all(item["status"] == "PASS" for item in reports) else "ERRORS_FOUND"}
    output = root / "qa-lab" / "session-zip-structure" / "v2.1.2-install-layout.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("packages", "passed", "collection", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
