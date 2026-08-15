#!/usr/bin/env python3
from __future__ import annotations
import json
import statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'qa-lab/rebuild-v260/voice-audit-parallel-v260.json').read_text())
rows=[]; issues=[]
thresholds={'easy':0.55,'normal':0.75,'hard':0.90}
for song in data['rows']:
    for diff,a in song['difficulties'].items():
        outer=song['difficulties'][diff]; a=outer['alignment']; voice=a['voice_to_note']; note=a['note_to_voice']; drift=a.get('drift') or {}
        row={'song':song['song'],'difficulty':diff,'notes':outer['notes'],'lanes':outer['lanes'],'note_cov_120ms':a['note_coverage_120ms'],'note_p95_ms':note['p95_ms'],'note_signed_mean_ms':a['note_to_voice_signed']['signed_mean_ms'],'voice_event_cov_120ms':a['voice_event_coverage_120ms'],'voice_event_p95_ms':voice['p95_ms'],'drift_ms_per_minute':drift.get('slope_ms_per_minute')}
        rows.append(row)
        if row['note_cov_120ms'] < .95: issues.append(f"{song['song']}:{diff}:note_coverage")
        if row['note_p95_ms'] is not None and row['note_p95_ms'] > 120: issues.append(f"{song['song']}:{diff}:note_p95")
        if row['voice_event_cov_120ms'] < thresholds[diff]: issues.append(f"{song['song']}:{diff}:event_coverage")
        if row['drift_ms_per_minute'] is not None and abs(row['drift_ms_per_minute']) > 30: issues.append(f"{song['song']}:{diff}:drift")
by_diff={}
for diff in ('easy','normal','hard'):
    group=[r for r in rows if r['difficulty']==diff]
    def vals(k): return [r[k] for r in group if r[k] is not None]
    by_diff[diff]={'note_cov_120ms_min':min(vals('note_cov_120ms')),'note_p95_ms_max':max(vals('note_p95_ms')),'voice_event_cov_120ms_min':min(vals('voice_event_cov_120ms')),'voice_event_p95_ms_max':max(vals('voice_event_p95_ms')),'drift_abs_max':max(abs(x) for x in vals('drift_ms_per_minute')) if vals('drift_ms_per_minute') else None,'failures':sum(1 for x in issues if f':{diff}:' in x)}
payload={'version':'2.6.0-vocal-audit-summary','status':'PASS' if not issues else 'VOICE_SYNC_REVIEW_REQUIRED','songs':20,'difficulties':60,'thresholds':{'note_coverage_120ms':.95,'note_p95_ms':120,'event_coverage_by_difficulty':thresholds,'drift_abs_ms_per_minute':30},'by_difficulty':by_diff,'issues':issues,'rows':rows}
out=ROOT/'qa-lab/rebuild-v260/voice-audit-summary-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'issues':len(issues),'by_difficulty':by_diff,'output':str(out)},ensure_ascii=False))
