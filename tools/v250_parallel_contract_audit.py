#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def load(p): return json.loads(p.read_text(encoding='utf-8'))

def asset_base(mod, asset):
    if asset.startswith('shared:'): return mod/'shared'/'images'/asset.removeprefix('shared:')
    if asset.startswith(('characters/','stages/','notes/','ui/')): return mod/'shared'/'images'/asset
    return mod/'images'/asset

def atlas(mod, asset):
    base=asset_base(mod,asset); png=base.with_suffix('.png'); xml=base.with_suffix('.xml')
    frames=[]; xml_error=None
    if xml.is_file():
        try: frames=[n.attrib for n in ET.parse(xml).getroot().findall('.//SubTexture')]
        except Exception as e: xml_error=str(e)
    visible=0; total=0
    if png.is_file():
        try:
            with Image.open(png).convert('RGBA') as im:
                alpha=im.getchannel('A'); total=im.width*im.height; visible=sum(1 for p in alpha.getdata() if p>8)
        except Exception: pass
    return {'assetPath':asset,'resolved':str(base.relative_to(mod)),'png':png.is_file(),'xml':xml.is_file(),'xml_error':xml_error,'frame_names':[x.get('name','') for x in frames],'frame_sizes':[[x.get('width'),x.get('height')] for x in frames],'visible_alpha_ratio':round(visible/total,6) if total else 0.0}

def one(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'; issues=[]
    song_dir=next((mod/'data/songs').iterdir()); meta=load(song_dir/f'{song}-metadata.json'); chart=load(song_dir/f'{song}-chart.json')
    style=load(mod/'data/notestyles'/f"{meta['playData']['noteStyle']}.json")
    note_atlas=atlas(mod,style['assets']['note']['assetPath']); strum_atlas=atlas(mod,style['assets']['noteStrumline']['assetPath'])
    dist={d:{'player_0_3':0,'opponent_4_7':0,'other':0} for d in ('easy','normal','hard')}
    times={d:[] for d in ('easy','normal','hard')}
    for diff, notes in chart['notes'].items():
        for n in notes:
            d=int(n['d']); times[diff].append(float(n['t']))
            if 0<=d<=3: dist[diff]['player_0_3']+=1
            elif 4<=d<=7: dist[diff]['opponent_4_7']+=1
            else: dist[diff]['other']+=1
    if any(dist[d]['player_0_3']==0 for d in dist): issues.append('no_player_notes_0_3')
    if any(dist[d]['opponent_4_7']>0 for d in dist): issues.append('notes_on_opponent_strumline_4_7')
    if not note_atlas['png'] or not note_atlas['xml'] or note_atlas['xml_error']: issues.append('note_atlas_resolution')
    if not strum_atlas['png'] or not strum_atlas['xml'] or strum_atlas['xml_error']: issues.append('strumline_atlas_resolution')
    if note_atlas['visible_alpha_ratio']<0.01: issues.append('note_atlas_transparent')
    if len(note_atlas['frame_names'])<4: issues.append('note_frames_incomplete')
    if len(strum_atlas['frame_names'])<12: issues.append('strumline_frames_incomplete')
    if style.get('fallback')!='funkin': issues.append('fallback_not_funkin')
    result={'song':song,'status':'PASS' if not issues else 'ERROR','issues':issues,'official_mapping':{'player':0,'opponent':1,'player_lanes':'0-3','opponent_lanes':'4-7'},'chart_distribution':dist,'first_ms':{k:min(v) if v else None for k,v in times.items()},'note_atlas':note_atlas,'strumline_atlas':strum_atlas,'metadata':{'player':meta['playData']['characters'].get('player'),'playerVocals':meta['playData']['characters'].get('playerVocals',[]),'noteStyle':meta['playData']['noteStyle']}}
    return result

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex: rows=sorted(ex.map(one,SONGS),key=lambda x:x['song'])
    payload={'version':'2.5.0-contract-audit','status':'PASS' if all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','songs':20,'parallel_workers':20,'official_source':'SongData.hx getStrumlineIndex/getMustHitNote','rows':rows}
    out=ROOT/'qa-lab/rebuild-v250'/'parallel-contract-audit-v250.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'errors':sum(r['status']!='PASS' for r in rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
