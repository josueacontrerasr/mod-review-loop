#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
DIFFICULTIES = ("easy", "normal", "hard")


def one(root: Path, song: str) -> dict[str, Any]:
    mod = root / "mods" / f"esperon-dano-{song}"
    errors: list[str] = []
    def rel(path: Path) -> str: return str(path.relative_to(root))
    polymod = mod / "_polymod_meta.json"
    if not polymod.is_file(): errors.append("polymod_missing")
    else:
        data = json.loads(polymod.read_text(encoding="utf-8"))
        if data.get("api_version") != "0.8.6": errors.append(f"api_version:{data.get('api_version')}")
        if data.get("mod_version") != "2.6.2": errors.append(f"mod_version:{data.get('mod_version')}")
    data_dir = mod / "data" / "songs" / song
    manifest_path = data_dir / "manifest.json"
    metadata_path = data_dir / f"{song}-metadata.json"
    chart_path = data_dir / f"{song}-chart.json"
    for path in (manifest_path, metadata_path, chart_path):
        if not path.is_file(): errors.append(f"missing:{rel(path)}")
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("songId") != song: errors.append(f"songId:{manifest.get('songId')}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    chart = json.loads(chart_path.read_text(encoding="utf-8")) if chart_path.is_file() else {}
    if metadata.get("version") != "2.2.4": errors.append(f"metadata_version:{metadata.get('version')}")
    if chart.get("version") != "2.0.0": errors.append(f"chart_version:{chart.get('version')}")
    if chart.get("generatedBy") != "Friday Night Funkin' - 0.8.6": errors.append("chart_generatedBy")
    play = metadata.get("playData", {})
    if set(play.get("difficulties", [])) != set(DIFFICULTIES): errors.append(f"metadata_difficulties:{play.get('difficulties')}")
    if set(chart.get("notes", {}).keys()) != set(DIFFICULTIES): errors.append(f"chart_difficulties:{sorted(chart.get('notes', {}).keys())}")
    for diff in DIFFICULTIES:
        notes = chart.get("notes", {}).get(diff, [])
        if not isinstance(notes, list): errors.append(f"notes_not_array:{diff}"); continue
        for i, note in enumerate(notes):
            if set(note) - {"t", "d", "l", "k", "p"}: errors.append(f"note_extra_fields:{diff}:{i}")
            if "t" not in note or "d" not in note: errors.append(f"note_required:{diff}:{i}")
            if not isinstance(note.get("d"), int) or not 0 <= note.get("d", -1) <= 3: errors.append(f"lane:{diff}:{i}")
    album_json = mod / "data" / "ui" / "freeplay" / "albums" / f"esperon-{song}.json"
    art = mod / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-art.png"
    title = mod / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-title.png"
    title_xml = mod / "images" / "freeplay" / "albumRoll" / f"esperon-{song}-title.xml"
    if not album_json.is_file(): errors.append("album_json_missing")
    else:
        album = json.loads(album_json.read_text(encoding="utf-8"))
        if album.get("albumArtAsset") != f"freeplay/albumRoll/esperon-{song}-art": errors.append("album_art_path")
    for path in (art, title, title_xml):
        if not path.is_file(): errors.append(f"freeplay_missing:{rel(path)}")
    for path, expected in ((art, (512, 512)), (title, (512, 128))):
        if path.is_file():
            try:
                with Image.open(path) as image:
                    if image.size != expected: errors.append(f"image_size:{path.name}:{image.size}")
                    if image.getbbox() is None: errors.append(f"image_empty:{path.name}")
            except Exception as exc: errors.append(f"image_invalid:{path.name}:{exc}")
    if title_xml.is_file():
        try: ET.parse(title_xml)
        except Exception as exc: errors.append(f"title_xml_invalid:{exc}")
    required_assets = [
        mod / "data" / "characters" / f"esperon-{song}.json",
        mod / "data" / "characters" / f"rival-{song}.json",
        mod / "data" / "stages" / f"escenario-{song}.json",
        mod / "data" / "notestyles" / f"esperon-{song}-notes.json",
        mod / "scripts" / f"Esperon{''.join(part.capitalize() for part in song.split('-'))}HudV2.hxc",
        mod / "shared" / "images" / "characters" / f"esperon-{song}.png",
        mod / "shared" / "images" / "characters" / f"esperon-{song}.xml",
        mod / "shared" / "images" / "characters" / f"rival-{song}.png",
        mod / "shared" / "images" / "characters" / f"rival-{song}.xml",
        mod / "shared" / "images" / "stages" / f"escenario-{song}.png",
    ]
    for path in required_assets:
        if not path.is_file(): errors.append(f"asset_missing:{rel(path)}")
    script = mod / "scripts" / f"Esperon{''.join(part.capitalize() for part in song.split('-'))}HudV2.hxc"
    if script.is_file():
        text = script.read_text(encoding="utf-8")
        if "import funkin.modding.module.Module" not in text or "extends Module" not in text: errors.append("hscript_module_contract")
    return {"song": song, "status": "PASS" if not errors else "ERRORS_FOUND", "notes": {d: len(chart.get("notes", {}).get(d, [])) for d in DIFFICULTIES}, "cover": {"path": rel(art), "size": [512, 512] if art.is_file() else None}, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); parser.add_argument("--workers", type=int, default=8); args = parser.parse_args()
    root = args.root.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool: rows = sorted(pool.map(lambda song: one(root, song), SONGS), key=lambda row: row["song"])
    payload = {"scope": "VSLICE_086_CONTRACTS_ASSETS_V262", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": "2.6.2", "songs": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "ERRORS_FOUND", "rows": rows}
    output = root / "qa-lab" / "rebuild-v262" / "playstate-fix" / "contracts-assets-v262.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "passed": payload["passed"], "status": payload["status"], "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
