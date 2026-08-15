#!/usr/bin/env python3
"""Verificación final determinista de V-Slice 0.8.6 y resolución de assets."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    entries = []
    for mod in sorted((root / 'mods').glob('esperon-dano-*')):
        if not mod.is_dir():
            continue
        problems = []
        meta_path = mod / '_polymod_meta.json'
        meta = load(meta_path)
        api = meta.get('api_version') or meta.get('apiVersion')
        if api != '0.8.6':
            problems.append({'code': 'API_VERSION', 'detail': f'api_version={api!r}'})
        songs = list((mod / 'data' / 'songs').glob('*'))
        song = songs[0].name if len(songs) == 1 else None
        metadata_path = mod / 'data' / 'songs' / str(song) / f'{song}-metadata.json'
        chart_path = mod / 'data' / 'songs' / str(song) / f'{song}-chart.json'
        manifest_path = mod / 'data' / 'songs' / str(song) / 'manifest.json'
        metadata = load(metadata_path)
        chart = load(chart_path)
        if not manifest_path.is_file():
            problems.append({'code': 'SONG_MANIFEST', 'detail': str(manifest_path.relative_to(mod))})
        if metadata.get('version') != '2.2.4':
            problems.append({'code': 'METADATA_SCHEMA', 'detail': str(metadata.get('version'))})
        if chart.get('version') != '2.0.0':
            problems.append({'code': 'CHART_SCHEMA', 'detail': str(chart.get('version'))})
        char_jsons = sorted((mod / 'data' / 'characters').glob('*.json'))
        stage_jsons = sorted((mod / 'data' / 'stages').glob('*.json'))
        for resource in char_jsons + stage_jsons:
            data = load(resource)
            asset_path = data.get('assetPath') or data.get('asset_path')
            if asset_path:
                normalized_path = str(asset_path).removeprefix('shared:')
                explicit_shared = str(asset_path).startswith('shared:')
                stage_shared = resource.parent.name == 'stages' and data.get('directory') == 'shared'
                character_shared = resource.parent.name == 'characters' and (mod / 'shared' / 'images' / f'{normalized_path}.png').is_file()
                image_root = mod / 'shared' / 'images' if (explicit_shared or stage_shared or character_shared) else mod / 'images'
                candidate_png = image_root / f'{normalized_path}.png'
                candidate_xml = image_root / f'{normalized_path}.xml'
                if not candidate_png.is_file() or not candidate_xml.is_file():
                    problems.append({'code': 'ASSET_RESOLUTION', 'detail': f'{resource.relative_to(mod)} -> {asset_path}'})
        # Freeplay-facing static assets: mod icon and character icons must resolve. A dedicated Freeplay cover contract is not assumed.
        mod_icon = mod / '_polymod_icon.png'
        icons = sorted((mod / 'images' / 'icons').glob('*.png'))
        cover_candidates = [p for p in mod.rglob('*.png') if any(token in p.name.lower() for token in ('cover', 'album', 'freeplay', 'icon'))]
        # _polymod_icon.png is optional in V-Slice; record it as coverage, not as a Freeplay loading error.
        if len(icons) < 2:
            problems.append({'code': 'CHARACTER_ICONS', 'detail': f'{len(icons)} iconos'})
        entries.append({
            'mod': mod.name, 'song': song, 'api_version': api, 'metadata_version': metadata.get('version'), 'chart_version': chart.get('version'),
            'characters': len(char_jsons), 'stages': len(stage_jsons), 'mod_icon': mod_icon.is_file(), 'character_icons': len(icons),
            'freeplay_cover_candidates': [p.relative_to(mod).as_posix() for p in cover_candidates],
            'status': 'PASS' if not problems else 'ERROR', 'problems': problems
        })
    payload = {
        'scope': 'FINAL_VSLICE_086_STATIC_VERIFY', 'mods': len(entries), 'passed': sum(e['status'] == 'PASS' for e in entries),
        'status': 'PASS' if all(e['status'] == 'PASS' for e in entries) else 'ERROR',
        'freeplay_note': 'Se verifican iconos y assets estáticos que el mod declara. La apariencia exacta de la tarjeta/lista Freeplay requiere renderer del motor.',
        'entries': entries
    }
    out = root / 'qa-lab' / 'session-30min' / 'final-vslice-086-static.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: payload[k] for k in ('mods', 'passed', 'status')}, ensure_ascii=False))
    raise SystemExit(0 if payload['status'] == 'PASS' else 1)

if __name__ == '__main__':
    main()
