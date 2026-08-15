#!/usr/bin/env python3
"""Auditor actualizado de ZIPs V2.5.1 para FNF Mobile V-Slice 0.8.6."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "2.5.1"


def inspect_zip(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = sorted(name.rstrip("/") for name in archive.namelist() if name and not name.startswith("__MACOSX/"))
            roots = sorted({name.split("/", 1)[0] for name in names if "/" in name or name})
            if len(roots) != 1:
                errors.append(f"root_count={len(roots)}")
                root = roots[0] if roots else ""
            else:
                root = roots[0]
            relative = [name.removeprefix(root + "/") for name in names if name.startswith(root + "/")]
            forbidden_fragments = ("qa-lab/", "artifacts/", "logs/", "sync-candidates/", ".git/", "node_modules/")
            forbidden = [name for name in relative if any(fragment in name for fragment in forbidden_fragments)]
            if forbidden:
                errors.append(f"forbidden_work_files={len(forbidden)}")
            top_txt = [name for name in relative if "/" not in name and name.lower().endswith((".txt", ".md", ".jsonl")) and name != "_polymod_meta.json"]
            if top_txt:
                warnings.append(f"top_level_docs={len(top_txt)}")
            meta_path = f"{root}/_polymod_meta.json"
            if meta_path not in names:
                errors.append("root_polymod_manifest_missing")
                manifest = {}
            else:
                manifest = json.loads(archive.read(meta_path).decode("utf-8"))
                if manifest.get("api_version") != "0.8.6":
                    errors.append(f"api_version={manifest.get('api_version')}")
                if manifest.get("mod_version") != VERSION:
                    errors.append(f"mod_version={manifest.get('mod_version')}")
            scripts = [name for name in relative if name.startswith("scripts/") and name.endswith((".hxc", ".hx"))]
            script_reports = []
            if not scripts:
                errors.append("hscript_missing")
            for script in scripts:
                text = archive.read(f"{root}/{script}").decode("utf-8-sig", errors="replace")
                import_ok = bool(re.search(r"import\s+funkin\.modding\.module\.Module", text))
                extends_ok = bool(re.search(r"extends\s+Module", text))
                script_reports.append({"path": script, "import_module_ok": import_ok, "extends_module_ok": extends_ok, "bytes": len(text.encode("utf-8"))})
                if not import_ok or not extends_ok:
                    errors.append(f"hscript_module_contract={script}")
            charts = [name for name in relative if name.startswith("data/songs/") and name.endswith("-chart.json")]
            metadata = [name for name in relative if name.startswith("data/songs/") and name.endswith("-metadata.json")]
            song_manifests = [name for name in relative if name.startswith("data/songs/") and name.endswith("/manifest.json")]
            if len(charts) != 1 or len(metadata) != 1 or len(song_manifests) != 1:
                errors.append(f"song_data_counts={len(charts)},{len(metadata)},{len(song_manifests)}")
            for name in charts:
                payload = json.loads(archive.read(f"{root}/{name}").decode("utf-8"))
                if payload.get("version") != "2.0.0":
                    errors.append(f"chart_version={name}")
            audio = [name for name in relative if name.startswith("songs/") and name.lower().endswith(".ogg")]
            if not any(name.endswith("/Inst.ogg") for name in audio):
                errors.append("inst_missing")
            if not any("Voices-" in name for name in audio):
                errors.append("voices_missing")
            root_dirs = sorted({name.split("/", 1)[0] for name in relative if "/" in name})
            required = {"data", "images", "shared", "songs"}
            missing_dirs = sorted(required - set(root_dirs))
            if missing_dirs:
                errors.append(f"missing_runtime_dirs={','.join(missing_dirs)}")
            return {
                "package": path.name,
                "status": "PASS" if not errors else "ERROR",
                "errors": errors,
                "warnings": warnings,
                "root": root,
                "entries": len(relative),
                "scripts": script_reports,
                "charts": charts,
                "metadata": metadata,
                "song_manifests": song_manifests,
                "audio_files": audio,
                "manifest": {key: manifest.get(key) for key in ("id", "title", "api_version", "mod_version")},
            }
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"package": path.name, "status": "ERROR", "errors": [f"zip_read={exc}"], "warnings": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    root = args.root.resolve()
    delivery = root / "Mods .zip terminados"
    packages = sorted(path for path in delivery.glob(f"Mod-*-V{VERSION}.zip") if "Coleccion" not in path.name)
    collection = delivery / f"Mod-Esperon-Coleccion-V{VERSION}.zip"
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = list(executor.map(inspect_zip, packages))
    rows.sort(key=lambda row: row["package"])
    collection_report: dict[str, Any] = {"exists": collection.is_file(), "members": [], "status": "PASS"}
    if not collection.is_file():
        collection_report.update({"status": "ERROR", "error": "collection_missing"})
    else:
        try:
            with zipfile.ZipFile(collection) as archive:
                collection_report["members"] = sorted(name for name in archive.namelist() if name.endswith(".zip"))
                if len(collection_report["members"]) != 20:
                    collection_report.update({"status": "ERROR", "error": f"collection_members={len(collection_report['members'])}"})
        except (OSError, zipfile.BadZipFile) as exc:
            collection_report.update({"status": "ERROR", "error": str(exc)})
    payload = {
        "scope": "FULL_ZIP_HSCRIPT_AUDIT_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "mod_version": VERSION,
        "packages": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "collection": collection_report,
        "status": "PASS" if len(rows) == 20 and all(row["status"] == "PASS" for row in rows) and collection_report["status"] == "PASS" else "ERRORS_FOUND",
        "rows": rows,
        "limitations": ["La inspección ZIP/HScript no sustituye parser ni ejecución nativa del motor."],
    }
    output = root / "qa-lab" / "rebuild-v260" / "full-zip-hscript-audit-v260.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"packages": payload["packages"], "passed": payload["passed"], "collection_status": collection_report["status"], "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
