#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

ROOT = Path('/home/ubuntu/mod-review-loop-production')
MODS = ROOT / 'mods'
OUTPUT = ROOT / 'qa-lab/rebuild-v220/runtime-code-audit-v220.json'
ALLOWED_RENDER_TYPES = {'sparrow', 'packer', 'multisparrow', 'animateatlas', 'multianimateatlas', 'custom'}
REQUIRED_ANIMS = {'idle', 'singLEFT', 'singDOWN', 'singUP', 'singRIGHT'}


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8')), None
    except Exception as exc:
        return None, f'{exc.__class__.__name__}: {exc}'


def resolve_asset(root: Path, asset: str) -> dict:
    if not isinstance(asset, str) or not asset:
        return {'ok': False, 'asset': asset, 'paths': []}
    if asset.startswith('shared:'):
        relative = Path('shared/images') / asset.removeprefix('shared:')
    elif asset.startswith('library:'):
        relative = Path('images') / asset.removeprefix('library:')
    else:
        relative = Path('images') / asset
    base = root / relative
    paths = [base, Path(str(base) + '.png'), Path(str(base) + '.xml'), Path(str(base) + '.json')]
    existing = [path for path in paths if path.is_file()]
    return {'ok': bool(existing), 'asset': asset, 'relative': relative.as_posix(), 'existing': [str(path.relative_to(root)) for path in existing]}


def atlas_info(root: Path, xml_path: Path) -> dict:
    errors = []
    names = []
    image_path = None
    texture = None
    try:
        xml_root = ET.parse(xml_path).getroot()
        image_path = xml_root.attrib.get('imagePath')
        names = [node.attrib.get('name', '') for node in xml_root.findall('.//SubTexture')]
        if not names:
            errors.append('atlas has no SubTexture frames')
        if image_path:
            texture = (xml_path.parent / image_path).resolve()
            if not texture.is_file():
                errors.append(f'imagePath unresolved: {image_path}')
                texture = None
        else:
            errors.append('atlas missing imagePath')
        if texture:
            with Image.open(texture) as image:
                width, height = image.size
            for node in xml_root.findall('.//SubTexture'):
                try:
                    x, y, w, h = [int(node.attrib.get(key, '-1')) for key in ('x', 'y', 'width', 'height')]
                    if min(x, y, w, h) < 0 or x + w > width or y + h > height:
                        errors.append(f'frame out of bounds: {node.attrib.get("name", "") or "<unnamed>"}')
                except ValueError:
                    errors.append('frame contains non-integer bounds')
    except (ET.ParseError, OSError, ValueError) as exc:
        errors.append(f'xml/texture parse failed: {exc}')
    return {'xml': str(xml_path.relative_to(root)), 'imagePath': image_path, 'frame_count': len(names), 'frame_names': names, 'errors': errors, 'status': 'PASS' if not errors else 'ERROR'}


def inspect_character(root: Path, character_id: str, errors: list, warnings: list) -> dict:
    path = root / 'data' / 'characters' / f'{character_id}.json'
    data, err = read_json(path)
    if err or not isinstance(data, dict):
        errors.append(f'character {character_id}: invalid/missing JSON ({err})')
        return {'id': character_id, 'status': 'ERROR', 'json': str(path.relative_to(root)) if path.exists() else None}
    local_errors = []
    if data.get('version') != '1.0.2': local_errors.append(f'version={data.get("version")}')
    if data.get('renderType') not in ALLOWED_RENDER_TYPES: local_errors.append(f'renderType={data.get("renderType")}')
    resolved = resolve_asset(root, data.get('assetPath'))
    if not resolved['ok']: local_errors.append(f'assetPath unresolved: {data.get("assetPath")}')
    atlas_reports = []
    for existing in resolved.get('existing', []):
        if existing.endswith('.xml'):
            report = atlas_info(root, root / existing)
            atlas_reports.append(report)
    frames = [name for report in atlas_reports for name in report['frame_names']]
    animations = data.get('animations') if isinstance(data.get('animations'), list) else []
    animation_names = {item.get('name') for item in animations if isinstance(item, dict)}
    if not REQUIRED_ANIMS.issubset(animation_names):
        local_errors.append(f'missing required animation names: {sorted(REQUIRED_ANIMS - animation_names)}')
    missing_prefixes = []
    for item in animations:
        if not isinstance(item, dict):
            local_errors.append('animation entry is not object')
            continue
        prefix = item.get('prefix')
        if not isinstance(prefix, str) or not prefix:
            local_errors.append(f'animation {item.get("name")}: empty prefix')
        elif not any(name.startswith(prefix) for name in frames):
            missing_prefixes.append(prefix)
    if missing_prefixes: local_errors.append(f'missing atlas prefixes: {sorted(set(missing_prefixes))}')
    if not frames: local_errors.append('no atlas frames resolved')
    if local_errors: errors.extend(f'character {character_id}: {item}' for item in local_errors)
    return {'id': character_id, 'status': 'PASS' if not local_errors else 'ERROR', 'json': str(path.relative_to(root)), 'renderType': data.get('renderType'), 'assetPath': data.get('assetPath'), 'asset_resolution': resolved, 'animation_names': sorted(animation_names), 'atlas_reports': atlas_reports, 'errors': local_errors}


