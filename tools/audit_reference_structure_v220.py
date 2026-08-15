#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

REFS = [
    Path('/home/ubuntu/upload/v-slice_yo_la_conoci_en_un_taxi.zip'),
    Path('/home/ubuntu/upload/tse_disable_shader_v25.zip'),
    Path('/home/ubuntu/upload/its-been-so-long.zip'),
    Path('/home/ubuntu/upload/TODO.zip'),
]
PROD = Path('/home/ubuntu/mod-review-loop-production')
DELIVERY = PROD / 'Mods .zip terminados'
OUTPUT = PROD / 'qa-lab' / 'rebuild-v220' / 'reference-structure-audit.json'


def read_json(zf: ZipFile, name: str):
    try:
        return json.loads(zf.read(name).decode('utf-8')), None
    except Exception as exc:
        return None, f'{name}: {exc.__class__.__name__}: {exc}'


def inspect(path: Path, kind: str) -> dict:
    result = {
        'file': str(path), 'name': path.name, 'kind': kind, 'status': 'PASS', 'errors': [],
        'bytes': path.stat().st_size if path.exists() else None,
    }
    try:
        with ZipFile(path) as zf:
            names = sorted(name.rstrip('/') for name in zf.namelist() if name and not name.startswith('__MACOSX/'))
            roots = sorted({PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts})
            result['entry_count'] = len(names)
            result['roots'] = roots
            result['root_count'] = len(roots)
            file_names = sorted(info.filename.rstrip('/') for info in zf.infolist() if not info.is_dir() and info.filename and not info.filename.startswith('__MACOSX/'))
            result['root_files'] = sorted(name for name in file_names if len(PurePosixPath(name).parts) == 2)
            result['root_text_files'] = sorted(name for name in result['root_files'] if Path(name).suffix.lower() in {'.txt', '.md', '.log', '.csv', '.tsv'})
            result['root_nonstandard_files'] = sorted(name for name in result['root_files'] if Path(name).name not in {'_polymod_meta.json', '_polymod_icon.png', 'CREDITS.txt', 'LICENSE.txt', 'INSTALACION_MOVIL.txt', 'README.md'})
            result['has_macosx'] = any(name.startswith('__MACOSX/') for name in zf.namelist())
            result['qa_paths'] = sorted(name for name in names if any(token in PurePosixPath(name).parts for token in ('qa-lab', 'reports', 'artifacts', 'previews', 'logs', 'dist')))
            result['txt_paths'] = sorted(name for name in names if Path(name).suffix.lower() in {'.txt', '.md', '.log'})
            result['data_paths'] = sorted(name for name in names if '/data/' in f'/{name}' or name.startswith('data/'))[:400]
            result['image_paths'] = sorted(name for name in names if '/images/' in f'/{name}' or name.startswith('images/'))[:400]
            result['audio_paths'] = sorted(name for name in names if Path(name).suffix.lower() in {'.ogg', '.wav', '.mp3', '.flac'})
            result['script_paths'] = sorted(name for name in names if '/scripts/' in f'/{name}' or name.startswith('scripts/'))
            result['has_manifest_root'] = any(name.endswith('/_polymod_meta.json') or name == '_polymod_meta.json' for name in names)
            result['has_data_levels'] = any('/data/levels/' in f'/{name}' or name.startswith('data/levels/') for name in names)
            result['has_data_songs'] = any('/data/songs/' in f'/{name}' or name.startswith('data/songs/') for name in names)
            result['has_songs_audio'] = any('/songs/' in f'/{name}' or name.startswith('songs/') for name in names)
            result['zip_crc'] = zf.testzip() is None
            if len(roots) != 1:
                result['errors'].append(f'root_count={len(roots)}')
            if not result['zip_crc']:
                result['errors'].append('crc-failure')
            if result['has_macosx']:
                result['errors'].append('macosx-junk')
            root = roots[0] if roots else ''
            if kind == 'current-collection':
                collection_manifest = next((name for name in file_names if name.endswith('/MANIFEST.json')), None)
                result['has_collection_manifest'] = bool(collection_manifest)
                if not collection_manifest:
                    result['errors'].append('missing-collection-manifest')
                result['status'] = 'PASS' if not result['errors'] else 'ERROR'
                return result
            meta_names = [name for name in file_names if name == f'{root}/_polymod_meta.json' or name == '_polymod_meta.json']
            if not meta_names:
                result['errors'].append('missing-root-polymod-manifest')
            else:
                metadata, err = read_json(zf, meta_names[0])
                result['polymod_meta'] = metadata if err is None else {'error': err}
            # Parse the first song metadata/level/album found, keeping enough evidence for comparison.
            for name in names:
                if name.endswith('-metadata.json') and '/data/songs/' in f'/{name}':
                    payload, err = read_json(zf, name)
                    result['song_metadata_file'] = name
                    result['song_metadata'] = payload if err is None else {'error': err}
                    break
            result['level_files'] = [name for name in names if '/data/levels/' in f'/{name}' and name.endswith('.json')]
            result['album_files'] = [name for name in names if '/data/ui/freeplay/albums/' in f'/{name}' and name.endswith('.json')]
            if result['level_files']:
                payload, err = read_json(zf, result['level_files'][0])
                result['first_level'] = payload if err is None else {'error': err}
            if result['album_files']:
                payload, err = read_json(zf, result['album_files'][0])
                result['first_album'] = payload if err is None else {'error': err}
            result['status'] = 'PASS' if not result['errors'] else 'ERROR'
    except (BadZipFile, OSError) as exc:
        result['status'] = 'ERROR'
        result['errors'].append(f'{exc.__class__.__name__}: {exc}')
    return result


