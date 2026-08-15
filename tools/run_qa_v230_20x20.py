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
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def one(root: Path, song: str, round_no: int) -> dict:
    mod = root / "mods" / f"esperon-dano-{song}"
    issues = []
    files = [path for path in mod.rglob("*") if path.is_file()]
    for path in files:
        try:
            if path.suffix.lower() == ".json": json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".xml": ET.parse(path)
            elif path.suffix.lower() in (".png", ".jpg", ".jpeg"):
                with Image.open(path) as image: image.verify()
            elif path.suffix.lower() == ".ogg" and path.read_bytes()[:4] != b"OggS":
                issues.append(f"bad_ogg_header:{path.relative_to(mod)}")
        except Exception as exc:
            issues.append(f"parse:{path.relative_to(mod)}:{exc}")
    try:
        song_dir = next((mod / "data" / "songs").iterdir())
        meta = json.loads((song_dir / f"{song}-metadata.json").read_text(encoding="utf-8"))
        chart = json.loads((song_dir / f"{song}-chart.json").read_text(encoding="utf-8"))
        stage = json.loads((mod / "data" / "stages" / f"{meta['playData']['stage']}.json").read_text(encoding="utf-8"))
        if stage.get("directory") != "shared" or set(stage.get("characters", {})) != {"bf", "dad", "gf"}:
            issues.append("stage_contract")
        if set(chart.get("notes", {})) != {"easy", "normal", "hard"}: issues.append("difficulty_set")
        for difficulty, notes in chart.get("notes", {}).items():
            keys = [(float(note.get("t", -1)), int(note.get("d", -1))) for note in notes]
            if keys != sorted(keys) or len(keys) != len(set(keys)): issues.append(f"chart_{difficulty}_order_or_duplicate")
        if not (chart.get("scrollSpeed", {}).get("easy", 0) < chart.get("scrollSpeed", {}).get("normal", 0) < chart.get("scrollSpeed", {}).get("hard", 0)): issues.append("scroll_speed")
        for role in ("player", "opponent"):
            cid = meta["playData"]["characters"][role]
            character = json.loads((mod / "data" / "characters" / f"{cid}.json").read_text(encoding="utf-8"))
            asset = character["assetPath"]
            base = mod / "shared" / "images" / asset.removeprefix("shared:")
            if asset.startswith("shared:") or not base.with_suffix(".png").is_file() or not base.with_suffix(".xml").is_file(): issues.append(f"character_{role}_asset")
        if not (mod / "songs" / song / "Inst.ogg").is_file() or not list((mod / "songs" / song).glob("Voices-*.ogg")): issues.append("audio")
    except Exception as exc:
        issues.append(f"contract:{exc}")
    for archive in (root / "Mods .zip terminados").glob("Mod-*-V2.3.0.zip"):
        if song.replace("-", "").lower() in archive.name.replace("-", "").lower():
            try:
                with zipfile.ZipFile(archive) as package:
                    if package.testzip() is not None: issues.append("zip_crc")
            except Exception as exc:
                issues.append(f"zip:{exc}")
            break
    return {"song": song, "round": round_no, "files": len(files), "issues": issues, "status": "PASS" if not issues else "ERROR"}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    rounds = []
    for round_no in range(1, 21):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            rows = list(executor.map(lambda song: one(root, song, round_no), SONGS))
        status = "PASS" if all(row["status"] == "PASS" for row in rows) else "ERROR"
        rounds.append({"round": round_no, "status": status, "mods": rows})
        print(json.dumps({"round": round_no, "status": status, "files": sum(row["files"] for row in rows)}, ensure_ascii=False), flush=True)
    payload = {"status": "PASS" if all(item["status"] == "PASS" for item in rounds) else "ERRORS_FOUND", "version": "2.3.0", "rounds": 20, "mods_per_round": 20, "total_reviews": 400, "parallel_workers": 8, "rows": rounds, "scope": "Each round scans every source file and individual V2.3.0 ZIP CRC; collection is validated separately."}
    output = root / "qa-lab" / "rebuild-v230" / "qa-20x20-v230.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "rounds": 20, "total_reviews": 400, "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
