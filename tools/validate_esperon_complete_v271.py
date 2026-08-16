#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
BAD_SUFFIXES = {".txt", ".md", ".log", ".csv", ".html", ".bak"}


def inspect(path: Path, expected_roots: int | None = 1) -> dict[str, Any]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        roots = sorted({PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts})
        bad = [name for name in names if PurePosixPath(name).suffix.lower() in BAD_SUFFIXES]
        if expected_roots is not None and len(roots) != expected_roots: errors.append(f"root_count:{len(roots)}")
        if bad: errors.append(f"prohibited_files:{bad[:5]}")
        for root in roots:
            polymod = f"{root}/_polymod_meta.json"
            if polymod not in names: errors.append(f"polymod_missing:{root}")
            else:
                meta = json.loads(archive.read(polymod))
                if meta.get("api_version") != "0.8.6": errors.append(f"api_version:{root}:{meta.get('api_version')}")
                if meta.get('mod_version') != "2.7.1": errors.append(f"mod_version:{root}:{meta.get('mod_version')}")
            song = root.removeprefix("esperon-dano-")
            chart = f"{root}/data/songs/{song}/{song}-chart.json"
            metadata = f"{root}/data/songs/{song}/{song}-metadata.json"
            manifest = f"{root}/data/songs/{song}/manifest.json"
            for required in (chart, metadata, manifest):
                if required not in names: errors.append(f"required_missing:{required}")
            if chart in names:
                data = json.loads(archive.read(chart))
                if data.get("generatedBy") != "Friday Night Funkin' - 0.8.6; V2.7.1 density-aware vocal clusters, retimed holds and player lanes d=0..3": errors.append(f"generatedBy:{root}")
                if set(data.get("notes", {}).keys()) != {"easy", "normal", "hard"}: errors.append(f"difficulties:{root}")
                if any(note.get("d", -1) not in (0, 1, 2, 3) for notes in data.get("notes", {}).values() for note in notes): errors.append(f"lanes:{root}")
            voice = [name for name in names if name.startswith(f"{root}/songs/{song}/Voices-") and name.endswith(".ogg")]
            inst = f"{root}/songs/{song}/Inst.ogg"
            if len(voice) != 1: errors.append(f"voice_count:{root}:{len(voice)}")
            if inst not in names: errors.append(f"inst_missing:{root}")
        return {"zip": path.name, "status": "PASS" if not errors else "ERRORS_FOUND", "file_count": len(names), "roots": roots, "prohibited_count": len(bad), "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("root", type=Path, nargs="?", default=Path(".")); parser.add_argument("--workers", type=int, default=8); args = parser.parse_args()
    root = args.root.resolve(); delivery = root / "Mods .zip terminados"
    zips = sorted(delivery.glob("*.zip"))
    expected = {"Esperon-Completo.zip"} | {f"Mod-{'-'.join(word.capitalize() for word in song.split('-'))}-V2.7.1.zip" for song in SONGS}
    errors: list[str] = []
    actual = {path.name for path in zips}
    if actual != expected: errors.append(f"delivery_names:missing={sorted(expected-actual)},extra={sorted(actual-expected)}")
    individual_paths = [path for path in zips if path.name != "Esperon-Completo.zip"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool: individual = list(pool.map(lambda path: inspect(path, 1), individual_paths))
    complete = inspect(delivery / "Esperon-Completo.zip", 21) if (delivery / "Esperon-Completo.zip").is_file() else {"status": "ERRORS_FOUND", "errors": ["complete_missing"]}
    if complete.get("status") != "PASS": errors.extend(complete.get("errors", []))
    payload = {"scope": "ESPERON_COMPLETE_ZIP_GATE_V271", "executed_at": datetime.now(timezone.utc).isoformat(), "mod_version": "2.7.1", "individual_zips": len(individual), "individual_passed": sum(row["status"] == "PASS" for row in individual), "complete": complete, "delivery_zip_count": len(zips), "status": "PASS" if not errors and len(individual) == 21 and all(row["status"] == "PASS" for row in individual) else "ERRORS_FOUND", "errors": errors, "individual": sorted(individual, key=lambda row: row["zip"])}
    output = root / "qa-lab" / "rebuild-v271" / "playstate-fix" / "zip-gate-v271.json"; output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"individual_zips": payload["individual_zips"], "individual_passed": payload["individual_passed"], "delivery_zip_count": payload["delivery_zip_count"], "complete_status": complete.get("status"), "status": payload["status"], "output": str(output)}, ensure_ascii=False)); return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
