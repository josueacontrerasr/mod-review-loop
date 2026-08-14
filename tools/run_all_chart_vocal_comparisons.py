#!/usr/bin/env python3
"""Run chart-vocal comparisons for all 20 mods after stems are available."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis",
    "fango", "luma", "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo",
    "meteora", "mi-hogar", "nubia", "nuestro-amor-no-es-normal", "peligrosa",
    "rompecabezas", "solare", "tristella", "tu-dealer-de-nostalgia",
    "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def run_one(root: Path, song: str) -> dict:
    mod = next(root.glob(f"mods/esperon-dano-{song}"))
    stem = root / "sync-candidates/vocal-stems" / song / "vocals.wav"
    out = root / "sync-candidates/chart-vocal-comparisons" / f"{song}.json"
    command = [sys.executable, str(root / "tools/compare_chart_audio.py"), str(root), "--mod", str(mod), "--vocal-stem", str(stem), "--output", str(out)]
    result = subprocess.run(command, capture_output=True, text=True)
    return {"song": song, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "output": str(out)}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    timeout = float(os.environ.get("VOCAL_STEM_WAIT_SECONDS", "1800"))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        missing = [song for song in SONGS if not (root / "sync-candidates/vocal-stems" / song / "vocals.wav").is_file()]
        if not missing:
            break
        time.sleep(15)
    missing = [song for song in SONGS if not (root / "sync-candidates/vocal-stems" / song / "vocals.wav").is_file()]
    if missing:
        raise SystemExit(f"Faltan stems vocales después de esperar: {missing}")
    results = []
    workers = min(8, len(SONGS), os.cpu_count() or 2)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_one, root, song): song for song in SONGS}
        for future in as_completed(futures):
            result = future.result(); results.append(result); print(json.dumps(result, ensure_ascii=False), flush=True)
    results.sort(key=lambda item: item["song"])
    payload = {"status": "PASS" if all(item["returncode"] == 0 for item in results) else "ERRORS_FOUND", "songs": len(results), "results": results, "evidence_only": True}
    output = root / "qa-lab/rebuild-v221/chart-vocal-comparison-summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "songs": len(results), "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
