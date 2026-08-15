#!/usr/bin/env python3
"""Promueve charts vocal-only aprobados a los 20 mods como V2.6.0."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos",
]
VERSION = "2.6.0"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    vocal_root = root / "qa-lab" / "rebuild-v260" / "vocal-only"
    gates = [
        (vocal_root / "source-inventory-v260.json", "PASS"),
        (vocal_root / "candidate-summary-v260.json", "PASS_CANDIDATES_ISOLATED"),
        (vocal_root / "provenance-gate-v260.json", "PASS"),
        (vocal_root / "independent-vad-gate-v260.json", "PASS"),
        (vocal_root / "staging-manifest-v260.json", "PASS"),
    ]
    for path, expected in gates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != expected:
            raise SystemExit(f"gate bloqueado: {path} status={payload.get('status')} expected={expected}")
    rows: list[dict[str, Any]] = []
    for song in SONGS:
        mod = root / "mods" / f"esperon-dano-{song}"
        chart_path = mod / "data" / "songs" / song / f"{song}-chart.json"
        staged_chart_path = vocal_root / "staged-mods" / "mods" / f"esperon-dano-{song}" / "data" / "songs" / song / f"{song}-chart.json"
        manifest_path = mod / "_polymod_meta.json"
        old_chart_sha = sha(chart_path)
        old_manifest_sha = sha(manifest_path)
        staged_chart = json.loads(staged_chart_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["mod_version"] = VERSION
        description = str(manifest.get("description", ""))
        description = description.replace("V2.5.1 voice-first charts; official player lanes 0-3", "V2.6.0 vocal-only charts; no instrumental note generation")
        description = description.replace("V2.5.1 voice-priority charts; official player lanes 0-3", "V2.6.0 vocal-only charts; no instrumental note generation")
        if "V2.6.0 vocal-only charts" not in description:
            description = f"{description} — V2.6.0 vocal-only charts; no instrumental note generation".strip(" —")
        manifest["description"] = description
        chart_path.write_text(json.dumps(staged_chart, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        candidate = json.loads((vocal_root / song / "candidate-report.json").read_text(encoding="utf-8"))
        rows.append({
            "song": song,
            "chart_sha256_before": old_chart_sha,
            "chart_sha256_after": sha(chart_path),
            "manifest_sha256_before": old_manifest_sha,
            "manifest_sha256_after": sha(manifest_path),
            "source_vocal_sha256": candidate.get("source_vocal_sha256"),
            "notes": {difficulty: len(staged_chart.get("notes", {}).get(difficulty, [])) for difficulty in ("easy", "normal", "hard")},
            "instrumental_used_for_generation": False,
            "version": VERSION,
        })
    payload = {
        "scope": "VOCAL_ONLY_PROMOTION_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "mod_version": VERSION,
        "songs": len(rows),
        "promoted": len(rows),
        "status": "PASS",
        "production_modified": True,
        "instrumental_used_for_generation": False,
        "rows": rows,
        "policy": "Solo charts y manifests versionados fueron modificados; audio y assets permanecen intactos.",
    }
    output = vocal_root / "promotion-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"songs": payload["songs"], "promoted": payload["promoted"], "mod_version": VERSION, "status": payload["status"], "instrumental_used_for_generation": payload["instrumental_used_for_generation"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
