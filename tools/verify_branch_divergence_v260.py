#!/usr/bin/env python3
"""Verifica la divergencia de ramas solicitada antes de cualquier promoción."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAIN_EXPECTED = "2cd67f950b40d05f9f5e157f5ebed7510bc2ed36"
STABLE_BRANCH = "auto/vocal-sync-recheck-v5"
LAB_BRANCH = "auto/fnf-vslice-lab-v260"
HUD_PATH = "mods/esperon-dano-solare/scripts/EsperonSolareHudV2.hxc"
REQUIRED_RUNTIME_DIRS = ["shared", "data", "images", "songs"]


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def remote_refs(root: Path) -> dict[str, str]:
    output = run("git", "-C", str(root), "ls-remote", "origin", "refs/heads/main", f"refs/heads/{STABLE_BRANCH}", f"refs/heads/{LAB_BRANCH}")
    refs: dict[str, str] = {}
    for line in output.splitlines():
        sha, ref = line.split("\t", 1)
        refs[ref.removeprefix("refs/heads/")] = sha
    return refs


def ensure_ref(root: Path, ref: str, sha: str) -> None:
    local_ref = f"refs/remotes/origin/{ref}"
    subprocess.run(["git", "-C", str(root), "fetch", "origin", f"{sha}:{local_ref}"], capture_output=True, text=True, check=True)


def tree(root: Path, ref: str, prefix: str) -> list[str]:
    output = run("git", "-C", str(root), "ls-tree", "-r", "--name-only", ref, "--", prefix)
    return [line for line in output.splitlines() if line]


def commit_date(root: Path, ref: str) -> str:
    return run("git", "-C", str(root), "show", "-s", "--format=%cI", ref)


def commit_subject(root: Path, ref: str) -> str:
    return run("git", "-C", str(root), "show", "-s", "--format=%s", ref)


def show_file(root: Path, ref: str, path: str) -> str:
    result = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def file_blob(root: Path, ref: str, path: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", f"{ref}:{path}"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    refs = remote_refs(root)
    for branch, sha in refs.items():
        ensure_ref(root, branch, sha)
    main_ref = f"origin/main"
    stable_ref = f"origin/{STABLE_BRANCH}"
    lab_ref = f"origin/{LAB_BRANCH}"

    main_sha = refs.get("main")
    stable_sha = refs.get(STABLE_BRANCH)
    lab_sha = refs.get(LAB_BRANCH)
    main_files = tree(root, main_ref, "mods/esperon-dano-solare")
    stable_files = tree(root, stable_ref, "mods/esperon-dano-solare")
    lab_files = tree(root, lab_ref, "mods/esperon-dano-solare")
    stable_script = show_file(root, stable_ref, HUD_PATH)
    main_script = show_file(root, main_ref, HUD_PATH)
    stable_mod_tree = set(stable_files)
    main_mod_tree = set(main_files)
    lab_mod_tree = set(lab_files)
    stable_dirs = {path.split("/")[2] for path in stable_files if len(path.split("/")) >= 3}
    main_dirs = {path.split("/")[2] for path in main_files if len(path.split("/")) >= 3}
    lab_dirs = {path.split("/")[2] for path in lab_files if len(path.split("/")) >= 3}
    stable_audio_diff = run("git", "-C", str(root), "diff", "--name-only", f"{main_ref}..{stable_ref}", "--", "mods/*/songs/*/*.ogg").splitlines()
    stable_mod_diff = run("git", "-C", str(root), "diff", "--name-only", f"{main_ref}..{stable_ref}", "--", "mods").splitlines()
    lab_mod_diff = run("git", "-C", str(root), "diff", "--name-only", f"{stable_ref}..{lab_ref}", "--", "mods").splitlines()
    lab_audio_diff = run("git", "-C", str(root), "diff", "--name-only", f"{stable_ref}..{lab_ref}", "--", "mods/*/songs/*/*.ogg").splitlines()
    module_import_ok = bool(re.search(r"import\s+funkin\.modding\.module\.Module", stable_script))
    extends_module_ok = bool(re.search(r"extends\s+Module", stable_script))
    result: dict[str, Any] = {
        "scope": "BRANCH_DIVERGENCE_MAIN_VS_F75A74F_V260",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "expected_main_commit": MAIN_EXPECTED,
        "branches": {
            "main": {"ref": main_ref, "sha": main_sha, "date": commit_date(root, main_ref), "subject": commit_subject(root, main_ref), "matches_expected": main_sha == MAIN_EXPECTED},
            "stable_f75a74f": {"ref": stable_ref, "branch": STABLE_BRANCH, "sha": stable_sha, "date": commit_date(root, stable_ref), "subject": commit_subject(root, stable_ref)},
            "lab": {"ref": lab_ref, "branch": LAB_BRANCH, "sha": lab_sha, "date": commit_date(root, lab_ref), "subject": commit_subject(root, lab_ref)},
        },
        "solare_tree": {
            "main_has_hud_script": HUD_PATH in main_mod_tree,
            "stable_has_hud_script": HUD_PATH in stable_mod_tree,
            "lab_has_hud_script": HUD_PATH in lab_mod_tree,
            "main_has_scripts_directory": any(path.startswith("mods/esperon-dano-solare/scripts/") for path in main_files),
            "stable_has_scripts_directory": any(path.startswith("mods/esperon-dano-solare/scripts/") for path in stable_files),
            "runtime_directories": {
                "main": {name: name in main_dirs for name in REQUIRED_RUNTIME_DIRS},
                "stable_f75a74f": {name: name in stable_dirs for name in REQUIRED_RUNTIME_DIRS},
                "lab": {name: name in lab_dirs for name in REQUIRED_RUNTIME_DIRS},
            },
            "stable_script_blob": file_blob(root, stable_ref, HUD_PATH),
            "stable_script_module_import_ok": module_import_ok,
            "stable_script_extends_module_ok": extends_module_ok,
            "main_script_bytes": len(main_script.encode("utf-8")),
            "stable_script_bytes": len(stable_script.encode("utf-8")),
        },
        "diff_summary": {
            "stable_mod_changed_paths_from_main": len(stable_mod_diff),
            "stable_audio_changed_paths_from_main": len(stable_audio_diff),
            "stable_audio_changed_paths": stable_audio_diff,
            "stable_mod_changed_paths_sample": stable_mod_diff[:80],
            "lab_mod_changed_paths_from_stable": len(lab_mod_diff),
            "lab_audio_changed_paths_from_stable": len(lab_audio_diff),
            "lab_audio_changed_paths": lab_audio_diff,
        },
        "promotion_gate": {
            "main_is_stale_relative_to_stable": main_sha != stable_sha,
            "stable_runtime_tree_complete": all(name in stable_dirs for name in REQUIRED_RUNTIME_DIRS),
            "stable_hud_script_complete": HUD_PATH in stable_mod_tree and module_import_ok and extends_module_ok,
            "main_audio_is_older_than_stable": bool(stable_audio_diff),
            "lab_runtime_matches_stable": not lab_mod_diff,
            "lab_audio_matches_stable": not lab_audio_diff,
            "automatic_merge_or_release": False,
            "decision": "REVIEW_STABLE_BRANCH_AS_SOURCE" if all(name in stable_dirs for name in REQUIRED_RUNTIME_DIRS) and HUD_PATH in stable_mod_tree and module_import_ok and extends_module_ok and not lab_mod_diff and not lab_audio_diff else "BLOCK_PROMOTION",
        },
        "notes": [
            "La lista visible de commits de main no sustituye la consulta del ref remoto.",
            "La rama estable f75a74f contiene el script HUD, audio actualizado y el árbol runtime esperado; main conserva una base anterior y se requiere decidir explícitamente si se promociona la rama estable.",
            "La comparación no modifica ramas ni crea merge/release automáticamente.",
        ],
    }
    output = root / "qa-lab" / "rebuild-v260" / "branch-divergence-main-vs-f75a74f.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"main": main_sha, "stable_f75a74f": stable_sha, "lab": lab_sha, "decision": result["promotion_gate"]["decision"], "output": str(output)}, ensure_ascii=False))
    return 0 if result["promotion_gate"]["decision"] == "REVIEW_STABLE_BRANCH_AS_SOURCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
