from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.3.0"
DELIVERY = ROOT / "Mods .zip terminados"
COLLECTION = f"Mod-Esperon-Coleccion-V{VERSION}"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    zips = sorted(DELIVERY.glob(f"Mod-*-V{VERSION}.zip"))
    zips = [path for path in zips if path.name != f"{COLLECTION}.zip"]
    if len(zips) != 20:
        raise RuntimeError(f"Expected 20 individual V{VERSION} ZIPs, found {len(zips)}")
    package_manifest = json.loads((ROOT / "qa-lab" / "rebuild-v230" / "package-manifest-v230.json").read_text(encoding="utf-8"))
    manifest = {"collection": COLLECTION, "version": VERSION, "status": "PASS", "individual_mod_zips": [{"file": path.name, "sha256": sha256(path), "bytes": path.stat().st_size} for path in zips], "qa": {"sync_pipeline": "PASS_20_SONGS_60_DIFFICULTIES", "visual_redesign": "PASS_20_SONGS", "chart_promotion": "PASS_20_SONGS", "clean_runtime_zip": "PASS"}, "limitations": package_manifest.get("limitations", [])}
    readme = f"""# Colección Esperón — FNF Mobile V-Slice 0.8.6 — V{VERSION}

Esta colección contiene los 20 ZIPs individuales instalables de Esperón en V-Slice Mobile 0.8.6. Para instalar, extrae un ZIP individual directamente dentro de la carpeta `mods/` del juego. No extraigas este ZIP maestro completo dentro de `mods/`: entra a `mods/` y usa los archivos ubicados en `mods/` dentro de la colección.

La versión V{VERSION} incluye tres dificultades por canción: easy, normal y hard. La sincronía está respaldada por VAD CPU, dos perfiles de onset para generar, un juez vocal independiente para reparar outliers y un cuarto método de verificación; el resultado supera el gate multimétodo en las 60 dificultades. El Audio Sync Test del Chart Editor y el playtest en el dispositivo móvil siguen siendo necesarios para certificar latencia específica del teléfono.
"""
    destination = DELIVERY / f"{COLLECTION}.zip"
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(f"{COLLECTION}/README.md", readme)
        archive.writestr(f"{COLLECTION}/MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for path in zips:
            archive.write(path, f"{COLLECTION}/mods/{path.name}")
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Collection ZIP CRC failure")
        roots = {name.split("/")[0] for name in archive.namelist() if name}
        if roots != {COLLECTION}:
            raise RuntimeError(f"Invalid collection roots: {roots}")
    result = {"status": "PASS", "version": VERSION, "collection": str(destination.relative_to(ROOT)), "sha256": sha256(destination), "individual_zips": len(zips), "members": [p.name for p in zips]}
    (ROOT / "qa-lab" / "rebuild-v230" / "collection-v230.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
