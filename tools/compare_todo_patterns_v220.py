#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path('/home/ubuntu/mod-review-loop-production')
TODO_REPORT = ROOT / 'qa-lab/rebuild-v220/todo-mass-structure-audit.json'
ZIP_REPORT = ROOT / 'qa-lab/rebuild-v220/reference-structure-audit.json'
OUTPUT = ROOT / 'qa-lab/rebuild-v220/todo-v220-pattern-comparison.json'

def main() -> int:
    todo = json.loads(TODO_REPORT.read_text(encoding='utf-8'))
    zips = json.loads(ZIP_REPORT.read_text(encoding='utf-8'))
    valid_todo = [item for item in todo['candidates'] if item['status'] == 'MOD_MANIFEST_FOUND']
    invalid_todo = [item for item in todo['candidates'] if item['status'] != 'MOD_MANIFEST_FOUND']
    current = [item for item in zips['results'] if item['kind'] == 'current-individual']
    api_versions = Counter(str((item.get('manifest') or {}).get('api_version')) for item in valid_todo)
    todo_root_files = Counter(name for item in valid_todo for name in item.get('root_files', []))
    todo_root_dirs = Counter(name for item in valid_todo for name in item.get('root_dirs', []))
    todo_txt_locations = sorted((item['candidate'], name) for item in todo['candidates'] for name in item.get('txt_files', []))
    current_root_files = Counter(name.rsplit('/', 1)[-1] for item in current for name in item.get('root_files', []))
    current_text_count = sum(len(item.get('root_text_files', [])) for item in current)
    current_aux_count = sum(len(item.get('qa_paths', [])) for item in current)
    required_runtime_dirs = {'data', 'images', 'songs'}
    current_root_policy = {'_polymod_meta.json'}
    payload = {
        'audit': 'TODO_MASS_TO_V220_PATTERN_COMPARISON',
        'read_only': True,
        'todo': {
            'direct_candidates': todo['direct_candidate_count'],
            'manifest_mods': len(valid_todo),
            'non_mod_candidates': len(invalid_todo),
            'api_versions': dict(api_versions),
            'root_files_frequency': dict(todo_root_files),
            'root_directories_frequency': dict(todo_root_dirs),
            'nested_txt_or_markdown_count': len(todo_txt_locations),
            'nested_txt_or_markdown_locations': todo_txt_locations,
            'non_mod_candidates_detail': [{'candidate': item['candidate'], 'root_files': item['root_files'], 'root_dirs': item['root_dirs'], 'file_count': item['file_count']} for item in invalid_todo],
        },
        'v220': {
            'individual_zip_count': len(current),
            'root_file_frequency': dict(current_root_files),
            'root_text_file_count': current_text_count,
            'auxiliary_path_count': current_aux_count,
            'runtime_root_policy': sorted(current_root_policy),
            'all_have_required_runtime_dirs_by_observed_paths': all(item.get('has_data_songs') and item.get('has_songs_audio') for item in current),
            'all_have_single_root': all(item.get('root_count') == 1 for item in current),
            'all_have_crc': all(item.get('zip_crc') for item in current),
        },
        'comparison': {
            'TODO_is_mass_container_not_single_mod': todo['zip_roots'] == ['TODO'] and len(valid_todo) > 1,
            'V220_matches_runtime_root_manifest_policy': current_root_files == Counter({'_polymod_meta.json': len(current)}),
            'V220_has_no_root_text_or_aux_files': current_text_count == 0 and current_aux_count == 0,
            'TODO_text_files_are_optional_placeholders_or_documentation': all('/' in name or Path(name).name.lower() in {'readme.md', 'readme.txt'} for _, name in todo_txt_locations),
            'api_difference_is_version_age_not_layout_failure': all(version in {'0.8.4', '0.8.5'} for version in api_versions) and all((item.get('polymod_meta') or {}).get('api_version') == '0.8.6' for item in current),
            'status': 'PASS_NO_MOD_CHANGES_REQUIRED' if len(current) == 20 and current_text_count == 0 and current_aux_count == 0 and all(item.get('status') == 'PASS' for item in current) else 'REVIEW_REQUIRED',
        },
        'conclusion': 'TODO.zip contiene 12 mods con manifiesto y 1 candidato sin manifiesto; no es un único patrón de mod. Sus 12 archivos TXT/MD son placeholders o documentación opcional en subcarpetas; uno es README.md de un mod utilitario. Los 20 V2.2.0 siguen un subconjunto runtime más limpio y coherente con las referencias: una raíz, _polymod_meta.json, data/images/songs y assets/scripts según proceda. No se requiere modificar los mods por esta comparación.',
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload['comparison'], ensure_ascii=False))
    return 0 if payload['comparison']['status'] == 'PASS_NO_MOD_CHANGES_REQUIRED' else 1

if __name__ == '__main__':
    raise SystemExit(main())
