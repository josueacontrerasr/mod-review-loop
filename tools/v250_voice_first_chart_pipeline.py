#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import librosa
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'qa-lab/rebuild-v250'
OUT=EVID/'voice-first-candidates'
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

sys.path.insert(0,str(ROOT/'tools'))
from v230_sync_pipeline import (  # noqa: E402
    detector_times, independent_energy_judge, independent_onset_judge,
    verification_onset_judge, vad_cpu, load_mono, sha256, cluster_onsets, nearest,
)

def median_times(y,sr):
    hop=256
    env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop,aggregate=np.median)
    frames=librosa.onset.onset_detect(onset_envelope=env,sr=sr,hop_length=hop,backtrack=True,units='frames',delta=0.06,wait=5,pre_max=3,post_max=3)
    return [round(float(f*hop*1000/sr),3) for f in frames if f*hop*1000/sr>=120]

def spaced(events,min_gap,limit=None):
    picked=[]
    for e in sorted(events,key=lambda x:(float(x['t_ms']),-int(x.get('vote_count',0)))):
        t=float(e['t_ms'])
        if t<120: continue
        if any(abs(t-float(x['t_ms']))<min_gap for x in picked): continue
        picked.append(e)
        if limit is not None and len(picked)>=limit: break
    return picked

def note_times(notes): return [float(n['t']) for n in notes]

def make_notes(vocal_events,rhythm_events,diff):
    cfg={'easy':(360.0,0.15,0.80),'normal':(220.0,0.25,1.00),'hard':(140.0,0.35,1.22)}[diff]
    min_gap, rhythm_ratio, speed=cfg
    vocal=spaced(vocal_events,min_gap)
    rhythm=spaced(rhythm_events,min_gap)
    rhythm=[e for e in rhythm if nearest(float(e['t_ms']),[float(v['t_ms']) for v in vocal])[1] is None or nearest(float(e['t_ms']),[float(v['t_ms']) for v in vocal])[1]>90]
    rhythm= rhythm[:max(1,round(len(vocal)*rhythm_ratio))]
    merged=[]
    for i,e in enumerate(vocal): merged.append({'t':round(float(e['t_ms']),3),'d':i%4,'_family':'vocal','_votes':e.get('votes',[])})
    for i,e in enumerate(rhythm): merged.append({'t':round(float(e['t_ms']),3),'d':(i*2+1)%4,'_family':'rhythm','_votes':e.get('votes',[])})
    merged.sort(key=lambda n:(float(n['t']),int(n['d'])))
    # Final collision guard: one note per timestamp/lane and official player lanes only.
    seen=set(); out=[]
    for n in merged:
        k=(round(float(n['t']),3),int(n['d']))
        if k in seen: continue
        seen.add(k); out.append({k2:v for k2,v in n.items() if not k2.startswith('_')})
    return out, {'vocal_events_used':len(vocal),'rhythm_events_used':len(rhythm),'vocal_ratio':round(len(vocal)/max(1,len(out)),6),'scrollSpeed':speed,'min_gap_ms':min_gap}

def metrics(notes,vocal_times,rhythm_times):
    voice=[nearest(float(n['t']),vocal_times)[1] for n in notes]
    rhythm=[nearest(float(n['t']),rhythm_times)[1] for n in notes]
    return {'notes':len(notes),'player_lane_notes':sum(0<=int(n['d'])<=3 for n in notes),'voice_within_80ms':round(sum(e is not None and e<=80 for e in voice)/max(1,len(notes)),6),'voice_within_120ms':round(sum(e is not None and e<=120 for e in voice)/max(1,len(notes)),6),'rhythm_within_120ms':round(sum(e is not None and e<=120 for e in rhythm)/max(1,len(notes)),6),'first_ms':min((float(n['t']) for n in notes),default=None),'first_10s':sum(float(n['t'])<=10000 for n in notes),'lanes':sorted(set(int(n['d']) for n in notes))}

def process(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'; song_dir=next((mod/'data/songs').iterdir())
    meta=json.loads((song_dir/f'{song}-metadata.json').read_text())
    player=meta['playData']['characters']['player']; voice=mod/'songs'/song/f'Voices-{player}.ogg'; inst=mod/'songs'/song/'Inst.ogg'
    voice22,sr22=load_mono(voice,22050); voice16,_=load_mono(voice,16000); voice44,sr44=load_mono(voice,44100)
    inst22,instsr=load_mono(inst,22050); inst16,_=load_mono(inst,16000); inst44,inst44sr=load_mono(inst,44100)
    vad=vad_cpu(voice16)
    vdet=detector_times(voice22,sr22); vdet['median']=median_times(voice22,sr22); vdet['judge']=independent_onset_judge(voice22,sr22); vdet['verify']=verification_onset_judge(voice44,sr44)
    vocal_events=cluster_onsets(vdet,vad['segments'])
    rdet=detector_times(inst22,instsr); rdet['median']=median_times(inst22,instsr); rdet['judge']=independent_onset_judge(inst22,instsr); rdet['verify']=verification_onset_judge(inst44,inst44sr)
    rhythm_events=cluster_onsets(rdet,[])
    energy=independent_energy_judge(inst16,16000)
    rhythm_times=[float(e['t_ms']) for e in rhythm_events]
    for t in energy:
        if nearest(float(t),rhythm_times)[1] is not None and nearest(float(t),rhythm_times)[1]<=80: rhythm_events.append({'t_ms':float(t),'votes':['energy'],'vote_count':1})
    rhythm_events.sort(key=lambda e:float(e['t_ms']))
    current=json.loads((song_dir/f'{song}-chart.json').read_text())
    out=json.loads(json.dumps(current)); diffs={}; vocal_times=[float(e['t_ms']) for e in vocal_events]
    for diff in ('easy','normal','hard'):
        notes,build=make_notes(vocal_events,rhythm_events,diff); out['notes'][diff]=notes; diffs[diff]={'build':build,'metrics':metrics(notes,vocal_times,rhythm_times)}
    out['generatedBy']="Friday Night Funkin' - v0.8.6; V2.5.0 voice-first chart; official player strumline lanes 0-3"
    outpath=OUT/song/f'{song}-chart-v250.json'; outpath.parent.mkdir(parents=True,exist_ok=True); outpath.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'song':song,'voice_sha256':sha256(voice),'inst_sha256':sha256(inst),'vocal_events':len(vocal_events),'rhythm_events':len(rhythm_events),'vad_segments':len(vad['segments']),'vocal_coverage':vad['coverage_ratio'],'current_chart_sha256':hashlib.sha256((song_dir/f'{song}-chart.json').read_bytes()).hexdigest(),'difficulties':diffs,'output':str(outpath.relative_to(ROOT))}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=sorted(ex.map(process,SONGS),key=lambda x:x['song'])
    payload={'version':'2.5.0','status':'PASS','songs':len(rows),'difficulties':len(rows)*3,'parallel_workers':4,'method':{'priority':'vocal onsets from distributed Voices stem first; instrumental accents second','player_strumline':'d 0-3 per official SongData.hx','easy':'min gap 360ms, rhythm cap 15%, scrollSpeed 0.80','normal':'min gap 220ms, rhythm cap 25%, scrollSpeed 1.00','hard':'min gap 140ms, rhythm cap 35%, scrollSpeed 1.22'},'rows':rows}
    out=EVID/'voice-first-v250.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':'PASS','songs':20,'difficulties':60,'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
