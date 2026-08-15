#!/usr/bin/env python3
"""Publica un commit local en una rama de GitHub mediante la API Git Database.

Se usa cuando la API dispone de permisos de escritura pero el transporte Git HTTPS
rechaza la misma sesión. No modifica la rama base ni fuerza referencias.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def command(args: list[str], *, text: str | None = None) -> str:
    environment = os.environ.copy()
    environment.update({"NO_COLOR": "1", "CLICOLOR": "0", "TERM": "dumb"})
    result = subprocess.run(args, cwd=ROOT, input=text, text=True, capture_output=True, env=environment)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args)}\n{result.stderr}")
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout)


def api(method: str, endpoint: str, payload: dict | None = None) -> dict:
    args = ["gh", "api", "-X", method, endpoint]
    body = json.dumps(payload, ensure_ascii=False) if payload is not None else None
    if body is not None:
        args += ["--input", "-"]
    output = command(args, text=body)
    return json.loads(output) if output.strip() else {}


def local_changes(base: str) -> list[tuple[str, str]]:
    raw = command(["git", "diff", "--name-status", f"{base}..HEAD"])
    changes = []
    for line in raw.splitlines():
        status, path = line.split("\t", 1)
        if status.startswith("R"):
            _, old, new = line.split("\t", 2)
            changes.append(("D", old))
            changes.append(("A", new))
        else:
            changes.append((status[0], path))
    return changes


def mode_for(path: str) -> str:
    line = command(["git", "ls-files", "-s", "--", path]).strip()
    if not line:
        return "100644"
    return line.split()[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", default="main")
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    base_ref = api("GET", f"repos/{args.repo}/git/ref/heads/{args.branch}")
    remote_parent = base_ref["object"]["sha"]
    parent_commit = api("GET", f"repos/{args.repo}/git/commits/{remote_parent}")
    entries: list[dict] = []
    blob_cache: dict[str, str] = {}
    changes = local_changes(args.base)
    for status, relative in changes:
        if relative.startswith(("artifacts/", "build-logs/", "reports/")):
            continue
        if status == "D":
            entries.append({"path": relative, "mode": "100644", "type": "blob", "sha": None})
            continue
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"Archivo local no encontrado: {relative}")
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest not in blob_cache:
            blob = api("POST", f"repos/{args.repo}/git/blobs", {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"})
            blob_cache[digest] = blob["sha"]
        entries.append({"path": relative, "mode": mode_for(relative), "type": "blob", "sha": blob_cache[digest]})
    tree = api("POST", f"repos/{args.repo}/git/trees", {"base_tree": parent_commit["tree"]["sha"], "tree": entries})
    commit = api("POST", f"repos/{args.repo}/git/commits", {"message": args.message, "tree": tree["sha"], "parents": [remote_parent]})
    api("PATCH", f"repos/{args.repo}/git/refs/heads/{args.branch}", {"sha": commit["sha"], "force": False})
    report = {"repo": args.repo, "branch": args.branch, "parent": remote_parent, "commit": commit["sha"], "files": len(entries), "unique_blobs": len(blob_cache)}
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
