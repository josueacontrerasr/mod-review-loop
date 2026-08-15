#!/usr/bin/env python3
"""Publica cambios locales con createCommitOnBranch en lotes moderados.

Usa GitHub CLI para invocar GraphQL. Cada lote exige la punta anterior de la
rama, por lo que evita sobrescrituras. Los ZIPs grandes viajan solos; los assets
pequeños se agrupan para reducir drásticamente las solicitudes de contenido.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANSI_OSC = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")
MUTATION = """mutation($input: CreateCommitOnBranchInput!) {
  createCommitOnBranch(input: $input) {
    commit { oid url }
    ref { name }
  }
}"""


def clean(value: str) -> str:
    return ANSI_OSC.sub("", ANSI_CSI.sub("", value)).strip()


def local(*args: str) -> str:
    result = subprocess.run(list(args), cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(clean(result.stderr) or "Comando local falló")
    return clean(result.stdout)


def api_json(args: list[str], payload: dict | None = None) -> dict:
    command = ["gh", "api", *args]
    raw = None
    if payload is not None:
        command.extend(["--input", "-"])
        raw = json.dumps(payload, separators=(",", ":"))
    result = subprocess.run(command, cwd=ROOT, text=True, input=raw, capture_output=True)
    output = clean(result.stdout)
    if result.returncode:
        raise RuntimeError(clean(result.stderr) or output or "GitHub API rechazó la solicitud")
    if not output:
        raise RuntimeError("GitHub API devolvió una respuesta vacía")
    parsed = json.loads(output)
    if parsed.get("errors"):
        raise RuntimeError(json.dumps(parsed["errors"], ensure_ascii=False))
    return parsed


def remote_head(repo: str, branch: str) -> str:
    payload = api_json([f"repos/{repo}/git/ref/heads/{branch}"])
    return payload["object"]["sha"]


def changes(parent: str, head: str) -> list[str]:
    lines = local("git", "diff", "--name-status", f"{parent}..{head}").splitlines()
    paths: list[str] = []
    for line in lines:
        status, path = line.split("\t", 1)
        if status.startswith("D"):
            raise RuntimeError(f"No se admiten eliminaciones en este publicador: {path}")
        if not status.startswith(("A", "M")):
            raise RuntimeError(f"Cambio no admitido: {line}")
        paths.append(path)
    return paths


def chunks(paths: list[str], *, max_files: int, max_bytes: int) -> list[list[str]]:
    output: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0
    for path in paths:
        size = int(local("git", "cat-file", "-s", f"HEAD:{path}"))
        # ZIPs grandes van solos para mantener el payload GraphQL razonable.
        if size >= max_bytes:
            if current:
                output.append(current)
                current, current_bytes = [], 0
            output.append([path])
            continue
        if current and (len(current) >= max_files or current_bytes + size > max_bytes):
            output.append(current)
            current, current_bytes = [], 0
        current.append(path)
        current_bytes += size
    if current:
        output.append(current)
    return output


def addition(path: str) -> dict[str, str]:
    binary = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, check=True).stdout
    return {"path": path, "contents": base64.b64encode(binary).decode("ascii")}


def publish_batch(repo: str, branch: str, expected: str, headline: str, paths: list[str]) -> str:
    payload = {
        "query": MUTATION,
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": repo, "branchName": branch},
                "message": {"headline": headline},
                "expectedHeadOid": expected,
                "fileChanges": {"additions": [addition(path) for path in paths]},
            }
        },
    }
    response = api_json(["graphql"], payload)
    data = response.get("data", {}).get("createCommitOnBranch")
    if not data:
        raise RuntimeError(json.dumps(response, ensure_ascii=False))
    return data["commit"]["oid"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--max-files", type=int, default=50)
    parser.add_argument("--max-bytes", type=int, default=1_000_000)
    args = parser.parse_args()

    head = local("git", "rev-parse", "HEAD")
    parent = local("git", "rev-parse", "HEAD^")
    remote = remote_head(args.repo, args.branch)
    if remote != parent:
        raise RuntimeError(f"La punta remota {remote} no coincide con el padre local {parent}; no se sobrescribirá la rama.")
    paths = changes(parent, head)
    grouped = chunks(paths, max_files=max(1, args.max_files), max_bytes=max(1, args.max_bytes))
    print(json.dumps({"status": "ready", "files": len(paths), "batches": len(grouped), "remote_head": remote}, ensure_ascii=False), flush=True)
    current = remote
    for index, batch in enumerate(grouped, start=1):
        label = f"{args.message} ({index}/{len(grouped)})"
        current = publish_batch(args.repo, args.branch, current, label, batch)
        print(json.dumps({"status": "batch_published", "batch": index, "of": len(grouped), "files": len(batch), "head": current}, ensure_ascii=False), flush=True)
    print(json.dumps({"status": "published", "remote_head": current, "batches": len(grouped), "files": len(paths)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
