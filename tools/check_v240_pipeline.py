#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    errors=[]
    workflows=[ROOT/'.github/workflows/auto-evolucion.yml',ROOT/'.github/workflows/qa-lab-vslice.yml',ROOT/'.github/workflows/release-v240.yml']
    try:
        import yaml
        for p in workflows:
            yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as exc:
        errors.append(f'workflow_yaml:{exc}')
    for p in workflows:
        text=p.read_text(encoding='utf-8')
        if 'v230' in text or 'V2.3.0' in text or '2.3.0' in text:
            errors.append(f'stale_workflow_reference:{p.name}')
    ev=ROOT/'qa-lab/rebuild-v240'
    required=['freeplay-repair-v240.json','mixed-sync-v240.json','chart-promotion-v240.json','runtime-contract-v240.json','package-manifest-v240.json','zip-validation-v240.json','qa-20x20-v240.json','diagnose-freeplay-notes-v240.json']
    for name in required:
        p=ev/name
        if not p.is_file(): errors.append(f'missing_evidence:{name}'); continue
        try:
            d=json.loads(p.read_text(encoding='utf-8'))
            if d.get('status')!='PASS': errors.append(f'evidence_not_pass:{name}')
        except Exception as exc: errors.append(f'evidence_json:{name}:{exc}')
    delivery=ROOT/'Mods .zip terminados'
    files=sorted(p for p in delivery.iterdir() if p.is_file())
    zips=sorted(delivery.glob('*.zip'))
    if len(files)!=21 or len(zips)!=21: errors.append(f'delivery_count:files={len(files)},zips={len(zips)}')
    if any(p.suffix.lower()!='.zip' for p in files): errors.append('delivery_non_zip')
    individual=[p for p in zips if 'Coleccion' not in p.name]
    if len(individual)!=20: errors.append(f'individual_count:{len(individual)}')
    for p in individual:
        try:
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None: errors.append(f'crc:{p.name}')
                if any(part in n.split('/') for n in z.namelist() for part in ('qa-lab','reports','artifacts')): errors.append(f'evidence_inside:{p.name}')
        except Exception as exc: errors.append(f'zip_error:{p.name}:{exc}')
    print(json.dumps({'status':'PASS' if not errors else 'ERRORS_FOUND','errors':errors,'workflow_count':len(workflows),'evidence_count':len(required),'delivery_files':len(files),'individual_zips':len(individual)},ensure_ascii=False))
    return 0 if not errors else 1

if __name__=='__main__': raise SystemExit(main())
