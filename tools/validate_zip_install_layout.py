#!/usr/bin/env python3
"""Valida la estructura real de instalación de los ZIP v2.2.0 con política de runtime limpio."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

VERSION = "2.2.0"


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
        allowed_root_files = {"_polymod_meta.json", "_polymod_icon.png", "_polymod_icon.astc"}
        for info in archive.infolist():
            raw_name = info.filename.rstrip("/")
            if not raw_name.startswith(prefix):
                continue
            relative = raw_name[len(prefix):]
            if "/" not in relative and not info.is_dir() and relative not in allowed_root_files:
                errors.append(f"archivo auxiliar en raíz del mod: {relative}")
        forbidden_aux = {"CREDITS.txt", "LICENSE.txt", "INSTALACION_MOVIL.txt", "audio-evidence.json", "sync-report.json", "visual-v2-integrity.json"}
        for name in names:
            basename = name.rsplit("/", 1)[-1]
            if basename in forbidden_aux or any(token in name.split("/") for token in ("qa-lab", "artifacts", "previews", "reports")):
                errors.append(f"archivo auxiliar presente: {name}")
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
        play_data = metadata.get("playData", {}) if isinstance(metadata.get("playData", {}), dict) else {}
        album_id = play_data.get("album")
        if not isinstance(album_id, str) or not album_id:
            errors.append("playData.album ausente")
        if metadata.get("album") is not None:
            errors.append("album fuera de playData")
        if isinstance(album_id, str) and album_id:
            album_path = prefix + f"data/ui/freeplay/albums/{album_id}.json"
            require(names, album_path, errors)
            if album_path in names:
                album = json.loads(archive.read(album_path).decode("utf-8"))
                if album.get("version") != "1.0.3": errors.append("album version")
                for asset_key in ("albumArtAsset", "albumTitleAsset"):
                    asset_value = album.get(asset_key)
                    if not isinstance(asset_value, str):
                        errors.append(f"{asset_key} ausente")
                    else:
                        asset_exists(names, root, asset_value, errors)
        level_names = sorted(name for name in names if name.startswith(prefix + "data/levels/") and name.endswith(".json"))
        if not level_names:
            errors.append("data/levels ausente")
        for level_path in level_names:
            level_data = json.loads(archive.read(level_path).decode("utf-8"))
            if level_data.get("version") != "1.0.2": errors.append(f"level version: {level_path}")
            if level_data.get("visible") is False: errors.append(f"level invisible: {level_path}")
            if song not in level_data.get("songs", []): errors.append(f"song absent from level: {level_path}")
            title_asset = level_data.get("titleAsset")
            if not isinstance(title_asset, str):
                errors.append(f"titleAsset ausente: {level_path}")
            else:
                asset_exists(names, root, title_asset, errors)
            for asset_path in collect_asset_paths(level_data):
                asset_exists(names, root, asset_path, errors)
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
    output = root / "qa-lab" / "rebuild-v220" / "v2.2.0-install-layout.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("packages", "passed", "collection", "status")}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
