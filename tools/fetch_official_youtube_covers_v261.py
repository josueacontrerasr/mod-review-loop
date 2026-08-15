#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image
from io import BytesIO

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha(path: Path) -> str:
    digest = hashlib.sha256(); digest.update(path.read_bytes()); return digest.hexdigest()


def one(root: Path, song: str) -> dict:
    page = f"https://music.youtube.com/search?q={quote_plus('Esperón ' + song.replace('-', ' '))}"
    response = requests.get(page, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response.raise_for_status()
    html = response.text
    urls = []
    for match in re.findall(r"https://i\.ytimg\.com/vi/([A-Za-z0-9_-]{6,})/(?:hqdefault|maxresdefault)\.jpg[^\"']*", html):
        if match not in urls: urls.append(match)
    if not urls:
        return {"song": song, "status": "ERROR", "errors": ["no_youtube_thumbnail_found"], "page": page}
    video_id = urls[0]
    candidates = [f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"]
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-youtube-covers" / f"{song}.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)
    chosen = None
    for url in candidates:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code != 200: continue
        try:
            with Image.open(BytesIO(r.content)) as image:
                image.verify()
            output.write_bytes(r.content); chosen = url; break
        except Exception: continue
    if chosen is None:
        return {"song": song, "status": "ERROR", "errors": ["thumbnail_download_failed"], "page": page, "video_id": video_id}
    with Image.open(output) as image: size = list(image.size)
    return {"song": song, "status": "PASS", "page": page, "video_id": video_id, "thumbnail_url": chosen, "path": str(output.relative_to(root)), "sha256": sha(output), "size": size}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows = sorted(pool.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "OFFICIAL_YOUTUBE_MUSIC_COVERS_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-youtube-covers-v261.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
