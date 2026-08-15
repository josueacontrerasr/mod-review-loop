from __future__ import annotations

import concurrent.futures
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
EVIDENCE = ROOT / "qa-lab" / "rebuild-v230"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def process(song: str) -> dict:
    mod = ROOT / "mods" / f"esperon-dano-{song}"
    data_dir = mod / "data" / "songs"
    song_dir = next(data_dir.iterdir())
    production = song_dir / f"{song}-chart.json"
    candidate = EVIDENCE / "candidate-charts" / song / f"{song}-chart-v230.json"
    backup = EVIDENCE / "production-charts-before" / song / f"{song}-chart-v222.json"
    if not production.is_file() or not candidate.is_file():
        raise FileNotFoundError(f"Missing production/candidate chart for {song}")
    before = json.loads(production.read_text(encoding="utf-8"))
    after = json.loads(candidate.read_text(encoding="utf-8"))
    for difficulty in ("easy", "normal", "hard"):
        if not after.get("notes", {}).get(difficulty):
            raise ValueError(f"Empty difficulty {difficulty} for {song}")
    if before.get("timeChanges") != after.get("timeChanges"):
        raise ValueError(f"timeChanges changed for {song}")
    if before.get("generatedBy") == after.get("generatedBy") and before.get("notes") == after.get("notes"):
        raise ValueError(f"No chart change detected for {song}")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(production, backup)
    production.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audio_dir = mod / "songs" / song
    inst = audio_dir / "Inst.ogg"
    voices = sorted(audio_dir.glob("Voices-*.ogg"))
    return {
        "song": song,
        "production_chart": str(production.relative_to(ROOT)),
        "candidate_chart": str(candidate.relative_to(ROOT)),
        "backup_chart": str(backup.relative_to(ROOT)),
        "before_sha256": sha256(backup),
        "after_sha256": sha256(production),
        "inst_sha256": sha256(inst),
        "voices_sha256": {v.name: sha256(v) for v in voices},
        "notes": {d: len(after["notes"][d]) for d in ("easy", "normal", "hard")},
        "scroll_speed": after.get("scrollSpeed"),
        "time_changes_preserved": before.get("timeChanges") == after.get("timeChanges"),
        "audio_not_touched": True,
    }


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        rows = list(executor.map(process, SONGS))
    rows.sort(key=lambda row: row["song"])
    payload = {"status": "PASS", "version": "2.3.0", "songs": len(rows), "rows": rows, "policy": "Only V2.3.0 candidate charts were promoted; audio files and timeChanges were not modified."}
    (EVIDENCE / "chart-promotion-v230.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "songs": len(rows), "output": str(EVIDENCE / "chart-promotion-v230.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