def main() -> int:
    refs = [(path, 'reference') for path in REFS if path.is_file()]
    current = [(path, 'current-individual') for path in sorted(DELIVERY.glob('Mod-*-V*.zip')) if 'Coleccion' not in path.name]
    collection = [(path, 'current-collection') for path in sorted(DELIVERY.glob('Mod-Esperon-Coleccion-V*.zip'))]
    jobs = refs + current + collection
    results = []
    with ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as pool:
        futures = {pool.submit(inspect, path, kind): (path, kind) for path, kind in jobs}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (item['kind'], item['name']))
    refs_results = [item for item in results if item['kind'] == 'reference']
    current_results = [item for item in results if item['kind'] == 'current-individual']
    collection_results = [item for item in results if item['kind'] == 'current-collection']
    common_ref_root_files = sorted(set.intersection(*(set(item.get('root_files', [])) for item in refs_results))) if refs_results else []
    payload = {
        'audit': 'WIDE_RESEARCH_REFERENCE_STRUCTURE_V220',
        'target': 'FNF Mobile V-Slice 0.8.6',
        'read_only': True,
        'reference_count': len(refs_results),
        'reference_mass_zip': '/home/ubuntu/upload/TODO.zip',
        'current_individual_count': len(current_results),
        'collection_count': len(collection_results),
        'reference_common_root_files': common_ref_root_files,
        'reference_root_files_by_zip': {item['name']: item.get('root_files', []) for item in refs_results},
        'current_root_text_files_by_zip': {item['name']: item.get('root_text_files', []) for item in current_results},
        'current_root_nonstandard_files_by_zip': {item['name']: item.get('root_nonstandard_files', []) for item in current_results},
        'current_qa_paths_by_zip': {item['name']: item.get('qa_paths', []) for item in current_results},
        'reference_root_counts': {item['name']: item.get('root_count') for item in refs_results},
        'current_root_counts': {item['name']: item.get('root_count') for item in current_results},
        'results': results,
        'status': 'PASS_READ_ONLY' if len(refs_results) == 4 and len(current_results) == 20 and all(item['status'] == 'PASS' for item in results) else 'STRUCTURE_REVIEW_REQUIRED',
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ('status', 'reference_count', 'current_individual_count', 'collection_count')}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
