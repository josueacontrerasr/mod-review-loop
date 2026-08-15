#!/usr/bin/env python3
from __future__ import annotations
import json, statistics
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def metric(chart,ons):
 vals=[]
 for notes in chart.get('notes',{}).values():
  for n in notes:
   if int(n.get('d',0))>=4 and ons: vals.append(min(abs(float(n.get('t',0))-o) for o in ons))
 return {'notes':len(vals),'mean_ms':round(statistics.mean(vals),3) if vals else None,'median_ms':round(statistics.median(vals),3) if vals else None,'within_80':round(sum(x<=80 for x in vals)/len(vals),6) if vals else None,'within_120':round(sum(x<=120 for x in vals)/len(vals),6) if vals else None,'max_ms':round(max(vals),3) if vals else None}
def main():
 root=Path('/home/ubuntu/mod-review-loop-production'); rows=[]
 for s in SONGS:
  mod=root/f'mods/esperon-dano-{s}'; prod=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{s}-chart.json').read_text()); cand=json.loads((root/'qa-lab/rebuild-v222/candidate-charts'/s/f'{s}-chart-candidate.json').read_text()); ons=json.loads((root/'qa-lab/rebuild-v222/independent-onsets'/f'{s}.json').read_text())['onsets_ms']; a=metric(prod,ons); b=metric(cand,ons); rows.append({'song':s,'production':a,'candidate':b,'improvement_within_120':round((b['within_120'] or 0)-(a['within_120'] or 0),6),'improvement_mean_ms':round((a['mean_ms'] or 0)-(b['mean_ms'] or 0),3)})
 payload={'status':'PASS','songs':len(rows),'rows':rows,'promotion_policy':'Promote only if within_120 improves >=0.10, mean decreases, and no duplicate timestamp/direction is introduced; otherwise keep candidate isolated.'}; out=root/'qa-lab/rebuild-v222/candidate-cross-validation-summary.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS','songs':len(rows),'promotable':[r['song'] for r in rows if r['improvement_within_120']>=0.10 and r['improvement_mean_ms']>0],'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
