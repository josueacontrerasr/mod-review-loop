#!/usr/bin/env python3
"""Publica el último commit local mediante GitHub Git Data API invocada con gh.

Se usa cuando git push HTTPS no dispone de permisos. El publicador exige que el
padre de HEAD coincida con la punta remota de la rama, crea blobs en paralelo,
arma un tree sobre la punta remota, crea el commit y actualiza el ref sin force.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_local(*args: str) -> str:
    result = subprocess.run(list(args), cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Comando local falló")
    return result.stdout.strip()


def gh_api(path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    command = ["gh", "api", path, "--method", method]
    input_text = None
    if body is not None:
        command.extend(["--input", "-"])
        input_text = json.dumps(body, separators=(",", ":"))
    result = subprocess.run(command, cwd=ROOT, text=True, input=input_text, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"gh api {method} {path}: {result.stderr.strip()}")
    output = result.stdout.strip()
    # El terminal puede inyectar secuencias ANSI de color; la API sigue devolviendo JSON válido tras retirarlas.
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)
    output = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", output)
    if not output:
        raise RuntimeError(f"gh api {method} {path}: respuesta vacía")
    return json.loads(output)


def upload_entry(repo: str, path: str) -> dict:
    raw = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    blob = gh_api(f"repos/{repo}/git/blobs", method="POST", body={"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"})
    mode = run_local("git", "ls-tree", "HEAD", "--", path).split()[0]
    return {"path": path, "mode": mode, "type": "blob", "sha": blob["sha"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repository")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    head = run_local("git", "rev-parse", "HEAD")
    parent = run_local("git", "rev-parse", "HEAD^")
    remote_ref = gh_api(f"repos/{args.repo}/git/ref/heads/{args.branch}")
    remote_head = remote_ref["object"]["sha"]
    print(json.dumps({"stage": "remote_ref_checked", "remote_head": remote_head}, ensure_ascii=False), flush=True)
    if remote_head != parent:
        raise RuntimeError(f"La rama remota avanzó ({remote_head}) y no coincide con el padre local ({parent}); se requiere nueva revisión.")
    changed = run_local("git", "diff", "--name-status", f"{parent}..{head}").splitlines()
    additions: list[str] = []
    deletions: list[str] = []
    for row in changed:
        status, path = row.split("\t", 1)
        if status.startswith("D"):
            deletions.append(path)
        elif status.startswith(("A", "M")):
            additions.append(path)
        else:
            raise RuntimeError(f"Tipo de cambio no soportado: {row}")
    if not additions and not deletions:
        raise RuntimeError("No hay cambios para publicar")
    print(json.dumps({"status": "uploading", "files": len(additions), "deletions": len(deletions), "workers": args.workers}, ensure_ascii=False), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        entries = list(pool.map(lambda item: upload_entry(args.repo, item), additions))
    print(json.dumps({"stage": "blobs_uploaded", "files": len(entries)}, ensure_ascii=False), flush=True)
    entries.extend({"path": path, "mode": "100644", "type": "blob", "sha": None} for path in deletions)
    remote_commit = gh_api(f"repos/{args.repo}/git/commits/{remote_head}")
    tree = gh_api(f"repos/{args.repo}/git/trees", method="POST", body={"base_tree": remote_commit["tree"]["sha"], "tree": entries})
    print(json.dumps({"stage": "tree_created", "tree": tree["sha"]}, ensure_ascii=False), flush=True)
    commit = gh_api(f"repos/{args.repo}/git/commits", method="POST", body={"message": args.message, "tree": tree["sha"], "parents": [remote_head]})
    print(json.dumps({"stage": "commit_created", "commit": commit["sha"]}, ensure_ascii=False), flush=True)
    gh_api(f"repos/{args.repo}/git/refs/heads/{args.branch}", method="PATCH", body={"sha": commit["sha"], "force": False})
    print(json.dumps({"status": "published", "local_commit": head, "remote_commit": commit["sha"], "files": len(additions), "deletions": len(deletions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
