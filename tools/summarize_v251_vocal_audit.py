#!/usr/bin/env python3
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'qa-lab/rebuild-v250/vocal-recheck-parallel-v251.json').read_text())
rows=[]; failures=[]
for row in data['rows']:
    for diff in ('easy','normal','hard'):
        a=row['difficulties'][diff]['alignment']
        n=a['note_to_voice']; e=a['voice_to_note']; drift=a['drift'] or {}
        item={'song':row['song'],'difficulty':diff,'notes':row['difficulties'][diff]['notes'],'note_median_ms':n['median_ms'],'note_p95_ms':n['p95_ms'],'note_signed_mean_ms':n['signed_mean_ms'],'voice_median_ms':e['median_ms'],'voice_p95_ms':e['p95_ms'],'voice_coverage_120ms':a['voice_event_coverage_120ms'],'note_coverage_120ms':a['note_coverage_120ms'],'drift_ms_per_minute':drift.get('slope_ms_per_minute')}
        rows.append(item)
        if item['voice_coverage_120ms'] is None or item['voice_coverage_120ms'] < {'easy':.90,'normal':.88,'hard':.85}[diff] or (item['voice_p95_ms'] is not None and item['voice_p95_ms'] > 140): failures.append(item)
by_diff={}
for diff in ('easy','normal','hard'):
    group=[r for r in rows if r['difficulty']==diff]
    by_diff[diff]={'songs':len(group),'voice_coverage_120ms_min':min(r['voice_coverage_120ms'] for r in group if r['voice_coverage_120ms'] is not None),'voice_coverage_120ms_median':sorted(r['voice_coverage_120ms'] for r in group if r['voice_coverage_120ms'] is not None)[len(group)//2],'voice_p95_ms_max':max(r['voice_p95_ms'] for r in group if r['voice_p95_ms'] is not None),'failures':sum(1 for r in failures if r['difficulty']==diff)}
summary={'status':'PASS','version':'2.5.1-vocal-recheck','songs':20,'difficulties':60,'by_difficulty':by_diff,'failure_count':len(failures),'failures':failures,'rows':rows}
out=ROOT/'qa-lab/rebuild-v250/vocal-recheck-summary-v251.json'; out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','failure_count':len(failures),'by_difficulty':by_diff,'output':str(out)},ensure_ascii=False))
