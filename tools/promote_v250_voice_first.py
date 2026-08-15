#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def one(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'
    sd=next((mod/'data/songs').iterdir())
    prod=sd/f'{song}-chart.json'
    candidate=ROOT/'qa-lab/rebuild-v250/voice-first-candidates'/song/f'{song}-chart-v250.json'
    backup=ROOT/'qa-lab/rebuild-v250/production-charts-before'/f'{song}-chart-v240.json'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists(): shutil.copy2(prod,backup)
    before=json.loads(prod.read_text(encoding='utf-8'))
    after=json.loads(candidate.read_text(encoding='utf-8'))
    if set(after.get('notes',{})) != {'easy','normal','hard'}: raise ValueError(f'{song}:difficulty_set')
    for diff in ('easy','normal','hard'):
        notes=after['notes'][diff]
        if not notes: raise ValueError(f'{song}:{diff}:empty')
        if any(int(n['d'])<0 or int(n['d'])>3 for n in notes): raise ValueError(f'{song}:{diff}:non_player_lane')
        keys=[(round(float(n['t']),3),int(n['d'])) for n in notes]
        if keys != sorted(keys) or len(keys)!=len(set(keys)): raise ValueError(f'{song}:{diff}:order_or_duplicate')
    if before.get('timeChanges') != after.get('timeChanges'): raise ValueError(f'{song}:timeChanges_changed')
    shutil.copy2(candidate,prod)
    audio=mod/'songs'/song
    return {'song':song,'status':'PASS','chart_before_sha256':sha(backup),'chart_after_sha256':sha(prod),'audio':{'inst_sha256':sha(audio/'Inst.ogg'),'voice_shas':{p.name:sha(p) for p in sorted(audio.glob('Voices-*.ogg'))}},'notes':{d:len(after['notes'][d]) for d in ('easy','normal','hard')},'lane_domain':sorted({int(n['d']) for d in ('easy','normal','hard') for n in after['notes'][d]})}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex: rows=sorted(ex.map(one,SONGS),key=lambda x:x['song'])
    payload={'version':'2.5.0','status':'PASS','songs':len(rows),'charts_promoted':len(rows),'audio_unchanged':True,'timeChanges_unchanged':True,'player_lane_contract':'all notes d=0..3','rows':rows}
    out=ROOT/'qa-lab/rebuild-v250/voice-first-promotion-v250.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','songs':len(rows),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
