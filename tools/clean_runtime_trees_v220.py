#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path('/home/ubuntu/mod-review-loop-production')
MODS = ROOT / 'mods'
DOCS = ROOT / 'docs' / 'mod-documentation-v220'
EVIDENCE = ROOT / 'qa-lab' / 'rebuild-v220' / 'evidence'
AUX_DOCS = ('CREDITS.txt', 'LICENSE.txt', 'INSTALACION_MOVIL.txt')
AUX_EVIDENCE = ('audio-evidence.json', 'sync-report.json', 'visual-v2-integrity.json')
ALLOWED_ROOT_FILES = {'_polymod_meta.json'}
ALLOWED_ROOT_DIRS = {'data', 'images', 'scripts', 'shared', 'songs'}


def clean_one(mod: Path) -> dict:
    song_dirs = sorted(path for path in (mod / 'data' / 'songs').glob('*') if path.is_dir())
    if len(song_dirs) != 1:
        raise RuntimeError(f'{mod.name}: expected one song dir, got {len(song_dirs)}')
    song = song_dirs[0].name
    doc_dir = DOCS / song
    evidence_dir = EVIDENCE / song
    doc_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    moved_docs = []
    moved_evidence = []
    for name in AUX_DOCS:
        source = mod / name
        if source.is_file():
            shutil.copy2(source, doc_dir / name)
            source.unlink()
            moved_docs.append(name)
    for name in AUX_EVIDENCE:
        source = mod / name
        if source.is_file():
            shutil.copy2(source, evidence_dir / name)
            source.unlink()
            moved_evidence.append(name)
    manifest_path = mod / '_polymod_meta.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['mod_version'] = '2.2.0'
    manifest['license'] = f'Custom — documentación archivada en docs/mod-documentation-v220/{song}/LICENSE.txt'
    manifest['description'] = f"Mod V-Slice 0.8.6 con árbol runtime limpio para Freeplay/Story Mode; evidencia y documentación fuera del paquete ejecutable. Requiere Audio Sync Test y playtest móvil para confirmar sincronía."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    unexpected_files = sorted(path.name for path in mod.iterdir() if path.is_file() and path.name not in ALLOWED_ROOT_FILES)
    unexpected_dirs = sorted(path.name for path in mod.iterdir() if path.is_dir() and path.name not in ALLOWED_ROOT_DIRS)
    if unexpected_files or unexpected_dirs:
        raise RuntimeError(f'{mod.name}: runtime tree still has unexpected entries files={unexpected_files} dirs={unexpected_dirs}')
    return {'mod': mod.name, 'song': song, 'docs_moved': moved_docs, 'evidence_moved': moved_evidence, 'root_files': sorted(path.name for path in mod.iterdir() if path.is_file()), 'root_dirs': sorted(path.name for path in mod.iterdir() if path.is_dir()), 'status': 'PASS'}


def main() -> int:
    mods = sorted(path for path in MODS.glob('esperon-dano-*') if path.is_dir())
    reports = []
    with ThreadPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as pool:
        futures = {pool.submit(clean_one, mod): mod.name for mod in mods}
        for future in as_completed(futures):
            reports.append(future.result())
    reports.sort(key=lambda item: item['mod'])
    output = ROOT / 'qa-lab' / 'rebuild-v220' / 'runtime-tree-cleanup.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {'audit': 'RUNTIME_TREE_CLEANUP_V220', 'parallel': True, 'mods': len(reports), 'status': 'PASS' if len(reports) == 20 else 'ERROR', 'reports': reports}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': payload['status'], 'mods': payload['mods']}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
