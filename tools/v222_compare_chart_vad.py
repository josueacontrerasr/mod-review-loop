#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, statistics
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def one(root,song):
 mod=root/f'mods/esperon-dano-{song}'; chart=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-chart.json').read_text()); vad=json.loads((root/'qa-lab/rebuild-v222/vad'/f'{song}.json').read_text()); ons=vad['onsets_ms']; segs=vad['segments']; out={'song':song,'difficulties':{}}
 for diff,notes in chart.get('notes',{}).items():
  player=[n for n in notes if int(n.get('d',0))>=4]; errors=[]; inside=0
  for n in player:
   t=float(n.get('t',0)); e=min((abs(t-o) for o in ons),default=None); errors.append(e) if e is not None else None
   if any(s['start_ms']-80<=t<=s['end_ms']+80 for s in segs): inside+=1
  errors=[x for x in errors if x is not None];
  q=lambda p: (statistics.quantiles(errors,n=100,method='inclusive')[p-1] if len(errors)>=2 else (errors[0] if errors else None))
  out['difficulties'][diff]={'player_notes':len(player),'nearest_onset_mean_ms':round(statistics.mean(errors),3) if errors else None,'nearest_onset_median_ms':round(statistics.median(errors),3) if errors else None,'nearest_onset_p95_ms':round(q(95),3) if errors else None,'nearest_onset_max_ms':round(max(errors),3) if errors else None,'within_80ms_ratio':round(sum(x<=80 for x in errors)/len(errors),6) if errors else None,'inside_vocal_segment_ratio':round(inside/len(player),6) if player else None,'status':'PASS' if errors and sum(x<=120 for x in errors)/len(errors)>=0.75 else 'REVIEW'}
 return out

def main():
 root=Path('/home/ubuntu/mod-review-loop-production');
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=list(ex.map(lambda s:one(root,s),SONGS))
 rows.sort(key=lambda x:x['song']); payload={'status':'PASS','songs':len(rows),'workers':8,'method':'nearest VAD onset plus segment overlap; candidate evidence only','rows':rows}; out=root/'qa-lab/rebuild-v222/chart-vad-comparison.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
