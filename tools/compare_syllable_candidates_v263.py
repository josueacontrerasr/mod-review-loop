#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as futures
import json
from pathlib import Path
import librosa
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'qa-lab/rebuild-v263/playstate-fix/syllable-candidates'
DIFFS=('easy','normal','hard')

def nearest_error(x, values):
    if not values: return None
    return min(abs(float(x)-float(v)) for v in values)

def analyze(d: Path):
    align=json.loads((d/'syllable-alignment.json').read_text())
    chart=json.loads((d/'candidate-chart.json').read_text())
    mod=next((p for p in (ROOT/'mods').glob(f'esperon-dano-*/data/songs/{d.name}/{d.name}-chart.json')),None)
    prod=json.loads(mod.read_text()) if mod else {'notes':{}}
    voice=ROOT/align['voice']
    y,sr=librosa.load(voice,sr=16000,mono=True)
    hop=int(sr*0.01); frame=int(sr*0.04)
    rms=librosa.feature.rms(y=y,frame_length=frame,hop_length=hop,center=True)[0]
    rt=librosa.frames_to_time(np.arange(len(rms)),sr=sr,hop_length=hop)*1000
    peaks=[]
    for i in range(1,len(rms)-1):
        if rms[i]>=rms[i-1] and rms[i]>=rms[i+1] and rms[i]>np.percentile(rms,55):
            peaks.append(float(rt[i]))
    syll=align['syllables']
    errors=[]
    for s in syll:
        e=nearest_error(s['start_ms'],peaks)
        errors.append(e if e is not None else 99999)
    notes={dname:chart['notes'][dname] for dname in DIFFS}
    prod_notes={dname:prod.get('notes',{}).get(dname,[]) for dname in DIFFS}
    prod_deltas={}
    for dname in DIFFS:
        ct=[float(x['t']) for x in notes[dname]]
        pt=[float(x['t']) for x in prod_notes[dname]]
        deltas=[nearest_error(x,pt) for x in ct] if pt else []
        prod_deltas[dname]={
            'candidate_notes':len(ct),'production_notes':len(pt),
            'median_nearest_ms':round(float(np.median(deltas)),3) if deltas else None,
            'p95_nearest_ms':round(float(np.percentile(deltas,95)),3) if deltas else None,
        }
    return {
        'song':d.name,'voice':align['voice'],'duration_ms':align['duration_ms'],
        'syllables':len(syll),'interjections':sum(1 for s in syll if s['kind'].startswith('interjection')),
        'holds':sum(1 for s in syll if float(s.get('hold_ms',0))>=120),
        'low_confidence':sum(1 for s in syll if float(s.get('confidence',0))<0.45),
        'energy_nearest_ms':{'median':round(float(np.median(errors)),3),'p95':round(float(np.percentile(errors,95)),3),'over_120ms':sum(e>120 for e in errors)},
        'candidate_vs_production':prod_deltas,
    }

def main():
    global CAND
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-dir', type=Path, default=CAND)
    args=parser.parse_args()
    candidate_dir=args.candidate_dir.resolve()
    CAND=candidate_dir
    dirs=sorted(p for p in CAND.iterdir() if p.is_dir())
    with futures.ThreadPoolExecutor(max_workers=min(6,len(dirs))) as ex:
        rows=list(ex.map(analyze,dirs))
    out={'scope':'V263_SYLLABLE_CANDIDATE_COMPARISON','status':'MANUAL_REVIEW_REQUIRED','songs':len(rows),'parallel_workers':min(6,len(dirs)),'rows':rows,'interpretation':['Energy-nearest metrics are diagnostic, not syllable truth.','Candidate-vs-production deltas identify where the new method materially changes timing.','Low-confidence and high-error segments require review before promotion.']}
    p=CAND.parent/(CAND.name+'-comparison-v263.json'); p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'songs':len(rows),'output':str(p),'over_120ms':sum(r['energy_nearest_ms']['over_120ms'] for r in rows)}))

if __name__=='__main__': main()
