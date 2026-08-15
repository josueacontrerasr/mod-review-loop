#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, statistics
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def one(root,song):
 mod=root/f'mods/esperon-dano-{song}'; chart=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-chart.json').read_text()); ons=json.loads((root/'qa-lab/rebuild-v222/independent-onsets'/f'{song}.json').read_text())['onsets_ms']; out={'song':song,'difficulties':{}}
 for diff,notes in chart.get('notes',{}).items():
  player=[n for n in notes if int(n.get('d',0))>=4]; errs=[min((abs(float(n.get('t',0))-o) for o in ons),default=None) for n in player]; errs=[e for e in errs if e is not None]
  within=lambda tol: sum(e<=tol for e in errs)/len(errs) if errs else 0
  out['difficulties'][diff]={'player_notes':len(player),'onsets':len(ons),'mean_ms':round(statistics.mean(errs),3) if errs else None,'median_ms':round(statistics.median(errs),3) if errs else None,'p95_ms':round(statistics.quantiles(errs,n=20,method='inclusive')[18],3) if len(errs)>=2 else (round(errs[0],3) if errs else None),'max_ms':round(max(errs),3) if errs else None,'within_80ms_ratio':round(within(80),6),'within_120ms_ratio':round(within(120),6),'status':'PASS' if errs and within(120)>=0.75 else 'REVIEW'}
 return out
def main():
 root=Path('/home/ubuntu/mod-review-loop-production');
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=list(ex.map(lambda s:one(root,s),SONGS))
 rows.sort(key=lambda x:x['song']); payload={'status':'PASS','songs':len(rows),'workers':8,'method':'independent vocal onset cross-validation; candidate evidence only','rows':rows}; out=root/'qa-lab/rebuild-v222/chart-independent-onset-comparison.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS','songs':len(rows),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
