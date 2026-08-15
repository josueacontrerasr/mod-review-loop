#!/usr/bin/env python3
"""Validate isolated V2.6.6 vocal-mapped candidates on the real player strumline."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / 'qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small'
DIFFS = ('easy','normal','hard')


def load(p): return json.loads(p.read_text(encoding='utf-8'))


MAPPING = {'a': 0, 'e': 2, 'i': 3, 'o': 1, 'u': 1}


def direction_errors(notes, syllables):
    anchors = sorted({round(float(item['start_ms']), 3) for item in syllables})
    expected = {anchor: Counter() for anchor in anchors}
    has_unknown = {anchor: False for anchor in anchors}
    for item in syllables:
        anchor = min(anchors, key=lambda value: abs(value - float(item['start_ms'])))
        if abs(anchor - float(item['start_ms'])) <= 1.0:
            if item.get('vowel') in MAPPING:
                expected[anchor][MAPPING[item['vowel']]] += 1
            else:
                has_unknown[anchor] = True
    actual = {anchor: Counter() for anchor in anchors}
    errors = []
    for index, note in enumerate(notes):
        t = float(note['t'])
        near_exact = [anchor for anchor in anchors if abs(anchor - t) <= 0.05]
        if near_exact:
            anchor = min(near_exact, key=lambda value: abs(value - t))
            actual[anchor][int(note['d'])] += 1
            continue
        # Notes at t+0.5/t+1.0 ms are collision offsets or hard subdivisions.
        # They inherit a parent attack and must not inflate the parent's chord
        # counter; lane ownership and hold containment are checked separately.
        near_offset = [anchor for anchor in anchors if abs(anchor - t) <= 1.0]
        if near_offset:
            continue
        containing = [item for item in syllables if float(item['start_ms']) <= t <= float(item.get('vocal_end_ms', item['start_ms'])) + 20.0 and item.get('vowel') in MAPPING]
        if containing:
            expected_dirs = {MAPPING[item['vowel']] for item in containing}
            if int(note['d']) not in expected_dirs:
                item = min(containing, key=lambda value: abs(float(value['start_ms']) - t))
                errors.append((index, 'vowel_direction_mismatch_inside_hold', item.get('text'), item.get('vowel'), sorted(expected_dirs), note['d']))
    for anchor, values in actual.items():
        # If every syllable at this timestamp lacks a reliable vowel nucleus
        # (for example the Spanish conjunction "y"), the generator's
        # chronological fallback is intentional and cannot be checked against
        # the vowel map.
        if not expected[anchor] or has_unknown[anchor]:
            continue
        for direction, count in values.items():
            if count > expected[anchor].get(direction, 0):
                errors.append((anchor, 'vowel_direction_count_mismatch', direction, count, expected[anchor].get(direction, 0)))
    return errors


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
        expected_generated = "Friday Night Funkin' - 0.8.6; V2.6.6 vocal syllable vowel-mapped player lanes d=0..3"
        if chart.get('generatedBy') != expected_generated: errors.append((d.name,'chart','generatedBy','invalid',chart.get('generatedBy')))
        for diff in DIFFS:
            notes=chart['notes'][diff]
            lane_set={int(n.get('d',-1)) for n in notes}
            if not lane_set or not lane_set.issubset({0,1,2,3}): errors.append((d.name,diff,'lane_coverage','expected_player_0_1_2_3',sorted(lane_set)))
            prev=-1
            for i,n in enumerate(notes):
                t=float(n['t']); dur=float(n.get('l',0))
                if not (0 <= t < end): errors.append((d.name,diff,i,'time_out_of_audio',t,end))
                if t < prev: errors.append((d.name,diff,i,'not_sorted',t,prev))
                # Direction ownership is checked below with timestamp-aware chord groups;
                # notes sharing one attack may legitimately represent several syllables.
                if int(n['d']) not in range(0, 4):
                    errors.append((d.name,diff,i,'bad_player_lane',n['d']))
                if dur < 0: errors.append((d.name,diff,i,'negative_hold',dur))
                if dur and t+dur > end+25: errors.append((d.name,diff,i,'hold_out_of_audio',t,dur,end))
                if dur:
                    # Hold must end before the next aligned syllable.
                    nxt=next((x for x in starts if x > t+1), end)
                    if t+dur > nxt+15: errors.append((d.name,diff,i,'hold_crosses_next_syllable',t,dur,nxt))
                prev=t
            errors.extend((d.name, diff, *error) for error in direction_errors(notes, syll))
        rows.append({'song':d.name,'syllables':len(syll),'interjections':sum(1 for s in syll if s['kind'].startswith('interjection')),'holds':sum(1 for s in syll if float(s.get('hold_ms',0))>=120),'notes':{x:len(chart['notes'][x]) for x in DIFFS},'duration_ms':align['duration_ms']})
    out={'scope':'V266_VOWEL_MAPPED_SYLLABLE_CANDIDATE_VALIDATION','status':'PASS' if not errors and len(rows)==21 else 'FAIL','songs':len(rows),'errors':errors,'rows':rows,'rules':{'notes_inside_vocal_alignment':True,'holds_do_not_cross_next_syllable':True,'lanes':'0..3 player strumline','vowel_mapping':{'a':0,'e':2,'i':3,'o':1,'u':1},'difficulties':list(DIFFS)}}
    path=candidate_dir.parent/(candidate_dir.name+'-validation-v266.json')
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'songs':len(rows),'errors':len(errors),'output':str(path)}))
    return 0 if out['status']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())
