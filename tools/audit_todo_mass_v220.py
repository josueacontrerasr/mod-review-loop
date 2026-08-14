#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import PurePosixPath
from pathlib import Path
from zipfile import ZipFile

ZIP_PATH = Path('/home/ubuntu/upload/TODO.zip')
OUTPUT = Path('/home/ubuntu/mod-review-loop-production/qa-lab/rebuild-v220/todo-mass-structure-audit.json')


def read_json(zf: ZipFile, name: str):
    try:
        return json.loads(zf.read(name).decode('utf-8')), None
    except Exception as exc:
        return None, f'{exc.__class__.__name__}: {exc}'


def inspect_candidate(candidate: str, all_names: list[str]) -> dict:
    prefix = candidate.rstrip('/') + '/'
    candidate_names = [name for name in all_names if name.startswith(prefix)]
    files = [name for name in candidate_names if not name.endswith('/')]
    relative_files = sorted(name[len(prefix):] for name in files)
    root_files = sorted(name for name in relative_files if '/' not in name)
    root_dirs = sorted({name.split('/', 1)[0] for name in relative_files if '/' in name})
    txt_files = sorted(name for name in relative_files if Path(name).suffix.lower() in {'.txt', '.md', '.log'})
    aux_files = sorted(name for name in relative_files if Path(name).name in {'audio-evidence.json', 'sync-report.json', 'visual-v2-integrity.json'} or any(token in name.split('/') for token in ('qa-lab', 'artifacts', 'previews', 'reports', 'logs')))
    data_songs = sorted(name for name in relative_files if name.startswith('data/songs/') and name.endswith('.json'))
    levels = sorted(name for name in relative_files if name.startswith('data/levels/') and name.endswith('.json'))
    images = sorted(name for name in relative_files if name.startswith('images/') or name.startswith('shared/images/'))
    audio = sorted(name for name in relative_files if Path(name).suffix.lower() in {'.ogg', '.wav', '.mp3', '.flac'})
    manifest_path = next((name for name in relative_files if name == '_polymod_meta.json'), None)
    manifest = None
    manifest_error = None
    if manifest_path:
        with ZipFile(ZIP_PATH) as zf:
            manifest, manifest_error = read_json(zf, prefix + manifest_path)
    return {
        'candidate': candidate,
        'file_count': len(files),
        'root_files': root_files,
        'root_dirs': root_dirs,
        'txt_files': txt_files,
        'aux_files': aux_files,
        'data_song_json_count': len(data_songs),
        'level_json_count': len(levels),
        'image_count': len(images),
        'audio_count': len(audio),
        'manifest_path': manifest_path,
        'manifest_error': manifest_error,
        'manifest': manifest,
        'status': 'MOD_MANIFEST_FOUND' if manifest_path and not manifest_error else 'CANDIDATE_WITHOUT_VALID_MANIFEST',
    }


def main() -> int:
    with ZipFile(ZIP_PATH) as zf:
        all_names = sorted(name.rstrip('/') for name in zf.namelist() if name and not name.startswith('__MACOSX/'))
    roots = sorted({PurePosixPath(name).parts[0] for name in all_names if PurePosixPath(name).parts})
    todo_root = roots[0] if len(roots) == 1 else None
    direct_dirs = sorted({PurePosixPath(name).parts[1] for name in all_names if todo_root and name.startswith(todo_root + '/') and len(PurePosixPath(name).parts) >= 2})
    candidate_paths = [f'{todo_root}/{directory}' for directory in direct_dirs] if todo_root else []
    manifest_paths = [name for name in all_names if name.endswith('/_polymod_meta.json')]
    candidate_by_manifest = sorted({name.rsplit('/_polymod_meta.json', 1)[0] for name in manifest_paths})
    with ThreadPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as pool:
        futures = {pool.submit(inspect_candidate, candidate, all_names): candidate for candidate in candidate_paths}
        candidates = [future.result() for future in as_completed(futures)]
    candidates.sort(key=lambda item: item['candidate'])
    payload = {
        'audit': 'TODO_MASS_REFERENCE_STRUCTURE_V220',
        'read_only': True,
        'zip': str(ZIP_PATH),
        'zip_bytes': ZIP_PATH.stat().st_size,
        'entry_count': len(all_names),
        'zip_roots': roots,
        'todo_root': todo_root,
        'direct_subdirectories': direct_dirs,
        'direct_candidate_count': len(candidate_paths),
        'polymod_manifest_count': len(manifest_paths),
        'polymod_manifest_candidate_paths': candidate_by_manifest,
        'mods_with_valid_manifest': sum(item['status'] == 'MOD_MANIFEST_FOUND' for item in candidates),
        'candidates_without_valid_manifest': sum(item['status'] != 'MOD_MANIFEST_FOUND' for item in candidates),
        'total_txt_or_markdown_files': sum(len(item['txt_files']) for item in candidates),
        'total_auxiliary_files': sum(len(item['aux_files']) for item in candidates),
        'candidates': candidates,
        'interpretation': 'TODO.zip es un contenedor masivo; cada subdirectorio con _polymod_meta.json debe compararse como mod individual y las carpetas sin manifiesto deben clasificarse como plantilla, recurso o paquete incompleto.',
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ('entry_count', 'direct_candidate_count', 'polymod_manifest_count', 'mods_with_valid_manifest', 'candidates_without_valid_manifest', 'total_txt_or_markdown_files')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
