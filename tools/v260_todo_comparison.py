#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'qa-lab/rebuild-v260/todo-reference'
EVID = ROOT / 'qa-lab/rebuild-v260'

def load_jsons(base: Path):
    out = []
    for p in base.rglob('*.json'):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            if isinstance(d, dict):
                out.append((p, d))
        except Exception:
            pass
    return out

def key_inventory(items):
    counts = Counter()
    def walk(value, prefix=''):
        if isinstance(value, dict):
            for key, child in value.items():
                name = f'{prefix}.{key}' if prefix else key
                counts[name] += 1
                walk(child, name)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            walk(value[0], prefix + '[]')
    for _, data in items:
        walk(data)
    return counts

def main():
    ref = load_jsons(REF)
    current = load_jsons(ROOT / 'mods')
    ref_keys = key_inventory(ref)
    cur_keys = key_inventory(current)
    ref_names = Counter(p.name for p, _ in ref)
    cur_names = Counter(p.name for p, _ in current)
    ref_top = Counter(p.parts[0] if p.parts else '' for p, _ in ref)
    cur_top = Counter(p.parts[1] if len(p.parts) > 1 else p.parts[0] for p, _ in current)
    suspicious = []
    for p in REF.rglob('*'):
        if p.is_file() and (p.suffix.lower() in {'.py', '.sh', '.bat', '.exe', '.dll', '.so'} or 'scripts' in p.parts):
            suspicious.append(str(p.relative_to(REF)))
    payload = {
        'version': '2.6.0-todo-comparison',
        'status': 'PASS',
        'reference': {
            'json_count': len(ref),
            'common_filenames': ref_names.most_common(30),
            'top_paths': ref_top.most_common(30),
            'suspicious_files': suspicious[:300],
        },
        'current': {
            'json_count': len(current),
            'common_filenames': cur_names.most_common(30),
            'top_paths': cur_top.most_common(30),
        },
        'key_differences': {
            'reference_only': sorted(set(ref_keys) - set(cur_keys))[:300],
            'current_only': sorted(set(cur_keys) - set(ref_keys))[:300],
            'reference_key_counts': ref_keys.most_common(200),
            'current_key_counts': cur_keys.most_common(200),
        },
        'interpretation': [
            'TODO.zip was inspected as reference data only.',
            'Scripts/binaries found in the reference are not executed or copied automatically.',
            'Differences are candidates for review, not automatic compatibility claims.',
        ],
    }
    out = EVID / 'todo-zip-comparison.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'reference_jsons': len(ref), 'current_jsons': len(current), 'suspicious_files': len(suspicious), 'output': str(out)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
