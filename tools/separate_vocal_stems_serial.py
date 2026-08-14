#!/usr/bin/env python3
"""Separa stems vocales de forma serial con Demucs; no modifica audio ni mods."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path


def normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    for token in ("esperon", "letra", "audio"):
        text = text.replace(token, "")
    return "".join(char for char in text if char.isalnum())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,sample_rate,channels", "-of", "json", str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def source_for_song(root: Path, song: str) -> Path:
    target = normalized(song)
    candidates = []
    for source in root.glob("*.m4a"):
        key = normalized(source.stem)
        if key == target or target in key or key in target:
            candidates.append(source)
    if len(candidates) != 1:
        raise ValueError(f"{song}: no se obtuvo una fuente M4A única: {[item.name for item in candidates]}")
    return candidates[0]


def process_song(root: Path, song: str, segment: float, overlap: float, force: bool) -> dict:
    source = source_for_song(root, song)
    output = root / "sync-candidates" / "vocal-stems" / song
    vocals = output / "vocals.wav"
    evidence = output / "stem-evidence.json"
    if vocals.is_file() and evidence.is_file() and not force:
        return {"song": song, "status": "EXISTING", "vocals": str(vocals.relative_to(root))}
    workspace = output / "demucs-work"
    workspace.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "demucs.separate", "--two-stems=vocals", "-n", "htdemucs", "-d", "cpu",
        "--segment", str(int(segment)), "--overlap", str(overlap), "-o", str(workspace), str(source)
    ]
    log = output / "demucs.log"
    with log.open("w", encoding="utf-8") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, text=True)
    if result.returncode:
        raise RuntimeError(f"{song}: Demucs falló; revisar {log}")
    generated = list(workspace.glob("htdemucs/*/vocals.wav"))
    if len(generated) != 1:
        raise RuntimeError(f"{song}: no se generó un vocal stem único")
    shutil.copy2(generated[0], vocals)
    payload = {
        "scope": "VOCAL_STEM_EVIDENCE_ONLY",
        "song": song,
        "method": {"tool": "Demucs", "model": "htdemucs", "device": "cpu", "segment_seconds": segment, "overlap": overlap, "concurrency": 1},
        "source_m4a": {"path": source.relative_to(root).as_posix(), "sha256": sha256(source), "probe": probe(source)},
        "vocal_stem": {"path": vocals.relative_to(root).as_posix(), "sha256": sha256(vocals), "probe": probe(vocals)},
        "status": "SEPARATED_REQUIRES_HUMAN_QUALITY_REVIEW",
        "limitations": ["La separación puede contener sangrado instrumental, coros o artefactos.", "El stem no identifica por sí solo personaje/strumline ni aprueba sincronía."]
    }
    evidence.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"song": song, "status": "SEPARATED", "vocals": str(vocals.relative_to(root))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--song", action="append", default=[])
    parser.add_argument("--segment", type=float, default=7.0)
    parser.add_argument("--overlap", type=float, default=0.1)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    songs = args.song or sorted(path.name for mod in (root / "mods").glob("esperon-dano-*") for path in (mod / "data" / "songs").iterdir() if path.is_dir())
    results = []
    for song in songs:
        results.append(process_song(root, song, args.segment, args.overlap, args.force))
        print(json.dumps(results[-1], ensure_ascii=False), flush=True)
    print(json.dumps({"songs": len(results), "results": results}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
