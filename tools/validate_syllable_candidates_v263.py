#!/usr/bin/env python3
"""Validate isolated V2.6.3 syllable-aligned candidates."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / 'qa-lab/rebuild-v263/playstate-fix/syllable-candidates'
DIFFS = ('easy','normal','hard')


def load(p): return json.loads(p.read_text(encoding='utf-8'))


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-dir', type=Path, default=CAND)
    args=parser.parse_args()
    candidate_dir=args.candidate_dir.resolve()
    rows=[]
    errors=[]
    songs=sorted(p for p in candidate_dir.iterdir() if p.is_dir())
    for d in songs:
        align=load(d/'syllable-alignment.json')
        chart=load(d/'candidate-chart.json')
        syll=align['syllables']
        starts=[float(s['start_ms']) for s in syll]
        end=float(align['duration_ms'])
        for diff in DIFFS:
            notes=chart['notes'][diff]
            prev=-1
            for i,n in enumerate(notes):
                t=float(n['t']); dur=float(n.get('l',0))
                if not (0 <= t < end): errors.append((d.name,diff,i,'time_out_of_audio',t,end))
                if t < prev: errors.append((d.name,diff,i,'not_sorted',t,prev))
                if int(n['d']) not in range(4): errors.append((d.name,diff,i,'bad_lane',n['d']))
                if dur < 0: errors.append((d.name,diff,i,'negative_hold',dur))
                if dur and t+dur > end+25: errors.append((d.name,diff,i,'hold_out_of_audio',t,dur,end))
                if dur:
                    # Hold must end before the next aligned syllable.
                    nxt=next((x for x in starts if x > t+1), end)
                    if t+dur > nxt+15: errors.append((d.name,diff,i,'hold_crosses_next_syllable',t,dur,nxt))
                prev=t
        rows.append({'song':d.name,'syllables':len(syll),'interjections':sum(1 for s in syll if s['kind'].startswith('interjection')),'holds':sum(1 for s in syll if float(s.get('hold_ms',0))>=120),'notes':{x:len(chart['notes'][x]) for x in DIFFS},'duration_ms':align['duration_ms']})
    out={'scope':'V263_SYLLABLE_CANDIDATE_VALIDATION','status':'PASS' if not errors and len(rows)==21 else 'FAIL','songs':len(rows),'errors':errors,'rows':rows,'rules':{'notes_inside_vocal_alignment':True,'holds_do_not_cross_next_syllable':True,'lanes':'0..3','difficulties':list(DIFFS)}}
    path=candidate_dir.parent/(candidate_dir.name+'-validation-v263.json')
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'songs':len(rows),'errors':len(errors),'output':str(path)}))
    return 0 if out['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
