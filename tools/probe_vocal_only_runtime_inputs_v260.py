#!/usr/bin/env python3
"""Prueba dinámica: el generador vocal-only solo puede cargar Voices-*.ogg."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    path = root / "tools" / "build_vocal_only_candidates_v260.py"
    spec = importlib.util.spec_from_file_location("vocal_only_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("generator_import_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    loaded: list[str] = []
    original_load = module.librosa.load

    def wrapped_load(audio_path, *args, **kwargs):
        loaded.append(str(audio_path))
        return original_load(audio_path, *args, **kwargs)

    module.librosa.load = wrapped_load
    rows = [module.analyze_one(root, song) for song in SONGS]
    forbidden = sorted(path for path in loaded if Path(path).name == "Inst.ogg" or "instrumental" in Path(path).name.lower())
    vocal_inputs = sorted(set(path for path in loaded if "Voices-" in Path(path).name))
    payload = {
        "scope": "VOCAL_ONLY_DYNAMIC_INPUT_PROBE_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "songs": len(rows),
        "songs_passed": sum(row.get("status") == "PASS" for row in rows),
        "load_calls": len(loaded),
        "vocal_inputs": vocal_inputs,
        "forbidden_instrumental_inputs": forbidden,
        "status": "PASS" if len(rows) == 20 and all(row.get("status") == "PASS" for row in rows) and not forbidden else "ERRORS_FOUND",
        "policy": "El generador vocal-only no puede abrir Inst.ogg durante la creación de candidatos.",
    }
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "dynamic-input-probe-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "songs_passed": payload["songs_passed"], "load_calls": payload["load_calls"], "forbidden_instrumental_inputs": payload["forbidden_instrumental_inputs"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
