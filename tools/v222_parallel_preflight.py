#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, os, re
from pathlib import Path
import xml.etree.ElementTree as ET

SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def json_load(p): return json.loads(p.read_text(encoding='utf-8'))
def resolve_asset(mod, asset):
    if not isinstance(asset,str): return []
    if asset.startswith('shared:'):
        base=mod/'shared/images'/asset.removeprefix('shared:')
    else: base=mod/'images'/asset
    return [str(p.relative_to(mod)) for p in (base,Path(str(base)+'.png'),Path(str(base)+'.xml'),Path(str(base)+'.astc')) if p.is_file()]
def atlas_info(mod, base):
    resolved=resolve_asset(mod,base); out={'asset':base,'resolved':resolved,'frames':[],'imagePath':None,'xml':None}
    for rel in resolved:
        if rel.endswith('.xml'):
            try:
                root=ET.parse(mod/rel).getroot(); frames=[s.attrib.get('name','') for s in root.findall('.//SubTexture')]
                out.update({'xml':rel,'frames':frames,'imagePath':root.attrib.get('imagePath')})
            except Exception as e: out['xml_error']=str(e)
    return out

def one(root,song):
    mod=root/f'mods/esperon-dano-{song}'; songdir=mod/f'data/songs/{song}'; meta=json_load(songdir/f'{song}-metadata.json'); chart=json_load(songdir/f'{song}-chart.json'); stage_id=meta.get('playData',{}).get('stage'); stage_path=mod/f'data/stages/{stage_id}.json'; stage=json_load(stage_path) if stage_path.is_file() else None; style_id=meta.get('playData',{}).get('noteStyle'); style_path=mod/f'data/notestyles/{style_id}.json'; style=json_load(style_path) if style_path.is_file() else None
    stages=[]
    if stage:
        for prop in stage.get('props',[]):
            a=prop.get('assetPath'); ai=atlas_info(mod,a); stages.append({'assetPath':a,'resolved':ai['resolved'],'xml':ai.get('xml'),'frames':len(ai.get('frames',[])),'props_keys':sorted(prop.keys())})
    note_assets=[]
    if style:
        for group,data in style.get('assets',{}).items():
            if isinstance(data,dict) and isinstance(data.get('assetPath'),str):
                ai=atlas_info(mod,data['assetPath']); note_assets.append({'group':group,'assetPath':data['assetPath'],'resolved':ai['resolved'],'frames':len(ai.get('frames',[])),'prefixes':sorted({x.split('0000')[0] for x in ai.get('frames',[]) if x})[:80]})
    notes={d:{'count':len(ns),'first':ns[0].get('t') if ns else None,'last':ns[-1].get('t') if ns else None,'directions':sorted(set(n.get('d') for n in ns))} for d,ns in chart.get('notes',{}).items()}
    audio_files=sorted(str(p.relative_to(mod)) for p in (mod/f'songs/{song}').glob('*.ogg'))
    chars=meta.get('playData',{}).get('characters',{})
    return {'song':song,'mod':mod.name,'metadata_stage':stage_id,'stage_file':str(stage_path.relative_to(mod)) if stage_path.is_file() else None,'stage_version':stage.get('version') if stage else None,'stage_keys':sorted(stage.keys()) if stage else [],'stages':stages,'noteStyle':style_id,'noteStyle_version':style.get('version') if style else None,'note_assets':note_assets,'chart_version':chart.get('version'),'notes':notes,'characters':chars,'audio_files':audio_files}

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); root.joinpath('qa-lab/rebuild-v222').mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8,len(SONGS))) as ex: rows=list(ex.map(lambda s:one(root,s),SONGS))
    rows.sort(key=lambda x:x['song']); payload={'status':'PASS','songs':len(rows),'workers':min(8,len(SONGS)),'rows':rows,'scope':'read-only-preflight'}; out=root/'qa-lab/rebuild-v222/preflight-v222.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'workers':payload['workers'],'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
