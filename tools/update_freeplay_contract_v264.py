#!/usr/bin/env python3
"""Normalize and verify the official V-Slice 0.8.6 Freeplay album contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GENERATED_BY = "FNF Mobile V-Slice 0.8.6 V2.6.4 Freeplay album asset contract"


def main() -> int:
    rows = []
    errors: list[str] = []
    for mod in sorted((ROOT / "mods").glob("esperon-dano-*")):
        song_dirs = sorted(p for p in (mod / "data" / "songs").glob("*") if p.is_dir())
        if len(song_dirs) != 1:
            errors.append(f"{mod.name}: expected one song directory, found {len(song_dirs)}")
            continue
        song_dir = song_dirs[0]
        song = song_dir.name
        metadata_path = song_dir / f"{song}-metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        play_data = metadata.get("playData")
        album_id = play_data.get("album") if isinstance(play_data, dict) else None
        if not isinstance(album_id, str) or not album_id:
            errors.append(f"{mod.name}: missing playData.album")
            continue
        album_path = mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json"
        if not album_path.is_file():
            errors.append(f"{mod.name}: missing {album_path.relative_to(ROOT)}")
            continue
        album = json.loads(album_path.read_text(encoding="utf-8"))
        expected_art = f"freeplay/albumRoll/{album_id}-art"
        expected_title = f"freeplay/albumRoll/{album_id}-title"
        if album.get("version") != "1.0.3":
            errors.append(f"{mod.name}: album version={album.get('version')!r}")
        if album.get("albumArtAsset") != expected_art:
            errors.append(f"{mod.name}: albumArtAsset={album.get('albumArtAsset')!r}, expected={expected_art!r}")
        if album.get("albumTitleAsset") != expected_title:
            errors.append(f"{mod.name}: albumTitleAsset={album.get('albumTitleAsset')!r}, expected={expected_title!r}")
        art_path = mod / "images" / f"{expected_art}.png"
        title_png = mod / "images" / f"{expected_title}.png"
        title_xml = mod / "images" / f"{expected_title}.xml"
        for path in (art_path, title_png, title_xml):
            if not path.is_file():
                errors.append(f"{mod.name}: missing {path.relative_to(ROOT)}")
        album["generatedBy"] = EXPECTED_GENERATED_BY
        album_path.write_text(json.dumps(album, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append({
            "mod": mod.name,
            "song": song,
            "album": album_id,
            "albumArtAsset": album["albumArtAsset"],
            "albumTitleAsset": album["albumTitleAsset"],
            "art": str(art_path.relative_to(ROOT)),
            "title_png": str(title_png.relative_to(ROOT)),
            "title_xml": str(title_xml.relative_to(ROOT)),
        })
    report = {
        "scope": "V264_FREEPLAY_ALBUM_CONTRACT",
        "target": "FNF Mobile V-Slice 0.8.6",
        "status": "PASS" if len(rows) == 21 and not errors else "FAIL",
        "mods": len(rows),
        "errors": errors,
        "rows": rows,
        "contract": {
            "album_json": "data/ui/freeplay/albums/<playData.album>.json",
            "albumArtAsset": "freeplay/albumRoll/<album>-art",
            "albumTitleAsset": "freeplay/albumRoll/<album>-title",
            "title_assets": [".png", ".xml"],
            "required_title_frames": ["idle0", "switch0"],
        },
    }
    output = ROOT / "qa-lab" / "rebuild-v264" / "freeplay-contract-v264.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "mods": report["mods"], "errors": len(errors), "output": str(output)}, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

