#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def apply_one(root: Path, source_dir: Path, backup_dir: Path, song: str) -> dict[str, Any]:
    from PIL import Image, ImageOps
    source = source_dir / f"{song}.jpg"
    mod = root / "mods" / f"esperon-dano-{song}"
    art = mod / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-art.png"
    album_json = mod / "data" / "ui" / "freeplay" / "albums" / f"esperon-{song}.json"
    if not source.is_file(): return {"song": song, "status": "ERROR", "errors": [f"source_missing:{source}"]}
    if not art.is_file(): return {"song": song, "status": "ERROR", "errors": [f"target_missing:{art}"]}
    backup = backup_dir / f"{song}-art-before.png"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(art, backup)
    with Image.open(source) as image:
        source_size = image.size
        rgba = image.convert("RGBA")
        square = ImageOps.fit(rgba, (512, 512), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        square.save(art, format="PNG", optimize=True)
    album = json.loads(album_json.read_text(encoding="utf-8"))
    expected_path = f"freeplay/albumRoll/esperon-{song}-art"
    errors = []
    if album.get("albumArtAsset") != expected_path: errors.append(f"albumArtAsset:{album.get('albumArtAsset')}")
    with Image.open(art) as result:
        if result.size != (512, 512): errors.append(f"output_size:{result.size}")
        if result.mode not in ("RGB", "RGBA"): errors.append(f"output_mode:{result.mode}")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "source": str(source.relative_to(root.parent.parent.parent)), "source_sha256": sha(source), "source_size": source_size, "target": str(art.relative_to(root)), "target_sha256": sha(art), "target_size": [512, 512], "album_art_asset": album.get("albumArtAsset"), "backup": str(backup.relative_to(root)), "crop": "center_crop_to_square_then_512x512", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    source_dir = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "cover-sources"
    backup_dir = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "cover-backup-v260"
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = sorted(pool.map(lambda song: apply_one(root, source_dir, backup_dir, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "FREEPLAY_ORIGINAL_COVERS_V260", "executed_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "target_dimensions": [512, 512], "asset_contract": "freeplay/albumRoll/<song>-art", "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "freeplay-covers-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