def inspect_note_style(root: Path, style_id: str, errors: list) -> dict:
    path = root / 'data' / 'notestyles' / f'{style_id}.json'
    data, err = read_json(path)
    local_errors = []
    if err or not isinstance(data, dict):
        local_errors.append(f'invalid/missing JSON: {err}')
        errors.extend(f'noteStyle {style_id}: {item}' for item in local_errors)
        return {'id': style_id, 'status': 'ERROR', 'errors': local_errors}
    if data.get('version') not in {'1.0.0', '1.0.1'}:
        local_errors.append(f'version={data.get("version")}')
    assets = data.get('assets') if isinstance(data.get('assets'), dict) else {}
    asset_reports = []
    expected = {'note', 'noteStrumline'}
    if not expected.issubset(assets):
        local_errors.append(f'missing required asset groups: {sorted(expected - set(assets))}')
    for group, payload in assets.items():
        if not isinstance(payload, dict):
            local_errors.append(f'{group}: asset entry is not object')
            continue
        asset = payload.get('assetPath')
        resolved = resolve_asset(root, asset)
        report = {'group': group, 'assetPath': asset, 'resolution': resolved, 'prefixes': []}
        if not resolved['ok']:
            local_errors.append(f'{group} assetPath unresolved: {asset}')
            asset_reports.append(report)
            continue
        frames = []
        for existing in resolved.get('existing', []):
            if existing.endswith('.xml'):
                atlas = atlas_info(root, root / existing)
                report['atlas'] = atlas
                frames.extend(atlas['frame_names'])
                local_errors.extend(atlas['errors'])
        nested = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        prefixes = []
        for item in nested.values():
            if isinstance(item, dict) and isinstance(item.get('prefix'), str): prefixes.append(item['prefix'])
        report['prefixes'] = sorted(set(prefixes))
        missing = sorted(prefix for prefix in set(prefixes) if not any(frame.startswith(prefix) for frame in frames))
        if missing: local_errors.append(f'{group} missing atlas prefixes: {missing}')
        asset_reports.append(report)
    if local_errors: errors.extend(f'noteStyle {style_id}: {item}' for item in local_errors)
    return {'id': style_id, 'status': 'PASS' if not local_errors else 'ERROR', 'json': str(path.relative_to(root)), 'asset_reports': asset_reports, 'errors': local_errors}


