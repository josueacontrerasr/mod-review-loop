#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'qa-lab/rebuild-v250'
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
sys.path.insert(0,str(ROOT/'tools'))
from v230_sync_pipeline import detector_times, independent_onset_judge, verification_onset_judge, vad_cpu, load_mono, cluster_onsets, sha256  # noqa
from v250_voice_first_chart_pipeline import median_times  # noqa

def nearest(t, refs):
    if not refs:return None
    i=int(np.searchsorted(refs,t)); c=[]
    if i<len(refs):c.append((abs(t-refs[i]),t-refs[i]))
    if i:c.append((abs(t-refs[i-1]),t-refs[i-1]))
    return min(c,key=lambda x:x[0]) if c else None

def get_events(path, sr=22050):
    y,sr2=load_mono(path,sr); y44,sr44=load_mono(path,44100); y16,_=load_mono(path,16000)
    det=detector_times(y,sr2); det['median']=median_times(y,sr2); det['judge']=independent_onset_judge(y,sr2); det['verify']=verification_onset_judge(y44,sr44)
    vad=vad_cpu(y16)
    events=cluster_onsets(det,vad['segments'])
    return sorted(float(e['t_ms']) for e in events), len(vad['segments']), vad.get('coverage_ratio'), float(len(y)/max(sr2,1)*1000)

def row_for_diff(notes,vocal,rhythm,diff):
    cfg={'easy':{'vocal_match_ms':100,'rhythm_match_ms':140},'normal':{'vocal_match_ms':100,'rhythm_match_ms':140},'hard':{'vocal_match_ms':100,'rhythm_match_ms':140}}[diff]
    fam=[]; all_abs=[]; vocal_abs=[]; rhythm_abs=[]; unanchored=[]
    for n in notes:
        t=float(n.get('t',-1)); v=nearest(t,vocal); r=nearest(t,rhythm)
        vd=v[0] if v else float('inf'); rd=r[0] if r else float('inf')
        if vd <= cfg['vocal_match_ms'] and vd <= rd:
            family='vocal'; err=vd; signed=v[1]
            vocal_abs.append(vd)
        elif rd <= cfg['rhythm_match_ms']:
            family='rhythm'; err=rd; signed=r[1]
            rhythm_abs.append(rd)
        else:
            family='unanchored'; err=min(vd,rd); signed=None
            unanchored.append(t)
        if np.isfinite(err):all_abs.append(err)
        fam.append(family)
    total=len(notes)
    return {'notes':total,'family_counts':{k:fam.count(k) for k in ('vocal','rhythm','unanchored')},'vocal_note_coverage_120ms':round(sum(x<=120 for x in vocal_abs)/max(1,len(vocal_abs)),6),'rhythm_note_coverage_120ms':round(sum(x<=120 for x in rhythm_abs)/max(1,len(rhythm_abs)),6),'all_note_coverage_120ms':round(sum(x<=120 for x in all_abs)/max(1,total),6),'unanchored_ratio':round(len(unanchored)/max(1,total),6),'vocal_abs_median_ms':round(float(np.median(vocal_abs)),3) if vocal_abs else None,'rhythm_abs_median_ms':round(float(np.median(rhythm_abs)),3) if rhythm_abs else None,'all_abs_p95_ms':round(float(np.percentile(all_abs,95)),3) if all_abs else None}

def process(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); meta=json.loads((sd/f'{song}-metadata.json').read_text()); player=meta['playData']['characters']['player']; base=mod/'songs'/song
    voice,segments,coverage,duration=get_events(base/f'Voices-{player}.ogg'); rhythm,_,_,_=get_events(base/'Inst.ogg')
    chart=json.loads((sd/f'{song}-chart.json').read_text()); diffs={d:row_for_diff(chart['notes'][d],voice,rhythm,d) for d in ('easy','normal','hard')}
    return {'song':song,'voice_sha256':sha256(base/f'Voices-{player}.ogg'),'inst_sha256':sha256(base/'Inst.ogg'),'duration_ms':round(duration,3),'vocal_events':len(voice),'rhythm_events':len(rhythm),'vad_segments':segments,'vocal_coverage':coverage,'difficulties':diffs}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=sorted(ex.map(process,SONGS),key=lambda x:x['song'])
    out=EVID/'vocal-recheck-joint-audio-v251.json'; out.write_text(json.dumps({'version':'2.5.1-joint-vocal-rhythm','status':'PASS','songs':len(rows),'difficulties':60,'parallel_workers':8,'rows':rows},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','songs':len(rows),'difficulties':60,'output':str(out)},ensure_ascii=False))
if __name__=='__main__':main()
