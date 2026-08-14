#!/usr/bin/env python3
"""Organiza una única carpeta de ZIP finales y conserva históricos fuera de ella."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from hashlib import sha256
from pathlib import Path

VERSION_RE = re.compile(r"^(esperon-dano-(?P<song>.+)-v(?P<version>\d+\.\d+\.\d+))\.zip$")
COLLECTION_RE = re.compile(r"^esperon-vslice-086-collection-v(?P<version>\d+\.\d+\.\d+)\.zip$")


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_song_name(song: str) -> str:
    return "-".join(part[:1].upper() + part[1:] for part in song.split("-") if part)


def inspect_zip(path: Path, collection: bool = False) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken:
                return False, f"CRC inválido: {broken}"
            roots = {name.split("/")[0] for name in archive.namelist() if name and not name.startswith("__MACOSX")}
            if collection:
                single_root = next((root for root in roots if root.startswith("Mod-Esperon-Coleccion-V")), "")
                if roots == {single_root}:
                    return True, "colección autocontenida"
                if len(roots) == 20 and all(root.endswith(".zip") for root in roots):
                    return True, "20 ZIP individuales"
                return False, f"formato de colección inesperado: {len(roots)} raíces"
            if len(roots) != 1:
                return False, f"se esperaban 1 raíz y hay {len(roots)}"
            return True, next(iter(roots))
    except (OSError, zipfile.BadZipFile) as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--latest-version", default="2.2.0")
    parser.add_argument("--include-collection", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    source = root / "dist"
    latest = root / "Mods .zip terminados"
    history = source / "historico"
    latest.mkdir(parents=True, exist_ok=True)
    history.mkdir(parents=True, exist_ok=True)

    candidates: list[tuple[Path, str, str]] = []
    for path in sorted(source.glob("*.zip")):
        match = VERSION_RE.match(path.name)
        if match and match.group("version") == args.latest_version:
            song = match.group("song")
            candidates.append((path, song, f"Mod-{canonical_song_name(song)}-V{args.latest_version}.zip"))
        elif args.include_collection:
            collection = COLLECTION_RE.match(path.name)
            if collection and collection.group("version") == args.latest_version:
                candidates.append((path, "__collection__", f"Mod-Esperon-Coleccion-V{args.latest_version}.zip"))

    if not candidates:
        # Permite reanudar una migración que ya movió los archivos desde dist/.
        for path in sorted(latest.glob("*.zip")):
            match = re.match(r"^Mod-(?P<song>.+)-V(?P<version>\d+\.\d+\.\d+)\.zip$", path.name)
            if not match or match.group("version") != args.latest_version:
                continue
            if match.group("song") == "Esperon-Coleccion":
                candidates.append((path, "__collection__", path.name))
            else:
                candidates.append((path, match.group("song").lower(), path.name))

    if len([entry for entry in candidates if entry[1] != "__collection__"]) != 20:
        raise SystemExit(f"Se esperaban 20 ZIP individuales v{args.latest_version}; se encontraron {len([entry for entry in candidates if entry[1] != '__collection__'])}.")
    if len({entry[1] for entry in candidates if entry[1] != "__collection__"}) != 20:
        raise SystemExit("Hay canciones duplicadas en la selección final.")

    selected_sources = {path.resolve() for path, _, _ in candidates}
    # Mueve todos los ZIP anteriores y las colecciones fuera de la carpeta descargable.
    for path in sorted(source.glob("*.zip")):
        if path.resolve() in selected_sources:
            continue
        target = history / path.name
        if target.exists():
            target.unlink()
        shutil.move(str(path), str(target))

    # Elimina solo antiguos ZIPs de la misma canción en la carpeta final; otros archivos son un error.
    for path in latest.iterdir():
        if path.is_file() and path.suffix.lower() == ".zip":
            if path.name not in {name for _, _, name in candidates}:
                target = history / path.name
                if target.exists():
                    target.unlink()
                shutil.move(str(path), str(target))
        elif path.is_file() or path.is_symlink():
            raise SystemExit(f"La carpeta final contiene un archivo no ZIP: {path.name}")
        elif path.is_dir():
            raise SystemExit(f"La carpeta final contiene un directorio inesperado: {path.name}")

    records = []
    for source_path, song, output_name in candidates:
        output = latest / output_name
        if source_path.resolve() != output.resolve():
            if output.exists():
                output.unlink()
            shutil.move(str(source_path), str(output))
        valid, root_name = inspect_zip(output, collection=(song == "__collection__"))
        if not valid:
            raise SystemExit(f"ZIP inválido {output.name}: {root_name}")
        records.append({"song": song, "file": output.relative_to(root).as_posix(), "sha256": digest(output), "bytes": output.stat().st_size, "zip_root": root_name})

    contents = sorted(path.name for path in latest.iterdir())
    if any(not name.endswith(".zip") for name in contents):
        raise SystemExit("La carpeta final contiene algo que no es ZIP.")
    report = {
        "folder": latest.relative_to(root).as_posix(),
        "latest_version": args.latest_version,
        "individual_mods": len([item for item in records if item["song"] != "__collection__"]),
        "collection_included": any(item["song"] == "__collection__" for item in records),
        "files": records,
        "status": "PASS",
    }
    output = root / "qa-lab" / "final" / "final-zip-delivery-inventory.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"folder": report["folder"], "files": len(records), "individual_mods": report["individual_mods"], "status": report["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
