#!/usr/bin/env python3
"""Stage the Esperon mods in the official FNF Android mods location.

This tool does not execute an APK. It prepares the exact Android path documented
by FNF v0.8.6 and can optionally push the staged directories to a connected
emulator through adb.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SONGS = [
    "arcoloria", "cortamos-y-volvemos", "dano", "dias-magicos", "eclipsis", "fango", "luma",
    "maraton-de-peliculas", "me-voy-a-morir-si-no-me-besas-ahora-mismo", "meteora", "mi-hogar",
    "nubia", "nuestro-amor-no-es-normal", "peligrosa", "rompecabezas", "solare", "tristella",
    "tu-dealer-de-nostalgia", "un-poco-bien-un-poco-mal", "volver-a-vernos", "si-te-vas",
]
PACKAGE_NAME = "me.funkin.fnf"
OFFICIAL_RELATIVE_PATH = Path("Android") / "obb" / PACKAGE_NAME / "mods"


def copy_one(source: Path, destination: Path) -> dict[str, Any]:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    manifest = destination / "_polymod_meta.json"
    song_dirs = sorted((destination / "data" / "songs").glob("*"))
    return {
        "mod": source.name,
        "source": str(source),
        "destination": str(destination),
        "manifest_at_root": manifest.is_file(),
        "song_directories": [path.name for path in song_dirs if path.is_dir()],
        "status": "PASS" if manifest.is_file() and len(song_dirs) == 1 else "ERROR",
    }


def adb_run(serial: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["adb", "-s", serial, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def push_one(serial: str, staged: Path, remote_root: str) -> dict[str, Any]:
    result = adb_run(serial, "push", str(staged), f"{remote_root}/", timeout=300)
    return {
        "mod": staged.name,
        "remote": f"{remote_root}/{staged.name}",
        "returncode": result.returncode,
        "stdout": result.stdout.strip()[-1000:],
        "stderr": result.stderr.strip()[-1000:],
        "status": "PASS" if result.returncode == 0 else "ERROR",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--source-root", type=Path, default=None, help="Override the repository mods directory")
    parser.add_argument("--destination", type=Path, default=None, help="Override the simulated emulated/0 destination")
    parser.add_argument("--adb-serial", default=None, help="Optional emulator/device serial from adb devices")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    root = args.root.resolve()
    source_root = (args.source_root or root / "mods").resolve()
    destination = (args.destination or root / "qa-lab" / "mobile-sim" / "storage" / "emulated" / "0" / OFFICIAL_RELATIVE_PATH).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[Path, Path]] = []
    missing: list[str] = []
    for song in SONGS:
        source = source_root / f"esperon-dano-{song}"
        if not source.is_dir():
            missing.append(str(source))
            continue
        jobs.append((source, destination / source.name))

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        rows = list(executor.map(lambda pair: copy_one(*pair), jobs))
    rows.sort(key=lambda row: row["mod"])

    push_rows: list[dict[str, Any]] = []
    adb_status = "NOT_REQUESTED"
    remote_root = f"/sdcard/{OFFICIAL_RELATIVE_PATH.as_posix()}"
    if args.adb_serial:
        mkdir = adb_run(args.adb_serial, "shell", "mkdir", "-p", remote_root)
        if mkdir.returncode != 0:
            adb_status = "ERROR"
            push_rows.append({"status": "ERROR", "step": "mkdir", "stderr": mkdir.stderr.strip()[-1000:]})
        else:
            adb_status = "PASS"
            staged_dirs = [destination / f"esperon-dano-{song}" for song in SONGS]
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
                push_rows = list(executor.map(lambda path: push_one(args.adb_serial, path, remote_root), staged_dirs))
            if any(row.get("status") != "PASS" for row in push_rows):
                adb_status = "ERROR"

    payload = {
        "scope": "OFFICIAL_ANDROID_MOD_STAGE_V272",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "target_version": "0.8.6",
        "package_name": PACKAGE_NAME,
        "official_android_path": f"/sdcard/{OFFICIAL_RELATIVE_PATH.as_posix()}",
        "simulated_root": str(destination.relative_to(root)),
        "source_root": str(source_root.relative_to(root)) if source_root.is_relative_to(root) else str(source_root),
        "mods_expected": len(SONGS),
        "mods_staged": len(rows),
        "missing_sources": missing,
        "manifest_root_passed": sum(row["manifest_at_root"] for row in rows),
        "adb_serial": args.adb_serial,
        "adb_status": adb_status,
        "adb_push": push_rows,
        "status": "PASS" if len(rows) == len(SONGS) and not missing and all(row["status"] == "PASS" for row in rows) and adb_status != "ERROR" else "ERRORS_FOUND",
        "rows": rows,
    }
    output = root / "qa-lab" / "rebuild-v272" / "official-android-stage-v272.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mods_staged": payload["mods_staged"], "adb_status": adb_status, "status": payload["status"], "output": str(output)}, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
