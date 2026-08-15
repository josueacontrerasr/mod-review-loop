#!/usr/bin/env python3
"""Alinea los 20 mods con el layout V-Slice oficial sin tocar contenido musical."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOVED_DIRS = ("characters", "stages", "notes", "ui")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def move_tree(src: Path, dst: Path) -> int:
    if not src.exists():
        return 0
    moved = 0
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        target = dst / item.name
        if target.exists():
            if item.is_dir() and target.is_dir():
                moved += move_tree(item, target)
                item.rmdir()
            else:
                raise RuntimeError(f"colisión de asset: {target}")
        else:
            shutil.move(str(item), str(target))
            moved += 1
    try:
        src.rmdir()
    except OSError:
        pass
    return moved


def main() -> int:
    mods = sorted(path for path in (ROOT / "mods").glob("esperon-dano-*") if path.is_dir())
    entries = []
    for mod in mods:
        song_dirs = sorted(path for path in (mod / "data/songs").glob("*") if path.is_dir())
        if len(song_dirs) != 1:
            raise RuntimeError(f"{mod.name}: se esperaban 1 carpeta de canción y hay {len(song_dirs)}")
        song_dir = song_dirs[0]
        chart = next(song_dir.glob("*-chart.json"))
        metadata = next(song_dir.glob("*-metadata.json"))
        inst = mod / "songs" / song_dir.name / "Inst.ogg"
        before = {"chart_sha256": sha256(chart), "metadata_sha256": sha256(metadata), "inst_sha256": sha256(inst)}
        moved = {}
        for dirname in MOVED_DIRS:
            moved[dirname] = move_tree(mod / "images" / dirname, mod / "shared/images" / dirname)
        manifest_path = song_dir / "manifest.json"
        manifest_created = False
        if not manifest_path.exists():
            manifest_path.write_text(json.dumps({"version": "1.0.0", "songId": song_dir.name}, indent=2) + "\n", encoding="utf-8")
            manifest_created = True
        after = {"chart_sha256": sha256(chart), "metadata_sha256": sha256(metadata), "inst_sha256": sha256(inst)}
        if before != after:
            raise RuntimeError(f"integridad musical violada: {mod.name}")
        required = [
            mod / "shared/images/characters",
            mod / "shared/images/stages",
            mod / "shared/images/notes",
            mod / "shared/images/ui",
        ]
        missing_dirs = [str(path.relative_to(mod)) for path in required if not path.exists()]
        if missing_dirs:
            raise RuntimeError(f"{mod.name}: faltan directorios shared: {missing_dirs}")
        entries.append({"mod": mod.name, "song": song_dir.name, "moved": moved, "manifest_created": manifest_created, "protected_hashes": after, "status": "PASS"})
    payload = {
        "scope": "VSLICE_SHARED_ASSET_LAYOUT_REPAIR",
        "mods": len(mods),
        "changed": sum(any(item["moved"].values()) or item["manifest_created"] for item in entries),
        "entries": entries,
        "status": "PASS" if len(mods) == 20 and all(item["status"] == "PASS" for item in entries) else "ERRORS_FOUND",
        "contract": "shared:<asset> resolves under shared/images/<asset>",
        "music_policy": "Hashes de Inst.ogg, metadata y chart deben permanecer sin cambios.",
    }
    output = ROOT / "qa-lab" / "session-zip-structure" / "asset-layout-repair.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods": payload["mods"], "changed": payload["changed"], "status": payload["status"]}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
