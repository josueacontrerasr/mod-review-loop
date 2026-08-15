#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
old=json.loads((ROOT/'qa-lab/rebuild-v250/vocal-recheck-joint-audio-v251.json').read_text())
new=json.loads((ROOT/'qa-lab/rebuild-v250/voice-priority-candidates-v251.json').read_text())
rows=[]; issues=[]
for o,n in zip(sorted(old['rows'],key=lambda x:x['song']),sorted(new['rows'],key=lambda x:x['song'])):
    for diff in ('easy','normal','hard'):
        oa=o['difficulties'][diff]; na=n['difficulties'][diff]['metrics']; nb=n['difficulties'][diff]['build']
        row={'song':o['song'],'difficulty':diff,'old_all_cov_120ms':oa['all_note_coverage_120ms'],'old_unanchored':oa['unanchored_ratio'],'old_vocal_notes':oa['family_counts']['vocal'],'old_rhythm_notes':oa['family_counts']['rhythm'],'new_notes':na['notes'],'new_voice_to_note_cov_120ms':na['voice_to_note']['coverage_120ms'],'new_note_to_voice_cov_120ms':na['note_to_voice']['coverage_120ms'],'new_note_to_rhythm_cov_120ms':na['note_to_rhythm']['coverage_120ms'],'new_voice_median_ms':na['voice_to_note']['median_ms'],'new_voice_p95_ms':na['voice_to_note']['p95_ms'],'new_rhythm_p95_ms':na['note_to_rhythm']['p95_ms'],'vocal_ratio':nb['vocal_ratio']}
        rows.append(row)
        gate={'easy':.90,'normal':.88,'hard':.85}[diff]
        if row['new_voice_to_note_cov_120ms'] < gate: issues.append(f"{o['song']}:{diff}:voice_coverage")
        if row['new_voice_p95_ms'] is not None and row['new_voice_p95_ms'] > 140: issues.append(f"{o['song']}:{diff}:voice_p95")
        if row['new_note_to_rhythm_cov_120ms'] < .75: issues.append(f"{o['song']}:{diff}:rhythm_coverage")
by_diff={}
for diff in ('easy','normal','hard'):
    g=[r for r in rows if r['difficulty']==diff]
    by_diff[diff]={'voice_to_note_cov_min':min(r['new_voice_to_note_cov_120ms'] for r in g),'voice_to_note_cov_median':sorted(r['new_voice_to_note_cov_120ms'] for r in g)[len(g)//2],'voice_p95_max':max(r['new_voice_p95_ms'] for r in g if r['new_voice_p95_ms'] is not None),'rhythm_p95_max':max(r['new_rhythm_p95_ms'] for r in g if r['new_rhythm_p95_ms'] is not None),'notes_total':sum(r['new_notes'] for r in g),'failures':sum(1 for x in issues if f':{diff}:' in x)}
payload={'version':'2.5.1-candidate-comparison','status':'PASS' if not issues else 'MANUAL_REVIEW_REQUIRED','songs':20,'difficulties':60,'by_difficulty':by_diff,'issues':issues,'rows':rows}
out=ROOT/'qa-lab/rebuild-v250/vocal-alignment-before-after-v251.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':payload['status'],'issues':len(issues),'by_difficulty':by_diff,'output':str(out)},ensure_ascii=False))
