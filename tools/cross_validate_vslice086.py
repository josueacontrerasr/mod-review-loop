#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path('/home/ubuntu/mod-review-loop-production')
TASKS = {
    'zip_install_layout': ['python3', 'tools/validate_zip_install_layout.py'],
    'official_reference_comparison': ['python3', 'tools/audit_zip_structure.py', '.', '--reference', '/home/ubuntu/upload/v-slice_yo_la_conoci_en_un_taxi.zip', '--reference', '/home/ubuntu/upload/tse_disable_shader_v25.zip', '--reference', '/home/ubuntu/upload/its-been-so-long.zip', '--delivery-dir', 'Mods .zip terminados'],
    'sync_ui_static': ['python3', 'tools/validate_sync_ui_v2.py', '.'],
}


def run(name: str, command: list[str]) -> dict:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
    return {
        'name': name,
        'command': command,
        'returncode': completed.returncode,
        'stdout': completed.stdout[-12000:],
        'stderr': completed.stderr[-12000:],
        'status': 'PASS' if completed.returncode == 0 else 'ERROR',
    }


def main() -> int:
    results = []
    with ThreadPoolExecutor(max_workers=len(TASKS)) as executor:
        futures = {executor.submit(run, name, command): name for name, command in TASKS.items()}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item['name'])
    payload = {
        'audit': 'CROSS_VALIDATION_VSLICE_086',
        'parallel': True,
        'status': 'PASS' if all(item['status'] == 'PASS' for item in results) else 'ERRORS_FOUND',
        'results': results,
    }
    output = ROOT / 'qa-lab/rebuild-v220/cross-validation-vslice086.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': payload['status'], 'checks': len(results), 'passed': sum(item['status'] == 'PASS' for item in results)}, ensure_ascii=False))
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
