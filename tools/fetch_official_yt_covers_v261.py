#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import json
import subprocess
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
OFFICIAL_CHANNELS = {"UCTgHpxojLQgDd04ko9uPqaA", "UCAd2i_6WeGwyeeJ-zmcdJgg"}
EXCLUDED_TITLE_TERMS = ("instrumental", "slowed", "speed up", "versión lenta", "versión rápida", "acapella", "remix")


def one(root: Path, song: str) -> dict:
    query = f"ytsearch8:Esperón {song.replace('-', ' ')}"
    try:
        proc = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download", query], capture_output=True, text=True, timeout=90, check=True)
        data = json.loads(proc.stdout)
        entries = data.get("entries", [])
    except Exception as exc:
        return {"song": song, "status": "ERROR", "errors": [f"yt_dlp:{type(exc).__name__}:{exc}"]}
    usable = [entry for entry in entries if entry and entry.get("id")]
    official = [entry for entry in usable if entry.get("channel_id") in OFFICIAL_CHANNELS or entry.get("uploader_id") in OFFICIAL_CHANNELS or (entry.get("channel") or "").lower() in ("esperón", "esperón - topic")]
    original = [entry for entry in official if not any(term in (entry.get("title") or "").lower() for term in EXCLUDED_TITLE_TERMS)]
    selected = (original or official or usable)[0] if (original or official or usable) else None
    if not selected:
        return {"song": song, "status": "ERROR", "errors": ["no_yt_result"], "query": query}
    video_id = selected["id"]
    out = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-youtube-covers" / f"{song}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    chosen = None
    for url in (f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"):
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as image:
                image.verify()
            out.write_bytes(response.content); chosen = url; break
        except Exception:
            continue
    if chosen is None:
        return {"song": song, "status": "ERROR", "errors": ["thumbnail_download_failed"], "video_id": video_id, "title": selected.get("title"), "channel_id": selected.get("channel_id")}
    with Image.open(out) as image: size = list(image.size)
    return {"song": song, "status": "PASS", "title": selected.get("title"), "video_id": video_id, "video_url": f"https://www.youtube.com/watch?v={video_id}", "channel": selected.get("channel"), "channel_id": selected.get("channel_id"), "thumbnail_url": chosen, "path": str(out.relative_to(root)), "size": size, "selection": "official_channel_preferred_non_instrumental"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows = sorted(pool.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "OFFICIAL_YT_DLP_COVERS_V261", "executed_at": datetime.now(timezone.utc).isoformat(), "official_channel_ids": sorted(OFFICIAL_CHANNELS), "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows}
    output = root / "qa-lab" / "rebuild-v260" / "playstate-fix" / "official-yt-dlp-covers-v261.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
