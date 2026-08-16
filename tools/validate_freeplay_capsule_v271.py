from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from diagnose_freeplay_capsule_v271 import SONGS, audit_song

EXPECTED_GENERATED = "FNF Mobile V-Slice 0.8.6 V2.7.1 Freeplay capsule + album asset contract"


def validate_album_title(mod: Path, album_assets: dict, errors: list[str]) -> dict:
    title = album_assets.get("albumTitleAsset", {})
    png_info = title.get("png", {})
    xml_path = Path(title.get("xml_path", ""))
    report = {"png": png_info, "xml": str(xml_path.relative_to(mod)) if xml_path.is_file() else str(xml_path), "frames": []}
    if not png_info.get("exists"):
        errors.append("album_title_png_missing")
        return report
    if png_info.get("size") not in ([512, 128], [512, 512]):
        errors.append(f"album_title_png_unexpected_size:{png_info.get('size')}")
    if not xml_path.is_file():
        errors.append("album_title_xml_missing")
        return report
    try:
        root = ET.parse(xml_path).getroot()
        image_path = root.attrib.get("imagePath")
        png_name = Path(png_info["path"]).name
        if image_path != png_name:
            errors.append(f"album_title_imagePath_mismatch:{image_path}!={png_name}")
        names = [node.attrib.get("name", "") for node in root.findall(".//SubTexture")]
        report["frames"] = names
        if not any(name.startswith("idle0") for name in names):
            errors.append("album_title_missing_idle0")
        if not any(name.startswith("switch0") for name in names):
            errors.append("album_title_missing_switch0")
        with_png = png_info.get("size") or [0, 0]
        width, height = with_png
        for node in root.findall(".//SubTexture"):
            attrs = node.attrib
            x, y, w, h = (int(attrs.get(key, -1)) for key in ("x", "y", "width", "height"))
            if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                errors.append(f"album_title_frame_out_of_bounds:{attrs.get('name')}")
    except Exception as exc:
        errors.append(f"album_title_xml_parse_failed:{exc}")
    return report


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    rows = []
    errors = []
    art_hashes: dict[str, list[str]] = {}
    for song in SONGS:
        row = audit_song(root, song)
        row_errors = list(row["errors"])
        if row["level_count"] != 1:
            row_errors.append("capsule_level_count_not_one")
        for level in row["levels"]:
            title_png = level["titleAsset"]["png"]
            if not title_png.get("exists") or not title_png.get("nontransparent"):
                row_errors.append("capsule_titleAsset_missing_or_transparent")
            if title_png.get("size") not in ([900, 220], [512, 256], [512, 512]):
                row_errors.append(f"capsule_titleAsset_unexpected_size:{title_png.get('size')}")
        art = row.get("album_assets", {}).get("albumArtAsset", {}).get("png", {})
        if art.get("size") != [512, 512]:
            row_errors.append(f"album_art_unexpected_size:{art.get('size')}")
        if art.get("sha256"):
            art_hashes.setdefault(art["sha256"], []).append(song)
        album_report = validate_album_title(root / "mods" / row["mod"], row.get("album_assets", {}), row_errors)
        row["album_title_gate"] = album_report
        row["errors"] = sorted(set(row_errors))
        row["status"] = "PASS" if not row["errors"] else "ERRORS_FOUND"
        rows.append(row)
    for digest, songs in art_hashes.items():
        if len(songs) > 1:
            for song in songs:
                for row in rows:
                    if row["song"] == song:
                        row["errors"].append(f"duplicate_album_art_sha256:{digest[:12]}:{','.join(songs)}")
                        row["status"] = "ERRORS_FOUND"
    errors = [{"song": row["song"], "errors": row["errors"]} for row in rows if row["errors"]]
    payload = {
        "scope": "FREEPLAY_CAPSULE_AND_ALBUM_GATE_V271",
        "target_version": "0.8.6",
        "mod_version": "2.7.1",
        "generatedBy": EXPECTED_GENERATED,
        "mods": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "status": "PASS" if len(rows) == 21 and not errors else "ERRORS_FOUND",
        "errors": errors,
        "rows": rows,
        "rules": {
            "capsule_asset": "data/levels/*.json titleAsset -> images/storymenu/*.png",
            "album_asset": "playData.album -> data/ui/freeplay/albums/<id>.json -> images/freeplay/albumRoll/*.png",
            "album_title_frames": ["idle0", "switch0"],
            "duplicate_album_art_rejected": True,
        },
    }
    out = root / "qa-lab" / "rebuild-v271" / "freeplay-capsule-gate-v271.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "mods": len(rows), "passed": payload["passed"], "errors": len(errors), "output": str(out)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
