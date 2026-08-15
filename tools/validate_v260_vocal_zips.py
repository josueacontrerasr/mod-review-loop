#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "2.6.0"

def inspect(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = {name.rstrip("/") for name in archive.namelist() if name and not name.startswith("__MACOSX/")}
        roots = sorted({name.split("/", 1)[0] for name in names})
        if len(roots) != 1:
            return {"package": path.name, "status": "ERROR", "errors": [f"roots={roots}"]}
        root = roots[0]
        relative = {name.removeprefix(root + "/") for name in names if name.startswith(root + "/")}
        if "_polymod_meta.json" not in relative: errors.append("manifest_missing")
        else:
            manifest = json.loads(archive.read(f"{root}/_polymod_meta.json").decode("utf-8"))
            if manifest.get("api_version") != "0.8.6": errors.append("api_version")
            if manifest.get("mod_version") != VERSION: errors.append("mod_version")
        if any(token in name for name in relative for token in ("qa-lab/", "sync-candidates/", "artifacts/", "logs/")): errors.append("lab_files")
        charts = [name for name in relative if name.startswith("data/songs/") and name.endswith("-chart.json")]
        metadata = [name for name in relative if name.startswith("data/songs/") and name.endswith("-metadata.json")]
        if len(charts) != 1 or len(metadata) != 1: errors.append(f"song_data={len(charts)},{len(metadata)}")
        if charts:
            chart = json.loads(archive.read(f"{root}/{charts[0]}").decode("utf-8"))
            if chart.get("version") != "2.0.0": errors.append("chart_version")
            if set(chart.get("notes", {})) != {"easy", "normal", "hard"}: errors.append("difficulty_set")
            for difficulty, notes in chart.get("notes", {}).items():
                keys = [(float(note.get("t", -1)), int(note.get("d", -1))) for note in notes]
                if keys != sorted(keys) or len(keys) != len(set(keys)): errors.append(f"chart_{difficulty}_order")
                if any(timestamp < 0 or lane not in (0, 1, 2, 3) for timestamp, lane in keys): errors.append(f"chart_{difficulty}_lanes")
        scripts = [name for name in relative if name.startswith("scripts/") and name.endswith((".hxc", ".hx"))]
        if not scripts: errors.append("hscript_missing")
        for script in scripts:
            text = archive.read(f"{root}/{script}").decode("utf-8-sig", errors="replace")
            if not re.search(r"import\s+funkin\.modding\.module\.Module", text) or not re.search(r"extends\s+Module", text): errors.append(f"hscript_module={script}")
        audio = [name for name in relative if name.startswith("songs/") and name.endswith(".ogg")]
        if not any(name.endswith("/Inst.ogg") for name in audio): errors.append("inst_missing")
        if not any("Voices-" in name for name in audio): errors.append("voices_missing")
        for required in ("data", "images", "shared", "songs"):
            if not any(name.startswith(required + "/") for name in relative): errors.append(f"dir_missing={required}")
    return {"package": path.name, "status": "PASS" if not errors else "ERROR", "errors": errors, "entries": len(relative), "charts": charts, "audio_files": audio, "scripts": scripts}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    delivery = root / "Mods .zip terminados"
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if "Coleccion" not in path.name)
    rows = [inspect(path) for path in packages]
    collection = delivery / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    collection_members: list[str] = []
    collection_error = None
    if not collection.is_file(): collection_error = "collection_missing"
    else:
        with zipfile.ZipFile(collection) as archive:
            collection_members = sorted(name for name in archive.namelist() if name.endswith(".zip"))
            if len(collection_members) != 20: collection_error = f"collection_members={len(collection_members)}"
    payload = {"scope": "VSLICE_086_VOCAL_ONLY_ZIP_GATE_V260", "executed_at": datetime.now(timezone.utc).isoformat(), "target_version": "0.8.6", "mod_version": VERSION, "packages": len(rows), "passed": sum(row["status"] == "PASS" for row in rows), "collection_members": len(collection_members), "collection_error": collection_error, "status": "PASS" if len(rows) == 20 and all(row["status"] == "PASS" for row in rows) and collection_error is None else "ERRORS_FOUND", "rows": rows, "instrumental_used_for_generation": False}
    output = root / "qa-lab" / "rebuild-v260" / "vocal-only" / "zip-gate-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packages": payload["packages"], "passed": payload["passed"], "collection_members": payload["collection_members"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
