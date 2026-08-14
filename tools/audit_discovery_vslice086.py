#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

ROOT = Path('/home/ubuntu/mod-review-loop-production')
SOURCE_ROOT = ROOT / 'mods'
DELIVERY = ROOT / 'Mods .zip terminados'
VERSION = '2.1.3'


def read_json_source(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8')), None
    except Exception as exc:
        return None, f'{path}: {exc.__class__.__name__}'


def read_json_zip(archive: ZipFile, name: str):
    try:
        return json.loads(archive.read(name).decode('utf-8')), None
    except Exception as exc:
        return None, f'{name}: {exc.__class__.__name__}'


def story_asset_exists_source(root: Path, asset: str) -> bool:
    if not isinstance(asset, str) or not asset:
        return False
    base = root / 'images' / asset
    return base.is_file() or (Path(str(base) + '.png')).is_file() or (Path(str(base) + '.xml')).is_file()


def story_asset_exists_zip(names: set[str], root: str, asset: str) -> bool:
    if not isinstance(asset, str) or not asset:
        return False
    base = f'{root}/images/{asset}'
    return base in names or f'{base}.png' in names or f'{base}.xml' in names


def find_song_dir_source(root: Path):
    dirs = sorted(path for path in (root / 'data' / 'songs').glob('*') if path.is_dir()) if (root / 'data' / 'songs').is_dir() else []
    return dirs[0] if len(dirs) == 1 else None


def find_song_dir_zip(names: set[str], root: str):
    prefix = f'{root}/data/songs/'
    dirs = sorted({PurePosixPath(name).parts[3] for name in names if name.startswith(prefix) and len(PurePosixPath(name).parts) >= 5})
    return dirs[0] if len(dirs) == 1 else None


def inspect_source(root: Path) -> dict:
    errors = []
    warnings = []
    song_dir = find_song_dir_source(root)
    if song_dir is None:
        return {'mod': root.name, 'source': True, 'status': 'ERROR', 'errors': ['song dir count != 1'], 'warnings': []}
    song = song_dir.name
    metadata_path = song_dir / f'{song}-metadata.json'
    metadata, err = read_json_source(metadata_path)
    if err: errors.append(err)
    if not isinstance(metadata, dict): metadata = {}
    play = metadata.get('playData') if isinstance(metadata.get('playData'), dict) else {}
    level_root = root / 'data' / 'levels'
    level_paths = sorted(level_root.glob('*.json')) if level_root.is_dir() else []
    level_reports = []
    for level_path in level_paths:
        level, level_err = read_json_source(level_path)
        item = {'file': str(level_path.relative_to(root)), 'json_error': level_err}
        if isinstance(level, dict):
            item.update({key: level.get(key) for key in ('version', 'name', 'titleAsset', 'visible', 'songs', 'capsule')})
            item['title_asset_resolved'] = story_asset_exists_source(root, level.get('titleAsset'))
            item['song_linked'] = song in (level.get('songs') or [])
            item['props_resolved'] = all(story_asset_exists_source(root, prop.get('assetPath')) for prop in (level.get('props') or []) if isinstance(prop, dict))
        level_reports.append(item)
    chart, chart_err = read_json_source(song_dir / f'{song}-chart.json')
    if chart_err: errors.append(chart_err)
    chart_notes = chart.get('notes', {}) if isinstance(chart, dict) else {}
    chart_difficulties = sorted(chart_notes.keys()) if isinstance(chart_notes, dict) else []
    declared_difficulties = sorted(play.get('difficulties') or [])
    album = play.get('album')
    top_album = metadata.get('album')
    if not album and top_album:
        errors.append('album is at metadata root, not playData.album')
    if not level_paths:
        errors.append('no data/levels/*.json: song cannot be enumerated by FreeplayState or Story Mode')
    else:
        if not any(item.get('song_linked') for item in level_reports): errors.append('no level links this song in songs[]')
        if any(item.get('version') not in (None, '1.0.2') for item in level_reports): errors.append('level schema is not 1.0.2')
        if any(item.get('visible') is False for item in level_reports): warnings.append('level visible=false')
        if any(not item.get('title_asset_resolved') for item in level_reports): errors.append('level titleAsset unresolved')
    if declared_difficulties != chart_difficulties:
        warnings.append(f'difficulties metadata={declared_difficulties} chart={chart_difficulties}')
    status = 'PASS' if not errors else 'ERROR'
    return {
        'mod': root.name, 'source': True, 'song': song, 'status': status, 'errors': errors, 'warnings': warnings,
        'level_count': len(level_paths), 'levels': level_reports,
        'playData_album': album, 'metadata_root_album': top_album,
        'songVariations': play.get('songVariations'), 'declared_difficulties': declared_difficulties,
        'chart_difficulties': chart_difficulties,
    }


def inspect_zip(zip_path: Path) -> dict:
    errors = []
    warnings = []
    with ZipFile(zip_path) as archive:
        names = {name.rstrip('/') for name in archive.namelist()}
        roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
        if len(roots) != 1:
            return {'mod': zip_path.name, 'source': False, 'status': 'ERROR', 'errors': ['root count != 1'], 'warnings': []}
        root = next(iter(roots))
        song_dir = find_song_dir_zip(names, root)
        if song_dir is None:
            return {'mod': zip_path.name, 'source': False, 'status': 'ERROR', 'errors': ['song dir count != 1'], 'warnings': []}
        song = song_dir
        meta_name = f'{root}/data/songs/{song}/{song}-metadata.json'
        metadata, err = read_json_zip(archive, meta_name)
        if err: errors.append(err)
        if not isinstance(metadata, dict): metadata = {}
        play = metadata.get('playData') if isinstance(metadata.get('playData'), dict) else {}
        level_prefix = f'{root}/data/levels/'
        level_names = sorted(name for name in names if name.startswith(level_prefix) and name.endswith('.json'))
        level_reports = []
        for level_name in level_names:
            level, level_err = read_json_zip(archive, level_name)
            item = {'file': level_name.removeprefix(f'{root}/'), 'json_error': level_err}
            if isinstance(level, dict):
                item.update({key: level.get(key) for key in ('version', 'name', 'titleAsset', 'visible', 'songs', 'capsule')})
                item['title_asset_resolved'] = story_asset_exists_zip(names, root, level.get('titleAsset'))
                item['song_linked'] = song in (level.get('songs') or [])
                item['props_resolved'] = all(story_asset_exists_zip(names, root, prop.get('assetPath')) for prop in (level.get('props') or []) if isinstance(prop, dict))
            level_reports.append(item)
        chart_name = f'{root}/data/songs/{song}/{song}-chart.json'
        chart, chart_err = read_json_zip(archive, chart_name)
        if chart_err: errors.append(chart_err)
        chart_notes = chart.get('notes', {}) if isinstance(chart, dict) else {}
        chart_difficulties = sorted(chart_notes.keys()) if isinstance(chart_notes, dict) else []
        declared_difficulties = sorted(play.get('difficulties') or [])
        album = play.get('album')
        top_album = metadata.get('album')
        if not album and top_album: errors.append('album is at metadata root, not playData.album')
        if not level_names: errors.append('no data/levels/*.json: song cannot be enumerated by FreeplayState or Story Mode')
        else:
            if not any(item.get('song_linked') for item in level_reports): errors.append('no level links this song in songs[]')
            if any(item.get('version') not in (None, '1.0.2') for item in level_reports): errors.append('level schema is not 1.0.2')
            if any(item.get('visible') is False for item in level_reports): warnings.append('level visible=false')
            if any(not item.get('title_asset_resolved') for item in level_reports): errors.append('level titleAsset unresolved')
        if declared_difficulties != chart_difficulties: warnings.append(f'difficulties metadata={declared_difficulties} chart={chart_difficulties}')
        return {
            'mod': zip_path.name, 'source': False, 'song': song, 'status': 'PASS' if not errors else 'ERROR', 'errors': errors, 'warnings': warnings,
            'level_count': len(level_names), 'levels': level_reports,
            'playData_album': album, 'metadata_root_album': top_album,
            'songVariations': play.get('songVariations'), 'declared_difficulties': declared_difficulties,
            'chart_difficulties': chart_difficulties,
        }


def worker(pair: tuple[str, str]) -> dict:
    kind, path = pair
    return inspect_source(Path(path)) if kind == 'source' else inspect_zip(Path(path))


def main() -> int:
    source_paths = sorted(SOURCE_ROOT.glob('esperon-dano-*'))
    source_names = {path.name.removeprefix('esperon-dano-'): path for path in source_paths if path.is_dir()}
    zip_paths = sorted(path for path in DELIVERY.glob(f'Mod-*-V{VERSION}.zip') if path.name != f'Mod-Esperon-Coleccion-V{VERSION}.zip')
    jobs = [('source', str(path)) for path in source_paths if path.is_dir()] + [('zip', str(path)) for path in zip_paths]
    reports = []
    with ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as pool:
        futures = {pool.submit(worker, job): job for job in jobs}
        for future in as_completed(futures): reports.append(future.result())
    reports.sort(key=lambda item: (item.get('source') is False, item.get('mod', '')))
    source_reports = [item for item in reports if item['source']]
    zip_reports = [item for item in reports if not item['source']]
    payload = {
        'audit': 'DISCOVERY_VISIBILITY_VSLICE_086',
        'target': 'FNF Mobile V-Slice 0.8.6',
        'parallel': True,
        'source_count': len(source_reports),
        'zip_count': len(zip_reports),
        'source_passed': sum(item['status'] == 'PASS' for item in source_reports),
        'zip_passed': sum(item['status'] == 'PASS' for item in zip_reports),
        'source_errors': sum(item['status'] == 'ERROR' for item in source_reports),
        'zip_errors': sum(item['status'] == 'ERROR' for item in zip_reports),
        'root_cause_confirmed': 'Missing data/levels/*.json prevents FreeplayState from enumerating these songs.',
        'status': 'PASS' if len(source_reports) == 20 and len(zip_reports) == 20 and all(item['status'] == 'PASS' for item in reports) else 'DISCOVERY_ERRORS_FOUND',
        'reports': reports,
    }
    output = ROOT / 'qa-lab/wide-research-v212/discovery-visibility-audit.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ('status', 'source_count', 'zip_count', 'source_passed', 'zip_passed', 'source_errors', 'zip_errors')}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
