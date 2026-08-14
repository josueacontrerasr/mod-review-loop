#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

def distances(times, refs):
    if not times or not refs: return []
    r=np.asarray(sorted(refs),dtype=float); out=[]
    for t in times:
        i=int(np.searchsorted(r,t)); i=min(max(i,0),len(r)-1); j=max(0,i-1); out.append(float(min(abs(t-r[i]),abs(t-r[j]))))
    return out

def summary(ds):
    if not ds: return {'match120_pct':None,'median_ms':None,'p90_ms':None,'max_ms':None}
    a=np.asarray(ds,dtype=float); return {'match120_pct':round(float(np.mean(a<=120)*100),3),'median_ms':round(float(np.median(a)),3),'p90_ms':round(float(np.percentile(a,90)),3),'max_ms':round(float(np.max(a)),3)}

def main():
    root=Path(' /home/ubuntu/mod-review-loop-production'.strip()); rows=[]
    for activity in sorted((root/'sync-candidates/vocal-activity').glob('*.json')):
        song=activity.stem; ev=json.loads(activity.read_text()); refs=ev['candidate_vocal_onsets_ms']; mod=root/f'mods/esperon-dano-{song}'
        songdir=next((mod/'data/songs').iterdir()); prod=json.loads((songdir/f'{song}-chart.json').read_text())['notes']['normal']; cand=json.loads((root/f'sync-candidates/voice-aligned-charts/{song}/{song}-chart.json').read_text())['notes']['normal']
        prod_times=[float(n['t']) for n in prod]; cand_times=[float(n['t']) for n in cand]
        rows.append({'song':song,'independent_onsets':len(refs),'production_notes':len(prod_times),'candidate_notes':len(cand_times),'production':summary(distances(prod_times,refs)),'candidate':summary(distances(cand_times,refs))})
    payload={'status':'PASS' if len(rows)==20 else 'ERRORS_FOUND','songs':len(rows),'detector':'analyze_vocal_activity.py','rows':rows,'limitations':['Onsets independientes siguen siendo candidatos y no identifican sílabas/personajes.','No sustituye Audio Sync Test ni playtest móvil.','No se modificó producción.']}
    out=root/'qa-lab/rebuild-v221/cross-validation-candidate-summary.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