def inspect_stage(root: Path, stage_id: str, errors: list) -> dict:
    path = root / 'data' / 'stages' / f'{stage_id}.json'
    data, err = read_json(path)
    if err or not isinstance(data, dict):
        errors.append(f'stage {stage_id}: invalid/missing JSON ({err})')
        return {'id': stage_id, 'status': 'ERROR'}
    local_errors = []
    if data.get('version') not in {'1.0.0', '1.0.1'}: local_errors.append(f'version={data.get("version")}')
    props = data.get('props') if isinstance(data.get('props'), list) else []
    prop_reports = []
    for prop in props:
        if not isinstance(prop, dict):
            local_errors.append('prop is not object'); continue
        resolved = resolve_asset(root, prop.get('assetPath'))
        report = {'assetPath': prop.get('assetPath'), 'resolution': resolved, 'animations': prop.get('animations', [])}
        if not resolved['ok']: local_errors.append(f'prop assetPath unresolved: {prop.get("assetPath")}')
        for existing in resolved.get('existing', []):
            if existing.endswith('.xml'):
                atlas = atlas_info(root, root / existing)
                report['atlas'] = atlas
                if atlas['errors']: local_errors.extend(atlas['errors'])
        prop_reports.append(report)
    characters = data.get('characters') if isinstance(data.get('characters'), dict) else {}
    for role, char_id in characters.items():
        if isinstance(char_id, str) and not (root / 'data' / 'characters' / f'{char_id}.json').is_file() and char_id not in {'bf', 'gf', 'dad', 'spooky', 'pico'}:
            local_errors.append(f'character link unresolved: {role}={char_id}')
    if local_errors: errors.extend(f'stage {stage_id}: {item}' for item in local_errors)
    return {'id': stage_id, 'status': 'PASS' if not local_errors else 'ERROR', 'json': str(path.relative_to(root)), 'prop_count': len(props), 'props': prop_reports, 'characters': characters, 'errors': local_errors}


def inspect_level(root: Path, song: str, errors: list) -> dict:
    paths = sorted((root / 'data' / 'levels').glob('*.json'))
    reports = []
    linked = False
    for path in paths:
        data, err = read_json(path)
        local_errors = []
        if err or not isinstance(data, dict): local_errors.append(f'invalid JSON: {err}')
        else:
            if data.get('version') != '1.0.2': local_errors.append(f'version={data.get("version")}')
            if data.get('visible') is False: local_errors.append('visible=false')
            if song in (data.get('songs') or []): linked = True
            else: continue
            if not resolve_asset(root, data.get('titleAsset'))['ok']: local_errors.append(f'titleAsset unresolved: {data.get("titleAsset")}')
            for prop in data.get('props') or []:
                if isinstance(prop, dict) and not resolve_asset(root, prop.get('assetPath'))['ok']:
                    local_errors.append(f'level prop unresolved: {prop.get("assetPath")}')
        reports.append({'file': str(path.relative_to(root)), 'errors': local_errors})
        errors.extend(f'level {path.name}: {item}' for item in local_errors)
    if not linked: errors.append(f'no visible level links song {song}')
    return {'level_count': len(paths), 'linked': linked, 'reports': reports}


