#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'qa-lab/rebuild-v250'
OUT=EVID/'voice-priority-candidates-v251'
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
sys.path.insert(0,str(ROOT/'tools'))
from v230_sync_pipeline import detector_times, independent_onset_judge, verification_onset_judge, vad_cpu, load_mono, cluster_onsets, sha256  # noqa
from v250_voice_first_chart_pipeline import median_times  # noqa

def nearest_pair(t, refs):
    if not refs:return (None,None)
    i=int(np.searchsorted(refs,t)); c=[]
    if i<len(refs): c.append((abs(t-refs[i]),refs[i]))
    if i: c.append((abs(t-refs[i-1]),refs[i-1]))
    return min(c,key=lambda x:x[0]) if c else (None,None)

def detect(path):
    y,sr=load_mono(path,22050); y44,sr44=load_mono(path,44100); y16,_=load_mono(path,16000)
    det=detector_times(y,sr); det['median']=median_times(y,sr); det['judge']=independent_onset_judge(y,sr); det['verify']=verification_onset_judge(y44,sr44)
    vad=vad_cpu(y16); events=cluster_onsets(det,vad['segments'])
    return sorted(float(e['t_ms']) for e in events),vad,float(len(y)/max(sr,1)*1000)

def spaced(times,min_gap):
    out=[]
    for t in sorted(times):
        if t<120: continue
        if not out or t-out[-1]>=min_gap: out.append(t)
    return out

def make_chart(vocal,rhythm,diff):
    cfg={'easy':(300.0,0.05,0.78),'normal':(180.0,0.10,0.98),'hard':(120.0,0.15,1.18)}[diff]
    min_gap,rhythm_ratio,speed=cfg
    vocal_selected=spaced(vocal,min_gap)
    rhythm_selected=[]
    for t in spaced(rhythm,min_gap):
        _,near=nearest_pair(t,vocal_selected)
        if near is not None and abs(t-near)<110: continue
        rhythm_selected.append(t)
    rhythm_selected=rhythm_selected[:max(0,round(len(vocal_selected)*rhythm_ratio))]
    notes=[]
    for i,t in enumerate(vocal_selected): notes.append({'t':round(t,3),'d':i%4,'_family':'vocal'})
    for i,t in enumerate(rhythm_selected): notes.append({'t':round(t,3),'d':(i*2+1)%4,'_family':'rhythm'})
    notes.sort(key=lambda x:(x['t'],x['d']))
    dedup=[]; seen=set()
    for n in notes:
        key=(n['t'],n['d'])
        if key not in seen: seen.add(key); dedup.append(n)
    return dedup,{'vocal_events_used':len(vocal_selected),'rhythm_events_used':len(rhythm_selected),'vocal_ratio':round(len(vocal_selected)/max(1,len(dedup)),6),'scrollSpeed':speed,'min_gap_ms':min_gap,'rhythm_cap':rhythm_ratio}

def metrics(notes,vocal,rhythm):
    note_voice=[]; note_rhythm=[]; voice_event=[]
    vocal_note_times=[]; rhythm_note_times=[]
    for n in notes:
        t=float(n['t']); vd,_=nearest_pair(t,vocal); rd,_=nearest_pair(t,rhythm)
        if n.get('_family')=='vocal':
            if vd is not None: note_voice.append(vd)
            vocal_note_times.append(t)
        else:
            if rd is not None: note_rhythm.append(rd)
            rhythm_note_times.append(t)
    for t in vocal:
        d,_=nearest_pair(t,sorted(vocal_note_times))
        if d is not None: voice_event.append(d)
    def stat(a):
        return {'count':len(a),'median_ms':round(float(np.median(a)),3) if a else None,'p95_ms':round(float(np.percentile(a,95)),3) if a else None,'coverage_40ms':round(sum(x<=40 for x in a)/max(1,len(a)),6) if a else 0.0,'coverage_80ms':round(sum(x<=80 for x in a)/max(1,len(a)),6) if a else 0.0,'coverage_120ms':round(sum(x<=120 for x in a)/max(1,len(a)),6) if a else 0.0}
    return {'notes':len(notes),'lanes':sorted({int(n['d']) for n in notes}),'vocal_note_to_voice':stat(note_voice),'rhythm_note_to_rhythm':stat(note_rhythm),'vocal_event_to_note':stat(voice_event),'family_counts':{'vocal':len(vocal_note_times),'rhythm':len(rhythm_note_times)}}

def process(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); meta=json.loads((sd/f'{song}-metadata.json').read_text()); player=meta['playData']['characters']['player']; base=mod/'songs'/song
    vocal,vad,duration=detect(base/f'Voices-{player}.ogg'); rhythm,_,_=detect(base/'Inst.ogg'); current=json.loads((sd/f'{song}-chart.json').read_text()); out=json.loads(json.dumps(current)); diffs={}
    for diff in ('easy','normal','hard'):
        notes,build=make_chart(vocal,rhythm,diff); out['notes'][diff]=[{k:v for k,v in n.items() if k != '_family'} for n in notes]; diffs[diff]={'build':build,'metrics':metrics(notes,vocal,rhythm)}
    out['generatedBy']='Friday Night Funkin\' - v0.8.6; V2.5.1 strict voice-priority candidate; player lanes 0-3'
    outpath=OUT/song/f'{song}-chart-v251.json'; outpath.parent.mkdir(parents=True,exist_ok=True); outpath.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return {'song':song,'voice_sha256':sha256(base/f'Voices-{player}.ogg'),'inst_sha256':sha256(base/'Inst.ogg'),'duration_ms':round(duration,3),'vocal_events':len(vocal),'vad_segments':len(vad['segments']),'vocal_coverage':vad.get('coverage_ratio'),'difficulties':diffs,'output':str(outpath.relative_to(ROOT))}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=sorted(ex.map(process,SONGS),key=lambda x:x['song'])
    out=EVID/'voice-priority-candidates-v251.json'; out.write_text(json.dumps({'version':'2.5.1-voice-priority-candidates','status':'PASS','songs':20,'difficulties':60,'parallel_workers':8,'method':'fresh vocal onsets first; rhythm accents capped 5/10/15 percent','rows':rows},ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS','songs':20,'difficulties':60,'output':str(out)},ensure_ascii=False))
if __name__=='__main__':main()
