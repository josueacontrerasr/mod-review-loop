#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "Mods .zip terminados"
PREFIX = "esperon-dano-"
VERSION = "2.6.0"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
FIXED_DATE = (2020, 1, 1, 0, 0, 0)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def display(song: str) -> str:
    return "-".join(word.capitalize() for word in song.split("-"))


def write_deterministic(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=FIXED_DATE)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)


def package_mod(song: str) -> Path:
    mod = ROOT / "mods" / f"{PREFIX}{song}"
    output = DELIVERY / f"Mod-{display(song)}-V{VERSION}.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(item for item in mod.rglob("*") if item.is_file()):
            relative = path.relative_to(mod.parent)
            write_deterministic(archive, relative.as_posix(), path.read_bytes())
    return output


def main() -> int:
    DELIVERY.mkdir(parents=True, exist_ok=True)
    for old in DELIVERY.glob("*.zip"):
        old.unlink()
    packages = [package_mod(song) for song in SONGS]
    manifest = {
        "version": VERSION,
        "status": "PASS",
        "mods": len(packages),
        "policy": "Vocal-only charts; Inst.ogg never generates notes",
        "packages": [{"file": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in packages],
    }
    manifest_path = ROOT / "qa-lab" / "rebuild-v260" / "vocal-only" / "package-manifest-v260.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    collection = DELIVERY / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    readme = "Esperón FNF Mobile V-Slice 0.8.6 V2.6.0\n\nCharts vocal-only: las flechas se generan exclusivamente desde Voices-*.ogg; el instrumental no genera notas. Contiene 20 ZIPs individuales.\n"
    with zipfile.ZipFile(collection, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        write_deterministic(archive, "README-INSTALACION.txt", readme.encode("utf-8"))
        for package in packages:
            write_deterministic(archive, package.name, package.read_bytes())
    print(json.dumps({"status": "PASS", "version": VERSION, "mods": len(packages), "collection": collection.name, "delivery_zips": len(list(DELIVERY.glob("*.zip"))), "manifest": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
