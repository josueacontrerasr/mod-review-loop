#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

DEFAULT_CHARACTERS={
    'bf': {'zIndex':300,'position':[900,560],'scale':1.0,'cameraOffsets':[-100,-100],'scroll':[1,1]},
    'dad': {'zIndex':200,'position':[260,560],'scale':1.0,'cameraOffsets':[100,-100],'scroll':[1,1]},
    'gf': {'zIndex':100,'position':[640,430],'scale':1.0,'cameraOffsets':[0,0],'scroll':[1,1]},
}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='.'); ap.add_argument('--songs',nargs='+',required=True); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); root=Path(args.root).resolve(); results=[]
    for song in args.songs:
        mod=root/f'mods/esperon-dano-{song}'; meta=json.loads((next((mod/'data/songs').iterdir())/f'{song}-metadata.json').read_text()); stage_id=meta['playData']['stage']; path=mod/f'data/stages/{stage_id}.json'; d=json.loads(path.read_text()); before=json.loads(json.dumps(d));
        if not d.get('props'): raise RuntimeError(f'{song}: stage sin props')
        prop=d['props'][0]; old=prop.get('assetPath'); prop['assetPath']=old.removeprefix('shared:'); prop['name']=prop.get('name') or 'stageBack'; prop.setdefault('isPixel',False); prop.setdefault('flipX',False); prop.setdefault('flipY',False); prop.setdefault('angle',0.0); prop.setdefault('blend',''); prop.setdefault('color','#FFFFFF'); prop.setdefault('danceEvery',0); prop.setdefault('animations',[]); prop.setdefault('startingAnimation',None); prop.setdefault('animType','sparrow'); d['directory']='shared'; d['characters']=json.loads(json.dumps(DEFAULT_CHARACTERS)); d['version']='1.0.1';
        changed=before!=d
        if args.apply and changed: path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
        results.append({'song':song,'stage':stage_id,'old_assetPath':old,'new_assetPath':prop['assetPath'],'changed':changed,'applied':args.apply and changed,'characters':sorted(d['characters']),'stage_file':str(path.relative_to(root))})
    out=root/'qa-lab/rebuild-v222/stage-contract-repair.json'; out.parent.mkdir(parents=True,exist_ok=True); payload={'status':'APPLIED' if args.apply else 'DRY_RUN','results':results,'official_basis':['StageData.hx v0.8.6: stage directory defaults to shared; StageDataProp assetPath is a path string.','Official modding docs: image assetPath is relative to the mod images library and a stage can declare characters/props.']}; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(results),'changed':sum(r['changed'] for r in results),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
