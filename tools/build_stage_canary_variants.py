#!/usr/bin/env python3
from __future__ import annotations
import json, shutil
from pathlib import Path

SONGS=['solare','dano']
def load(p): return json.loads(p.read_text())
def save(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); out=root/'qa-lab/rebuild-v222/canaries';
    if out.exists(): shutil.rmtree(out)
    for song in SONGS:
        mod=root/f'mods/esperon-dano-{song}'; stage_id=f'escenario-{song}'; src=mod/f'data/stages/{stage_id}.json'; original=load(src)
        base=dict(original); base['version']='1.0.1'; base['name']=f'Escenario {song.title()}'; base['props']=[dict(original['props'][0],name='stageBack',assetPath=f'stages/{stage_id}',isPixel=False,flipX=False,flipY=False,angle=0.0,blend='',color='#FFFFFF',danceEvery=0,animations=[],startingAnimation=None,animType='sparrow')]
        for variant, data in [('relative-path-only',base),('relative-path-with-characters',dict(base))]:
            data=json.loads(json.dumps(data))
            if variant.endswith('with-characters'):
                data['characters']={'bf':{'zIndex':300,'position':[900,560],'scale':1.0,'cameraOffsets':[-100,-100],'scroll':[1,1]},'dad':{'zIndex':200,'position':[260,560],'scale':1.0,'cameraOffsets':[100,-100],'scroll':[1,1]},'gf':{'zIndex':100,'position':[640,500],'scale':1.0,'cameraOffsets':[0,0],'scroll':[1,1]}}
            save(out/song/variant/f'{stage_id}.json',data)
            shutil.copy2(mod/f'shared/images/stages/{stage_id}.png',out/song/variant/f'{stage_id}.png')
            save(out/song/variant/'variant-manifest.json',{'song':song,'variant':variant,'source_stage':str(src.relative_to(root)),'assetPath':f'stages/{stage_id}','default_directory':'shared','runtime_note':'Canary only; not an installable mod.'})
    print(json.dumps({'status':'PASS','songs':len(SONGS),'variants':len(SONGS)*2,'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
