#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
old=json.loads((ROOT/'qa-lab/rebuild-v250/vocal-recheck-joint-audio-v251.json').read_text())
new=json.loads((ROOT/'qa-lab/rebuild-v250/voice-priority-candidates-v251.json').read_text())
rows=[]; issues=[]
for n in sorted(new['rows'],key=lambda x:x['song']):
    o=next(x for x in old['rows'] if x['song']==n['song'])
    for diff in ('easy','normal','hard'):
        nm=n['difficulties'][diff]['metrics']; b=n['difficulties'][diff]['build']; oldm=o['difficulties'][diff]
        row={'song':n['song'],'difficulty':diff,'notes':nm['notes'],'vocal_notes':nm['family_counts']['vocal'],'rhythm_notes':nm['family_counts']['rhythm'],'vocal_ratio':b['vocal_ratio'],'vocal_note_cov_120ms':nm['vocal_note_to_voice']['coverage_120ms'],'vocal_note_p95_ms':nm['vocal_note_to_voice']['p95_ms'],'vocal_event_cov_120ms':nm['vocal_event_to_note']['coverage_120ms'],'vocal_event_p95_ms':nm['vocal_event_to_note']['p95_ms'],'rhythm_note_cov_120ms':nm['rhythm_note_to_rhythm']['coverage_120ms'],'rhythm_note_p95_ms':nm['rhythm_note_to_rhythm']['p95_ms'],'old_all_note_cov_120ms':oldm['all_note_coverage_120ms'],'old_unanchored':oldm['unanchored_ratio']}
        rows.append(row)
        gate={'easy':.55,'normal':.75,'hard':.90}[diff]
        if row['vocal_note_cov_120ms'] < gate: issues.append(f"{n['song']}:{diff}:vocal_note_coverage")
        if row['vocal_event_cov_120ms'] < gate: issues.append(f"{n['song']}:{diff}:vocal_event_coverage")
        if row['vocal_note_p95_ms'] is not None and row['vocal_note_p95_ms'] > 140: issues.append(f"{n['song']}:{diff}:vocal_note_p95")
        if row['rhythm_notes'] and row['rhythm_note_cov_120ms'] < .70: issues.append(f"{n['song']}:{diff}:rhythm_note_coverage")
        # En fácil/normal la cobertura evento→nota es deliberadamente menor por densidad; la exactitud de cada flecha vocal sigue siendo obligatoria.
by_diff={}
for diff in ('easy','normal','hard'):
    g=[r for r in rows if r['difficulty']==diff]
    by_diff[diff]={'vocal_note_cov_min':min(r['vocal_note_cov_120ms'] for r in g),'vocal_event_cov_min':min(r['vocal_event_cov_120ms'] for r in g),'vocal_note_p95_max':max(r['vocal_note_p95_ms'] for r in g if r['vocal_note_p95_ms'] is not None),'vocal_event_p95_max':max(r['vocal_event_p95_ms'] for r in g if r['vocal_event_p95_ms'] is not None),'rhythm_note_cov_min':min(r['rhythm_note_cov_120ms'] for r in g if r['rhythm_notes']),'notes_total':sum(r['notes'] for r in g),'vocal_notes_total':sum(r['vocal_notes'] for r in g),'rhythm_notes_total':sum(r['rhythm_notes'] for r in g),'failures':sum(1 for x in issues if f':{diff}:' in x)}
payload={'version':'2.5.1-voice-priority-comparison','status':'PASS' if not issues else 'MANUAL_REVIEW_REQUIRED','songs':20,'difficulties':60,'by_difficulty':by_diff,'issues':issues,'rows':rows}
out=ROOT/'qa-lab/rebuild-v250/vocal-priority-comparison-v251.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':payload['status'],'issues':len(issues),'by_difficulty':by_diff,'output':str(out)},ensure_ascii=False))
