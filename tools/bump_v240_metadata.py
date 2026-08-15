#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREFIX='esperon-dano-'
def main():
    rows=[]
    for mod in sorted((ROOT/'mods').glob(PREFIX+'*')):
        if not mod.is_dir(): continue
        path=mod/'_polymod_meta.json'
        data=json.loads(path.read_text(encoding='utf-8'))
        old=data.get('mod_version')
        data['mod_version']='2.4.0'
        desc=str(data.get('description',''))
        desc=desc.replace('V2.3.0','V2.4.0')
        if 'albumRoll' not in desc: desc += ' Freeplay albumRoll contract repair and mixed rhythm-vocal chart.'
        data['description']=desc
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        rows.append({'mod':mod.name,'old_version':old,'new_version':data['mod_version'],'api_version':data.get('api_version')})
    out={'version':'2.4.0-meta-bump','status':'PASS' if len(rows)==20 and all(r['api_version']=='0.8.6' for r in rows) else 'ERROR','mods':len(rows),'rows':rows}
    path=ROOT/'qa-lab/rebuild-v240/metadata-bump-v240.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'mods':len(rows),'output':str(path)},ensure_ascii=False))
if __name__=='__main__': main()
