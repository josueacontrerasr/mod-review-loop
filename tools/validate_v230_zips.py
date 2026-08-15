from __future__ import annotations

import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.3.0"


def require(names: set[str], path: str, errors: list[str]) -> None:
    if path not in names:
        errors.append(f"missing:{path}")


def collect_asset_paths(value):
    if isinstance(value, dict):
        result = []
        for key, child in value.items():
            if key == "assetPath" and isinstance(child, str):
                result.append(child)
            else:
                result.extend(collect_asset_paths(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(collect_asset_paths(child))
        return result
    return []


def asset_exists(names: set[str], root: str, asset: str, errors: list[str]) -> None:
    if asset.startswith("shared:") or asset.startswith(("characters/", "stages/", "notes/", "ui/")):
        base = root + "/shared/images/" + asset.removeprefix("shared:")
    else:
        base = root + "/images/" + asset
    candidates = {base + ".png", base + ".xml", base + ".astc"}
    if not names.intersection(candidates):
        errors.append(f"asset_missing:{asset}")


def validate_package(path: Path) -> dict:
    errors = []
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                errors.append("crc_failure")
            names = {name.rstrip("/") for name in archive.namelist() if name and not name.startswith("__MACOSX/")}
            roots = {name.split("/", 1)[0] for name in names}
            if len(roots) != 1:
                return {"package": path.name, "status": "ERROR", "errors": [f"roots:{sorted(roots)}"]}
            root = next(iter(roots))
            if not root.startswith("esperon-dano-"):
                errors.append(f"unexpected_root:{root}")
            prefix = root + "/"
            require(names, prefix + "_polymod_meta.json", errors)
            if prefix + "_polymod_meta.json" in names:
                manifest = json.loads(archive.read(prefix + "_polymod_meta.json").decode("utf-8"))
                if manifest.get("api_version") != "0.8.6": errors.append("api_version")
                if manifest.get("mod_version") != VERSION: errors.append("mod_version")
            forbidden_tokens = ("qa-lab", "artifacts", "previews", "reports", "sync-candidates")
            forbidden_root_files = ("final-v222-report.md", "sync-report.json", "audio-evidence.json")
            file_names = {info.filename.rstrip("/") for info in archive.infolist() if not info.is_dir()}
            for name in names:
                relative = name[len(prefix):] if name.startswith(prefix) else name
                if any(token in name.split("/") for token in forbidden_tokens) or any(name.endswith(token) for token in forbidden_root_files):
                    errors.append(f"evidence_inside_zip:{name}")
                if name in file_names and name.startswith(prefix) and "/" not in relative and relative not in {"_polymod_meta.json", "_polymod_icon.png", "_polymod_icon.astc"}:
                    errors.append(f"unexpected_root_file:{relative}")
            song_dirs = sorted(name for name in names if name.startswith(prefix + "data/songs/") and name.count("/") == 3)
            if len(song_dirs) != 1:
                errors.append("song_dir_count")
                return {"package": path.name, "root": root, "status": "ERROR", "errors": errors}
            song = song_dirs[0].split("/")[-1]
            song_prefix = prefix + f"data/songs/{song}/"
            meta_name, chart_name = song_prefix + f"{song}-metadata.json", song_prefix + f"{song}-chart.json"
            require(names, meta_name, errors); require(names, chart_name, errors)
            require(names, prefix + f"data/characters/esperon-{song}.json", errors)
            require(names, prefix + f"data/characters/rival-{song}.json", errors)
            require(names, prefix + f"data/stages/escenario-{song}.json", errors)
            require(names, prefix + f"data/notestyles/esperon-{song}-notes.json", errors)
            require(names, prefix + f"songs/{song}/Inst.ogg", errors)
            if not any(name.startswith(prefix + f"songs/{song}/Voices-") and name.endswith(".ogg") for name in names):
                errors.append("voices_missing")
            if meta_name in names and chart_name in names:
                meta = json.loads(archive.read(meta_name).decode("utf-8")); chart = json.loads(archive.read(chart_name).decode("utf-8"))
                if meta.get("version") != "2.2.4": errors.append("metadata_version")
                if chart.get("version") != "2.0.0": errors.append("chart_version")
                if set(chart.get("notes", {})) != {"easy", "normal", "hard"}: errors.append("difficulty_set")
                for difficulty in ("easy", "normal", "hard"):
                    notes = chart.get("notes", {}).get(difficulty, [])
                    keys = [(round(float(n.get("t", -1)), 3), int(n.get("d", -1))) for n in notes]
                    if not notes: errors.append(f"empty:{difficulty}")
                    if keys != sorted(keys): errors.append(f"unsorted:{difficulty}")
                    if len(keys) != len(set(keys)): errors.append(f"duplicate:{difficulty}")
                    if any(t < 0 or d < 4 or d > 7 for t, d in keys): errors.append(f"domain:{difficulty}")
                play = meta.get("playData", {})
                album_id = play.get("album")
                if isinstance(album_id, str):
                    album_name = prefix + f"data/ui/freeplay/albums/{album_id}.json"; require(names, album_name, errors)
                    if album_name in names:
                        album = json.loads(archive.read(album_name).decode("utf-8"))
                        for key in ("albumArtAsset", "albumTitleAsset"):
                            asset = album.get(key)
                            if not isinstance(asset, str): errors.append(f"album_asset:{key}")
                            else: asset_exists(names, root, asset, errors)
                else:
                    errors.append("album_missing")
                style_id = play.get("noteStyle")
                style_name = prefix + f"data/notestyles/{style_id}.json" if isinstance(style_id, str) else None
                if style_name: require(names, style_name, errors)
            for rel in (f"data/characters/esperon-{song}.json", f"data/characters/rival-{song}.json", f"data/stages/escenario-{song}.json", f"data/notestyles/esperon-{song}-notes.json"):
                path_name = prefix + rel
                if path_name in names:
                    data = json.loads(archive.read(path_name).decode("utf-8"))
                    for asset in collect_asset_paths(data): asset_exists(names, root, asset, errors)
            title_candidates = [name for name in names if name.startswith(prefix + "images/freeplay/albums/") and name.endswith("-title.xml")]
            if not title_candidates:
                errors.append("album_title_xml_missing")
            for title in title_candidates:
                try:
                    text = archive.read(title).decode("utf-8")
                    if "idle0000" not in text or "switch0000" not in text: errors.append("album_title_prefixes")
                except Exception:
                    errors.append("album_title_xml_invalid")
            return {"package": path.name, "root": root, "song": song, "status": "PASS" if not errors else "ERROR", "errors": errors}
    except (zipfile.BadZipFile, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"package": path.name, "status": "ERROR", "errors": [f"exception:{exc}"]}


def main() -> int:
    delivery = ROOT / "Mods .zip terminados"
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if "Coleccion" not in path.name)
    reports = [validate_package(path) for path in packages]
    collection = delivery / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    collection_errors = []
    if not collection.is_file(): collection_errors.append("collection_missing")
    else:
        with zipfile.ZipFile(collection) as archive:
            names = set(archive.namelist())
            collection_root = f"Mod-Esperon-Coleccion-V{VERSION}"
            if archive.testzip() is not None: collection_errors.append("collection_crc")
            for package in packages:
                if f"{collection_root}/mods/{package.name}" not in names: collection_errors.append(f"collection_missing:{package.name}")
    payload = {"scope": "VSLICE_086_INSTALL_LAYOUT", "version": VERSION, "packages": len(packages), "passed": sum(item["status"] == "PASS" for item in reports), "collection": collection.name, "collection_errors": collection_errors, "reports": reports, "status": "PASS" if len(packages) == 20 and not collection_errors and all(item["status"] == "PASS" for item in reports) else "ERRORS_FOUND"}
    output = ROOT / "qa-lab" / "rebuild-v230" / "zip-validation-v230.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packages": payload["packages"], "passed": payload["passed"], "collection": payload["collection"], "status": payload["status"]}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
