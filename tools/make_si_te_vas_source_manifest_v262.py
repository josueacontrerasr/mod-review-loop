#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); args = parser.parse_args()
    root = args.root.resolve()
    source = root / "Esperón  Si Te Vas.m4a"
    mod = root / "mods/esperon-dano-si-te-vas"
    files = {
        "source_m4a": source,
        "demucs_vocals_wav": Path("/tmp/si-te-vas-demucs/htdemucs/Esperón  Si Te Vas/vocals.wav"),
        "demucs_instrumental_wav": Path("/tmp/si-te-vas-demucs/htdemucs/Esperón  Si Te Vas/no_vocals.wav"),
        "freeplay_cover_png": mod / "images/freeplay/albumRoll/esperon-si-te-vas-art.png",
        "runtime_inst_ogg": mod / "songs/si-te-vas/Inst.ogg",
        "runtime_voice_ogg": mod / "songs/si-te-vas/Voices-esperon-si-te-vas.ogg",
    }
    rows = {}
    for name, path in files.items():
        item = {"path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path), "exists": path.is_file()}
        if path.is_file(): item["sha256"] = sha(path)
        rows[name] = item
    payload = {"scope": "SI_TE_VAS_SOURCE_MANIFEST_V262", "executed_at": datetime.now(timezone.utc).isoformat(), "song": "si-te-vas", "artist": "Esperón", "source_probe": probe(source), "files": rows, "separation": {"engine": "Demucs htdemucs --two-stems=vocals --device cpu", "chart_generation_source": "runtime_voice_ogg_only", "instrumental_used_for_generation": False}}
    output = root / "qa-lab/rebuild-v262/playstate-fix/si-te-vas-source-manifest-v262.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "source_duration": payload["source_probe"].get("format", {}).get("duration")}, ensure_ascii=False))

if __name__ == "__main__": main()
