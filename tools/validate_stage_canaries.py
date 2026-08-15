#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); canary=root/'qa-lab/rebuild-v222/canaries'; rows=[]
    for stage_path in sorted(canary.glob('*/*/*.json')):
        if stage_path.name=='variant-manifest.json': continue
        d=json.loads(stage_path.read_text()); song=stage_path.parts[-3]; variant=stage_path.parts[-2]; stage_id=stage_path.stem; asset=d['props'][0]['assetPath']; source=root/f'mods/esperon-dano-{song}/shared/images/{asset}.png'; issues=[]
        if d.get('version') not in ('1.0.0','1.0.1','1.0.2'): issues.append('unsupported_stage_version')
        if asset.startswith('shared:'): issues.append('assetPath_uses_shared_prefix')
        if not source.is_file(): issues.append('relative_asset_missing')
        for k in ('name','cameraZoom','props'):
            if k not in d: issues.append('missing_'+k)
        prop=d['props'][0]
        for k in ('name','assetPath','position','scale','scroll','zIndex','alpha','animType','animations'):
            if k not in prop: issues.append('missing_prop_'+k)
        if variant.endswith('with-characters'):
            for char in ('bf','dad','gf'):
                if char not in d.get('characters',{}): issues.append('missing_character_'+char)
        rows.append({'song':song,'variant':variant,'stage':stage_id,'assetPath':asset,'source_asset':str(source.relative_to(root)),'source_exists':source.is_file(),'characters':sorted(d.get('characters',{})),'issues':issues,'status':'PASS' if not issues else 'ERROR'})
    payload={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','variants':len(rows),'rows':rows,'runtime_limit':'Static contract/resolution check only; no native Haxe runtime available.'}; out=root/'qa-lab/rebuild-v222/stage-canary-validation.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'variants':len(rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
