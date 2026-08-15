#!/usr/bin/env python3
from __future__ import annotations
import json
import statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'qa-lab/rebuild-v260/joint-audio-audit-v260.json').read_text())
rows=[]; issues=[]
for song in data['rows']:
    for diff,a in song['difficulties'].items():
        row={'song':song['song'],'difficulty':diff,'notes':a['notes'],'vocal_notes':a['family_counts']['vocal'],'rhythm_notes':a['family_counts']['rhythm'],'unanchored_ratio':a['unanchored_ratio'],'vocal_note_cov_120ms':a['vocal_note_coverage_120ms'],'rhythm_note_cov_120ms':a['rhythm_note_coverage_120ms'],'all_note_cov_120ms':a['all_note_coverage_120ms'],'vocal_median_ms':a['vocal_abs_median_ms'],'rhythm_median_ms':a['rhythm_abs_median_ms'],'all_p95_ms':a['all_abs_p95_ms']}
        rows.append(row)
        if row['vocal_note_cov_120ms'] < .95: issues.append(f"{song['song']}:{diff}:vocal_note_cov")
        if row['rhythm_notes'] and row['rhythm_note_cov_120ms'] < .90: issues.append(f"{song['song']}:{diff}:rhythm_note_cov")
        if row['unanchored_ratio'] > .02: issues.append(f"{song['song']}:{diff}:unanchored")
by_diff={}
for diff in ('easy','normal','hard'):
    g=[r for r in rows if r['difficulty']==diff]
    by_diff[diff]={'vocal_note_cov_min':min(r['vocal_note_cov_120ms'] for r in g),'rhythm_note_cov_min':min(r['rhythm_note_cov_120ms'] for r in g if r['rhythm_notes']),'unanchored_max':max(r['unanchored_ratio'] for r in g),'all_p95_max':max(r['all_p95_ms'] for r in g if r['all_p95_ms'] is not None),'notes_total':sum(r['notes'] for r in g),'vocal_notes_total':sum(r['vocal_notes'] for r in g),'rhythm_notes_total':sum(r['rhythm_notes'] for r in g),'failures':sum(1 for x in issues if f':{diff}:' in x)}
payload={'version':'2.6.0-joint-audio-summary','status':'PASS' if not issues else 'VOICE_SYNC_REVIEW_REQUIRED','songs':20,'difficulties':60,'thresholds':{'vocal_note_cov_120ms':.95,'rhythm_note_cov_120ms':.90,'unanchored_ratio':.02},'by_difficulty':by_diff,'issues':issues,'rows':rows}
out=ROOT/'qa-lab/rebuild-v260/joint-audio-summary-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'issues':len(issues),'by_difficulty':by_diff,'output':str(out)},ensure_ascii=False))
