#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
VERSION = "2.6.5"
EXCLUDED_SUFFIXES = {".txt", ".md", ".log", ".csv", ".html", ".bak"}
FIXED_DATE = (2020, 1, 1, 0, 0, 0)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_files(mod: Path) -> list[Path]:
    return sorted((path for path in mod.rglob("*") if path.is_file() and path.suffix.lower() not in EXCLUDED_SUFFIXES), key=lambda path: path.relative_to(mod).as_posix())


def make_zip(output: Path, folders: list[Path]) -> dict[str, Any]:
    included: list[str] = []
    excluded: list[str] = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for folder in folders:
            for path in runtime_files(folder):
                relative = path.relative_to(folder.parent).as_posix()
                info = zipfile.ZipInfo(relative, date_time=FIXED_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
                included.append(relative)
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in EXCLUDED_SUFFIXES:
                    excluded.append(path.relative_to(folder.parent).as_posix())
    return {"path": str(output), "sha256": sha(output), "folders": [folder.name for folder in folders], "file_count": len(included), "excluded_count": len(excluded), "excluded": sorted(excluded)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    delivery = root / "Mods .zip terminados"
    delivery.mkdir(parents=True, exist_ok=True)
    for entry in delivery.iterdir():
        if entry.is_dir(): shutil.rmtree(entry)
        else: entry.unlink()
    mods = [root / "mods" / f"esperon-dano-{song}" for song in SONGS]
    missing = [str(path) for path in mods if not path.is_dir()]
    if missing: raise SystemExit(f"missing_mods:{missing}")
    rows = []
    for song, mod in zip(SONGS, mods):
        title = "-".join(word.capitalize() for word in song.split("-"))
        output = delivery / f"Mod-{title}-V{VERSION}.zip"
        rows.append(make_zip(output, [mod]))
    complete = make_zip(delivery / "Esperon-Completo.zip", mods)
    manifest = {"scope": "ESPERON_COMPLETE_PACKAGE_V265", "executed_at": datetime.now(timezone.utc).isoformat(), "mod_version": VERSION, "songs": len(SONGS), "individual_zips": len(rows), "complete_zip": complete, "individual": rows, "delivery_entries": sorted(path.name for path in delivery.iterdir()), "status": "PASS" if len(rows) == 21 and complete["folders"] == [mod.name for mod in mods] else "ERRORS_FOUND", "policy": "Delivery contains only final ZIPs; runtime ZIPs exclude reports and text artifacts."}
    output = root / "qa-lab" / "rebuild-v265" / "playstate-fix" / "package-manifest-v265.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": manifest["songs"], "individual_zips": manifest["individual_zips"], "complete_zip": complete["path"], "complete_file_count": complete["file_count"], "delivery_entries": len(manifest["delivery_entries"]), "status": manifest["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
