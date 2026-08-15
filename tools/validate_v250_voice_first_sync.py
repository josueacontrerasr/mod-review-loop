#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def main():
    voice=json.loads((ROOT/'qa-lab/rebuild-v250/voice-first-v250.json').read_text())
    promo=json.loads((ROOT/'qa-lab/rebuild-v250/voice-first-promotion-v250.json').read_text())
    issues=[]; rows=[]
    for song in SONGS:
        vr=next(r for r in voice['rows'] if r['song']==song); pr=next(r for r in promo['rows'] if r['song']==song)
        row={'song':song,'status':'PASS','issues':[]}
        if pr['lane_domain'] != [0,1,2,3]: row['issues'].append('lane_domain')
        if pr['audio']['inst_sha256'] != vr['inst_sha256']: row['issues'].append('inst_hash_mismatch')
        if not pr['audio']['voice_shas']: row['issues'].append('voice_hash_missing')
        for diff in ('easy','normal','hard'):
            m=vr['difficulties'][diff]['metrics']; b=vr['difficulties'][diff]['build']
            if m['player_lane_notes'] != m['notes']: row['issues'].append(f'{diff}_non_player_notes')
            min_voice={'easy':0.85,'normal':0.80,'hard':0.75}[diff]
            if m['voice_within_120ms'] < min_voice: row['issues'].append(f'{diff}_voice_coverage')
            if m['first_10s'] <= 0: row['issues'].append(f'{diff}_no_early_notes')
            if b['vocal_events_used'] <= 0: row['issues'].append(f'{diff}_no_vocal_events')
        counts=pr['notes']
        if not (counts['easy'] < counts['normal'] < counts['hard']): row['issues'].append('density_order')
        if row['issues']: row['status']='ERROR'; issues.extend(f"{song}:{x}" for x in row['issues'])
        rows.append(row)
    payload={'version':'2.5.0','status':'PASS' if not issues else 'ERRORS_FOUND','songs':20,'difficulties':60,'method':'vocal-first onset consensus with instrumental accents; official player lanes 0-3','rows':rows,'issues':issues}
    out=ROOT/'qa-lab/rebuild-v250/voice-first-sync-validation-v250.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'songs':20,'errors':len(issues),'output':str(out)},ensure_ascii=False)); return 0 if not issues else 1
if __name__=='__main__': raise SystemExit(main())
