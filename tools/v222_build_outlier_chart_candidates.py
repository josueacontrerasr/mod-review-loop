#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def nearest(t,ons): return min(ons,key=lambda x:abs(float(t)-x)) if ons else None
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='.'); ap.add_argument('--songs',nargs='+',default=SONGS); ap.add_argument('--threshold',type=float,default=120); args=ap.parse_args(); root=Path(args.root).resolve(); rows=[]; outroot=root/'qa-lab/rebuild-v222/candidate-charts'
 for song in args.songs:
  mod=root/f'mods/esperon-dano-{song}'; songdir=next((mod/'data/songs').iterdir()); p=songdir/f'{song}-chart.json'; d=json.loads(p.read_text()); ons=json.loads((root/'qa-lab/rebuild-v222/independent-onsets'/f'{song}.json').read_text())['onsets_ms']; c=json.loads(json.dumps(d)); changed=0
  for diff,notes in c.get('notes',{}).items():
   used=set()
   for n in notes:
    if int(n.get('d',0))<4: continue
    t=float(n.get('t',0)); o=nearest(t,ons)
    if o is None or abs(t-o)<=args.threshold: continue
    key=(round(float(o),3),int(n.get('d',0)))
    if key in used: continue
    n['t']=round(float(o),3); used.add(key); changed+=1
  for diff,notes in c.get('notes',{}).items(): notes.sort(key=lambda n:(float(n.get('t',0)),int(n.get('d',0))))
  out=outroot/song/f'{song}-chart-candidate.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n'); rows.append({'song':song,'changed_notes':changed,'source_chart':str(p.relative_to(root)),'candidate':str(out.relative_to(root)),'threshold_ms':args.threshold})
 payload={'status':'CANDIDATE_ONLY','songs':len(rows),'rows':rows,'warning':'Not promoted; onset candidates require human Audio Sync Test.'}; report=root/'qa-lab/rebuild-v222/outlier-candidate-summary.json'; report.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'changed':sum(r['changed_notes'] for r in rows),'output':str(report)},ensure_ascii=False))
if __name__=='__main__': main()
