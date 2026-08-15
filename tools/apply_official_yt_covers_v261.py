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
from PIL import Image, ImageOps

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha(path: Path) -> str:
    digest = hashlib.sha256(); digest.update(path.read_bytes()); return digest.hexdigest()


def one(root: Path, source_dir: Path, backup_dir: Path, song: str) -> dict[str, Any]:
    source = source_dir / f"{song}.jpg"; art = root / "mods" / f"esperon-dano-{song}" / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-art.png"
    if not source.is_file() or not art.is_file(): return {"song": song, "status": "ERROR", "errors": [f"missing:{source if not source.is_file() else art}"]}
    backup_dir.mkdir(parents=True, exist_ok=True); backup = backup_dir / f"{song}-before-official.png"; shutil.copy2(art, backup)
    with Image.open(source) as image:
        source_size = list(image.size); square = ImageOps.fit(image.convert("RGBA"), (512, 512), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)); square.save(art, format="PNG", optimize=True)
    with Image.open(art) as result: size = list(result.size); bbox = result.getbbox()
    return {"song": song, "status": "PASS" if size == [512, 512] and bbox is not None else "ERRORS_FOUND", "source": str(source.relative_to(root)), "source_sha256": sha(source), "source_size": source_size, "target": str(art.relative_to(root)), "target_sha256": sha(art), "target_size": size, "backup": str(backup.relative_to(root)), "crop": "center_crop_to_square_then_512x512", "errors": [] if size == [512, 512] and bbox is not None else ["invalid_output"]}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); parser.add_argument("--workers", type=int, default=8); args = parser.parse_args(); root = args.root.resolve()
    source_dir = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-youtube-covers"; backup_dir = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-cover-backup-v261"
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool: rows = sorted(pool.map(lambda song: one(root, source_dir, backup_dir, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "APPLY_OFFICIAL_YOUTUBE_COVERS_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-cover-apply-v261.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
