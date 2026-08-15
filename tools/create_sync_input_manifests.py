#!/usr/bin/env python3
"""Crea manifiestos de entrada para análisis de sincronía; no altera los mods."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path)
    ], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    output = root / "sync-candidates" / "input-manifests"
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for mod in sorted(path for path in (root / "mods").glob("esperon-dano-*") if path.is_dir()):
        songs = [path for path in (mod / "data" / "songs").iterdir() if path.is_dir()]
        if len(songs) != 1:
            raise ValueError(f"{mod.name}: se esperaba una canción")
        song = songs[0].name
        audio = mod / "songs" / song / "Inst.ogg"
        metadata = songs[0] / f"{song}-metadata.json"
        chart = songs[0] / f"{song}-chart.json"
        payload = {
            "scope": "SYNC_CANDIDATE_INPUT_MANIFEST",
            "song": song,
            "mod": mod.name,
            "target_funkin_api": "0.8.6",
            "final_audio": {
                "path": audio.relative_to(root).as_posix(),
                "sha256": sha256(audio),
                "probe": probe(audio)
            },
            "metadata": {"path": metadata.relative_to(root).as_posix(), "sha256": sha256(metadata)},
            "chart": {"path": chart.relative_to(root).as_posix(), "sha256": sha256(chart)},
            "vocal_source_status": "UNVERIFIED_NO_DISTRIBUTED_VOCALS_DECLARED",
            "promotion_rule": "NO_REPLACE_PRODUCTION_CHART_WITHOUT_REVIEWED_ANCHORS_AUDIO_SYNC_TEST_AND_MOBILE_PLAYTEST"
        }
        target = output / f"{song}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report.append({"song": song, "audio_sha256": payload["final_audio"]["sha256"]})
    summary = {"scope": "SYNC_CANDIDATE_INPUT_MANIFESTS", "songs": len(report), "entries": report}
    (root / "sync-candidates" / "input-manifests.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": len(report), "output": str(output.relative_to(root))}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
