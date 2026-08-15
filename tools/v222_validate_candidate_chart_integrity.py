#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def main():
 root=Path('/home/ubuntu/mod-review-loop-production'); rows=[]
 for s in SONGS:
  p=root/'qa-lab/rebuild-v222/candidate-charts'/s/f'{s}-chart-candidate.json'; d=json.loads(p.read_text()); issues=[]
  for diff,notes in d.get('notes',{}).items():
   keys=[(round(float(n.get('t',-1)),3),int(n.get('d',-1))) for n in notes];
   if keys!=sorted(keys): issues.append(diff+':not_sorted')
   if len(keys)!=len(set(keys)): issues.append(diff+':duplicate_time_direction')
   if any(n.get('t',-1)<0 or n.get('d',-1)<0 or n.get('d',-1)>7 for n in notes): issues.append(diff+':invalid_note')
   if any(n.get('l',0)<0 for n in notes): issues.append(diff+':invalid_hold')
  rows.append({'song':s,'issues':issues,'status':'PASS' if not issues else 'ERROR'})
 payload={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','songs':len(rows),'rows':rows,'candidate_only':True}; out=root/'qa-lab/rebuild-v222/candidate-integrity.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'errors':sum(r['status']!='PASS' for r in rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
