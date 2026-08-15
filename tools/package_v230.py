from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.3.0"
SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def name_for(song: str) -> str:
    display = "-".join(part[:1].upper() + part[1:] for part in song.split("-") if part)
    return f"Mod-{display}-V{VERSION}.zip"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    sync = json.loads((ROOT / "qa-lab" / "rebuild-v230" / "sync-pipeline-v230.json").read_text(encoding="utf-8"))
    visuals = json.loads((ROOT / "qa-lab" / "rebuild-v230" / "visual-redesign-v230.json").read_text(encoding="utf-8"))
    promotion = json.loads((ROOT / "qa-lab" / "rebuild-v230" / "chart-promotion-v230.json").read_text(encoding="utf-8"))
    if sync.get("status") != "PASS" or sync.get("songs") != 20 or sync.get("difficulties") != 60:
        raise RuntimeError("V2.3.0 sync pipeline is not PASS for 20 songs and 60 difficulties")
    if visuals.get("status") != "PASS" or visuals.get("songs") != 20:
        raise RuntimeError("V2.3.0 visual regeneration is not PASS for 20 songs")
    if promotion.get("status") != "PASS" or promotion.get("songs") != 20:
        raise RuntimeError("V2.3.0 chart promotion is not PASS for 20 songs")
    delivery = ROOT / "Mods .zip terminados"
    delivery.mkdir(parents=True, exist_ok=True)
    for old in delivery.glob("*.zip"):
        old.unlink()
    packages = []
    for song in SONGS:
        mod = ROOT / "mods" / f"esperon-dano-{song}"
        manifest_path = mod / "_polymod_meta.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.update({"api_version": "0.8.6", "mod_version": VERSION, "description": f"Mod V-Slice Mobile 0.8.6 de {song}; chart vocalmente alineado por VAD/onsets multimétodo, easy/normal/hard, y visuales V2.3.0."})
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        destination = delivery / name_for(song)
        shutil.make_archive(str(destination.with_suffix("")), "zip", root_dir=mod.parent, base_dir=mod.name)
        packages.append({"song": song, "mod": mod.name, "zip": str(destination.relative_to(ROOT)), "sha256": sha256(destination), "bytes": destination.stat().st_size, "version": VERSION, "clean_runtime_root": True, "sync_status": "MULTIMETHOD_PASS_REQUIRES_NATIVE_AUDIO_SYNC_TEST"})
    manifest = {"version": VERSION, "status": "PASS", "songs": len(packages), "packages": packages, "runtime_tree_policy": "Each ZIP contains only the mod root; QA reports, text evidence and collection ZIP remain outside individual runtime ZIPs.", "sync_policy": sync["method"], "limitations": ["The multimethod audio analysis is a static evidence gate; native Chart Editor Audio Sync Test and mobile playtest remain required for final device certification."]}
    write_json(ROOT / "qa-lab" / "rebuild-v230" / "package-manifest-v230.json", manifest)
    print(json.dumps({"status": manifest["status"], "packages": len(packages), "delivery": str(delivery)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
