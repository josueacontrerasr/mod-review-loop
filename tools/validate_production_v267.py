#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import json
from validate_syllable_candidates_v267 import direction_errors
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
SONGS=[p.name for p in sorted((ROOT/'mods').glob('esperon-dano-*/data/songs/*')) if p.is_dir()]
DIFFS=('easy','normal','hard')

def one(song: str) -> dict[str,Any]:
    mod=ROOT/'mods'/f'esperon-dano-{song}'
    chart_path=mod/'data/songs'/song/f'{song}-chart.json'
    align_path=ROOT/'qa-lab/rebuild-v267/playstate-fix/syllable-candidates-small'/song/'syllable-alignment.json'
    chart=json.loads(chart_path.read_text())
    align=json.loads(align_path.read_text())
    syll=align['syllables']
    intervals=[(float(s['start_ms'])-45.0,float(s['vocal_end_ms'])+45.0) for s in syll]
    spans=[(float(s['start_ms'])-10.0,float(s['vocal_end_ms'])+20.0) for s in syll]
    starts=[float(s['start_ms']) for s in syll]
    errors=[]; counts={}; outside=0; leaked=0; bad_lanes=0; bad_holds=0; unaligned=0; vowel_mismatches=0
    for diff in DIFFS:
        notes=chart.get('notes',{}).get(diff,[]); counts[diff]=len(notes)
        if not notes or not {int(n.get('d',-1)) for n in notes}.issubset({0,1,2,3}): errors.append(f'lane_coverage_not_player_0_3:{diff}')
        for idx,n in enumerate(notes):
            if set(n)-{'t','d','l','k','p'}: leaked+=1
            if not isinstance(n.get('d'),int) or not 0<=n['d']<=3: bad_lanes+=1
            t=float(n.get('t',-1)); l=float(n.get('l',0) or 0)
            if not any(a<=t<=b for a,b in intervals): outside+=1
            nearest=min((abs(t-s) for s in starts),default=99999)
            inside_span=any(a<=t<=b for a,b in spans)
            if nearest>1.0 and not inside_span: unaligned+=1
            if l:
                end=t+l
                exact=[s for s in syll if abs(float(s['start_ms'])-t)<=1.0]
                item=max(exact,key=lambda s: float(s.get('vocal_end_ms',t)),default=min(syll,key=lambda s: abs(float(s['start_ms'])-t),default={'vocal_end_ms':t}))
                if end>float(item.get('vocal_end_ms',t))+50: bad_holds+=1
        vowel_mismatches += len(direction_errors(notes, syll))
    if outside: errors.append(f'notes_outside_syllable_intervals:{outside}')
    if unaligned: errors.append(f'notes_not_aligned_to_syllables:{unaligned}')
    if bad_holds: errors.append(f'holds_cross_vocal_boundary:{bad_holds}')
    if leaked: errors.append(f'candidate_metadata_leaked:{leaked}')
    if bad_lanes: errors.append(f'bad_player_lanes:{bad_lanes}')
    if vowel_mismatches: errors.append(f'vowel_direction_mismatches:{vowel_mismatches}')
    if not (counts['easy']<counts['normal']<=counts['hard']): errors.append(f'density_not_progressive:{counts}')
    if chart.get('generatedBy') != "Friday Night Funkin' - 0.8.6; V2.6.7 vocal RMS-VAD retimed holds and repetition-balanced player lanes d=0..3": errors.append('chart_generatedBy_invalid')
    if chart.get('candidateOnly') is not None or chart.get('sourcePolicy') is not None: errors.append('candidate_fields_leaked')
    return {'song':song,'status':'PASS' if not errors else 'ERRORS_FOUND','counts':counts,'outside_syllable_intervals':outside,'unaligned_notes':unaligned,'bad_holds':bad_holds,'vowel_direction_mismatches':vowel_mismatches,'candidate_metadata_leaked':leaked,'bad_player_lanes':bad_lanes,'generatedBy':chart.get('generatedBy'),'errors':errors}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: rows=sorted(pool.map(one,SONGS),key=lambda x:x['song'])
    payload={'scope':'PRODUCTION_VOCAL_SYLLABLE_VOWEL_MAPPED_GATE_V267','executed_at':datetime.now(timezone.utc).isoformat(),'target_version':'0.8.6','mod_version':'2.6.7','songs':len(rows),'passed':sum(x['status']=='PASS' for x in rows),'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'ERRORS_FOUND','total_notes_outside_syllable_intervals':sum(x['outside_syllable_intervals'] for x in rows),'total_unaligned_notes':sum(x['unaligned_notes'] for x in rows),'total_bad_holds':sum(x['bad_holds'] for x in rows),'rows':rows}
    out=ROOT/'qa-lab/rebuild-v267/playstate-fix/production-syllable-gate-v267.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'songs':payload['songs'],'passed':payload['passed'],'status':payload['status'],'outside':payload['total_notes_outside_syllable_intervals'],'unaligned':payload['total_unaligned_notes'],'bad_holds':payload['total_bad_holds'],'output':str(out)}))
    return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