def inspect_mod(mod_path: Path) -> dict:
    errors = []
    warnings = []
    song_dirs = sorted(path for path in (mod_path / 'data' / 'songs').glob('*') if path.is_dir())
    if len(song_dirs) != 1:
        return {'mod': mod_path.name, 'status': 'ERROR', 'errors': [f'song dir count={len(song_dirs)}'], 'warnings': []}
    song_dir = song_dirs[0]
    song = song_dir.name
    metadata, err = read_json(song_dir / f'{song}-metadata.json')
    if err or not isinstance(metadata, dict):
        return {'mod': mod_path.name, 'song': song, 'status': 'ERROR', 'errors': [f'metadata invalid: {err}'], 'warnings': []}
    play = metadata.get('playData') if isinstance(metadata.get('playData'), dict) else {}
    if metadata.get('version') != '2.2.4': errors.append(f'metadata version={metadata.get("version")}')
    chart, chart_err = read_json(song_dir / f'{song}-chart.json')
    if chart_err or not isinstance(chart, dict) or chart.get('version') != '2.0.0': errors.append(f'chart invalid/version: {chart_err or (chart or {}).get("version")}')
    difficulties = play.get('difficulties') if isinstance(play.get('difficulties'), list) else []
    notes = chart.get('notes') if isinstance(chart, dict) and isinstance(chart.get('notes'), dict) else {}
    for difficulty in difficulties:
        if difficulty not in notes or not isinstance(notes[difficulty], list) or not notes[difficulty]: errors.append(f'difficulty missing/empty: {difficulty}')
    for difficulty, note_list in notes.items():
        previous = -1.0
        if not isinstance(note_list, list): errors.append(f'notes[{difficulty}] not list'); continue
        for index, note in enumerate(note_list):
            if not isinstance(note, dict) or not isinstance(note.get('t'), (int, float)) or not isinstance(note.get('d'), int):
                errors.append(f'chart {difficulty}[{index}] malformed'); break
            if float(note['t']) < previous: errors.append(f'chart {difficulty} unsorted'); break
            previous = float(note['t'])
    chars = play.get('characters') if isinstance(play.get('characters'), dict) else {}
    char_reports = []
    for role in ('player', 'opponent'):
        char_id = chars.get(role)
        if not isinstance(char_id, str): errors.append(f'playData.characters.{role} missing')
        else: char_reports.append(inspect_character(mod_path, char_id, errors, warnings))
    stage_id = play.get('stage')
    stage_report = inspect_stage(mod_path, stage_id, errors) if isinstance(stage_id, str) else {'status': 'ERROR', 'errors': ['stage missing']}
    if not isinstance(stage_id, str): errors.append('playData.stage missing')
    style_id = play.get('noteStyle')
    style_report = inspect_note_style(mod_path, style_id, errors) if isinstance(style_id, str) else {'status': 'ERROR', 'errors': ['noteStyle missing']}
    if not isinstance(style_id, str): errors.append('playData.noteStyle missing')
    album_id = play.get('album')
    album_path = mod_path / 'data' / 'ui' / 'freeplay' / 'albums' / f'{album_id}.json' if isinstance(album_id, str) else None
    album, album_err = read_json(album_path) if album_path else (None, 'missing')
    album_errors = []
    if album_err or not isinstance(album, dict): album_errors.append(f'album invalid: {album_id}')
    else:
        if album.get('version') != '1.0.3': album_errors.append(f'album version={album.get("version")}')
        for field in ('albumArtAsset', 'albumTitleAsset'):
            if not resolve_asset(mod_path, album.get(field))['ok']: album_errors.append(f'{field} unresolved: {album.get(field)}')
    if album_errors: errors.extend(album_errors)
    level_report = inspect_level(mod_path, song, errors)
    script_reports = []
    for script in sorted((mod_path / 'scripts').glob('*.hxc')):
        text = script.read_text(encoding='utf-8', errors='replace')
        local_errors = []
        if 'import funkin.modding.module.Module;' not in text: local_errors.append('missing Module import')
        if 'import funkin.play.PlayState;' not in text: local_errors.append('missing PlayState import')
        if not re.search(r'class\s+\w+\s+extends\s+Module', text): local_errors.append('no Module subclass')
        if 'onCountdownStart' not in text and 'onSongStart' not in text: warnings.append(f'{script.name}: no known lifecycle hook')
        if local_errors: errors.extend(f'HScript {script.name}: {item}' for item in local_errors)
        script_reports.append({'file': str(script.relative_to(mod_path)), 'status': 'PASS' if not local_errors else 'ERROR', 'errors': local_errors})
    status = 'PASS' if not errors else 'ERROR'
    return {'mod': mod_path.name, 'song': song, 'status': status, 'errors': errors, 'warnings': warnings, 'metadata': {'version': metadata.get('version'), 'characters': chars, 'stage': stage_id, 'noteStyle': style_id, 'album': album_id, 'difficulties': difficulties}, 'characters': char_reports, 'stage': stage_report, 'noteStyle': style_report, 'level': level_report, 'album': {'file': str(album_path.relative_to(mod_path)) if album_path else None, 'errors': album_errors}, 'scripts': script_reports}


def main() -> int:
    mods = sorted(path for path in MODS.glob('esperon-dano-*') if path.is_dir())
    with ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 2)) as pool:
        futures = [pool.submit(inspect_mod, path) for path in mods]
        reports = [future.result() for future in as_completed(futures)]
    reports.sort(key=lambda item: item.get('mod', ''))
    payload = {'audit': 'RUNTIME_CODE_CONTRACTS_V220', 'target': 'FNF Mobile V-Slice 0.8.6', 'parallel': True, 'mod_count': len(reports), 'passed': sum(item['status'] == 'PASS' for item in reports), 'errors': sum(item['status'] == 'ERROR' for item in reports), 'warnings': sum(len(item['warnings']) for item in reports), 'reports': reports, 'status': 'PASS' if len(reports) == 20 and all(item['status'] == 'PASS' for item in reports) else 'ERRORS_FOUND'}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ('status', 'mod_count', 'passed', 'errors', 'warnings')}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
