#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
DIFFICULTIES = ("easy", "normal", "hard")


def one(root: Path, song: str, round_no: int) -> dict:
    mod = root / "mods" / f"esperon-dano-{song}"; issues = []; files = [path for path in mod.rglob("*") if path.is_file()]
    for path in files:
        try:
            if path.suffix.lower() == ".json": json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".xml": ET.parse(path)
            elif path.suffix.lower() in (".png", ".jpg", ".jpeg"):
                with Image.open(path) as image: image.verify()
            elif path.suffix.lower() == ".ogg" and path.read_bytes()[:4] != b"OggS": issues.append(f"bad_ogg_header:{path.relative_to(mod)}")
        except Exception as exc: issues.append(f"parse:{path.relative_to(mod)}:{exc}")
    try:
        song_dir = mod / "data" / "songs" / song
        poly = json.loads((mod / "_polymod_meta.json").read_text(encoding="utf-8"))
        if poly.get("api_version") != "0.8.6" or poly.get("mod_version") != "2.6.6": issues.append("manifest_contract")
        meta = json.loads((song_dir / f"{song}-metadata.json").read_text(encoding="utf-8")); chart = json.loads((song_dir / f"{song}-chart.json").read_text(encoding="utf-8"))
        if meta.get("version") != "2.2.4" or chart.get("version") != "2.0.0": issues.append("data_version")
        if chart.get("generatedBy") != "Friday Night Funkin' - 0.8.6; V2.6.6 vocal syllable vowel-mapped player lanes d=0..3": issues.append("chart_generatedBy")
        if set(chart.get("notes", {})) != set(DIFFICULTIES): issues.append("difficulty_set")
        counts = {diff: len(chart.get("notes", {}).get(diff, [])) for diff in DIFFICULTIES}
        if not (counts["easy"] < counts["normal"] <= counts["hard"]): issues.append("density_progression")
        for diff, notes in chart.get("notes", {}).items():
            keys = [(float(note.get("t", -1)), int(note.get("d", -1))) for note in notes]
            if keys != sorted(keys) or len(keys) != len(set(keys)): issues.append(f"chart_{diff}_order_or_duplicate")
            if any(t < 0 or d < 0 or d > 3 for t, d in keys): issues.append(f"chart_{diff}_lane_domain")
            if {d for _, d in keys} != {0, 1, 2, 3}: issues.append(f"chart_{diff}_lane_coverage")
        stage_id = meta["playData"]["stage"]; stage = json.loads((mod / "data" / "stages" / f"{stage_id}.json").read_text(encoding="utf-8"))
        if stage.get("directory") != "shared" or set(stage.get("characters", {})) != {"bf", "dad", "gf"}: issues.append("stage_contract")
        for role in ("player", "opponent"):
            cid = meta["playData"]["characters"][role]; character = json.loads((mod / "data" / "characters" / f"{cid}.json").read_text(encoding="utf-8")); asset = character["assetPath"]; base = mod / "shared" / "images" / asset.removeprefix("shared:")
            if not base.with_suffix(".png").is_file() or not base.with_suffix(".xml").is_file(): issues.append(f"character_{role}_asset")
        audio_dir = mod / "songs" / song
        if not (audio_dir / "Inst.ogg").is_file() or len(list(audio_dir.glob("Voices-*.ogg"))) != 1: issues.append("audio")
        album_id = meta["playData"]["album"]; album = json.loads((mod / "data" / "ui" / "freeplay" / "albums" / f"{album_id}.json").read_text(encoding="utf-8"))
        for key in ("albumArtAsset", "albumTitleAsset"):
            asset = album.get(key, "")
            if not asset.startswith("freeplay/albumRoll/") or not (mod / "images" / f"{asset}.png").is_file(): issues.append(f"album_{key}")
        if not (mod / "images" / f"{album['albumTitleAsset']}.xml").is_file(): issues.append("album_title_xml")
        with Image.open(mod / "images" / f"{album['albumArtAsset']}.png") as image:
            if image.size != (512, 512) or image.getbbox() is None: issues.append("album_art_visual")
        style_id = meta["playData"]["noteStyle"]; style = json.loads((mod / "data" / "notestyles" / f"{style_id}.json").read_text(encoding="utf-8"))
        if style.get("version") != "1.0.0" or style.get("fallback") != "funkin": issues.append("note_style_contract")
        script = next((path for path in (mod / "scripts").glob("*.hxc")), None)
        if script is None or "import funkin.modding.module.Module" not in script.read_text(encoding="utf-8") or "extends Module" not in script.read_text(encoding="utf-8"): issues.append("hscript_module")
    except Exception as exc: issues.append(f"contract:{exc}")
    archive_name = f"Mod-{'-'.join(word.capitalize() for word in song.split('-'))}-V2.6.6.zip"; archive = root / "Mods .zip terminados" / archive_name
    try:
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None: issues.append("zip_crc")
    except Exception as exc: issues.append(f"zip:{exc}")
    return {"song": song, "round": round_no, "files": len(files), "issues": issues, "status": "PASS" if not issues else "ERROR"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]; rounds = []
    for round_no in range(1, 21):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor: rows = list(executor.map(lambda song: one(root, song, round_no), SONGS))
        status = "PASS" if all(row["status"] == "PASS" for row in rows) else "ERROR"; rounds.append({"round": round_no, "status": status, "mods": rows}); print(json.dumps({"round": round_no, "status": status, "files": sum(row["files"] for row in rows)}, ensure_ascii=False), flush=True)
    complete = root / "Mods .zip terminados" / "Esperon-Completo.zip"
    complete_status = "PASS"
    try:
        with zipfile.ZipFile(complete) as package:
            if package.testzip() is not None: complete_status = "ERROR"
    except Exception: complete_status = "ERROR"
    payload = {"scope": "QA_20X21_V266", "status": "PASS" if all(item["status"] == "PASS" for item in rounds) and complete_status == "PASS" else "ERRORS_FOUND", "version": "2.6.6", "rounds": 20, "mods_per_round": 21, "total_reviews": 420, "parallel_workers": 8, "complete_zip_crc": complete_status, "rows": rounds}
    output = root / "qa-lab" / "rebuild-v266" / "playstate-fix" / "qa-20x21-v266.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps({"status": payload["status"], "rounds": 20, "total_reviews": 420, "complete_zip_crc": complete_status, "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
