#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 rows=[]; issues=[]
 for song in SONGS:
  mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); prod=sd/f'{song}-chart.json'; cand=ROOT/'qa-lab/rebuild-v250/voice-priority-candidates-v251'/song/f'{song}-chart-v251.json'; meta=json.loads((sd/f'{song}-metadata.json').read_text()); audio=mod/'songs'/song
  row={'song':song,'status':'PASS','issues':[],'production_chart_sha256':sha(prod),'candidate_chart_sha256':sha(cand),'inst_sha256':sha(audio/'Inst.ogg'),'voice_shas':{p.name:sha(p) for p in sorted(audio.glob('Voices-*.ogg'))}}
  if row['production_chart_sha256']!=row['candidate_chart_sha256']: row['issues'].append('candidate_mismatch')
  chart=json.loads(prod.read_text()); counts={}
  for d in ('easy','normal','hard'):
   arr=chart.get('notes',{}).get(d,[]); counts[d]=len(arr); keys=[(float(n.get('t',-1)),int(n.get('d',-1))) for n in arr]
   if keys!=sorted(keys) or len(keys)!=len(set(keys)): row['issues'].append(f'order_duplicate_{d}')
   if any(t<0 or d0<0 or d0>3 for t,d0 in keys): row['issues'].append(f'lane_domain_{d}')
  if not (counts['easy']<counts['normal']<counts['hard']): row['issues'].append('density_order')
  row['counts']=counts; row['timeChanges']=meta.get('timeChanges',[])
  if row['issues']:
   row['status']='ERROR'; issues.extend(f'{song}:{x}' for x in row['issues'])
  rows.append(row)
 payload={'version':'2.5.1-promoted-voice-priority','status':'PASS' if not issues else 'ERRORS_FOUND','songs':20,'difficulties':60,'rows':rows,'issues':issues}
 out=ROOT/'qa-lab/rebuild-v250/promoted-voice-priority-gate-v251.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':20,'issues':len(issues),'output':str(out)},ensure_ascii=False)); return 0 if not issues else 1
if __name__=='__main__':raise SystemExit(main())
