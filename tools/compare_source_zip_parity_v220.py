#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT = Path('/home/ubuntu/mod-review-loop-production')
VERSION = '2.2.0'
SOURCE_ROOT = ROOT / 'mods'
DELIVERY = ROOT / 'Mods .zip terminados'


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def inspect_source(source: Path, zip_path: Path) -> dict:
    errors = []
    with ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith('/')]
        roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
        if roots != {source.name}:
            errors.append(f'root mismatch: {sorted(roots)} vs {source.name}')
        zip_files = {str(PurePosixPath(name).relative_to(source.name)): digest_bytes(archive.read(name)) for name in names if PurePosixPath(name).parts and PurePosixPath(name).parts[0] == source.name}
    source_files = {str(path.relative_to(source)): digest_file(path) for path in source.rglob('*') if path.is_file()}
    missing = sorted(set(source_files) - set(zip_files))
    extra = sorted(set(zip_files) - set(source_files))
    changed = sorted(path for path in set(source_files) & set(zip_files) if source_files[path] != zip_files[path])
    if missing: errors.append(f'missing={len(missing)}')
    if extra: errors.append(f'extra={len(extra)}')
    if changed: errors.append(f'changed={len(changed)}')
    return {
        'source': source.name,
        'zip': zip_path.name,
        'source_files': len(source_files),
        'zip_files': len(zip_files),
        'missing': missing[:20],
        'extra': extra[:20],
        'changed': changed[:20],
        'status': 'PASS' if not errors else 'ERROR',
        'errors': errors,
    }


def locate_zip(source: Path) -> Path:
    # Each source song directory has its song id as the final component.
    song = source.name.removeprefix('esperon-dano-')
    expected = ''.join(part.capitalize() + '-' for part in song.split('-')).rstrip('-')
    # Preserve the project's established filename convention by matching the song id case-insensitively.
    matches = [path for path in DELIVERY.glob(f'Mod-*-V{VERSION}.zip') if song.replace('-', '').lower() in path.stem.replace('-', '').lower()]
    if len(matches) != 1:
        raise RuntimeError(f'{source.name}: expected one ZIP, found {len(matches)}')
    return matches[0]


def worker(source_name: str) -> dict:
    source = SOURCE_ROOT / source_name
    return inspect_source(source, locate_zip(source))


def main() -> int:
    sources = sorted(path.name for path in SOURCE_ROOT.glob('esperon-dano-*') if path.is_dir())
    reports = []
    with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        futures = {pool.submit(worker, name): name for name in sources}
        for future in as_completed(futures):
            reports.append(future.result())
    reports.sort(key=lambda item: item['source'])
    payload = {
        'audit': 'SOURCE_ZIP_BYTE_PARITY_VSLICE_086',
        'parallel': True,
        'input_count': len(reports),
        'passed': sum(item['status'] == 'PASS' for item in reports),
        'errors': sum(item['status'] == 'ERROR' for item in reports),
        'status': 'PASS' if len(reports) == 20 and all(item['status'] == 'PASS' for item in reports) else 'ERRORS_FOUND',
        'reports': reports,
    }
    output = ROOT / 'qa-lab/rebuild-v220/source-zip-byte-parity.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ('status', 'input_count', 'passed', 'errors')}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
