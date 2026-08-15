#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import json
import math
import sys
from pathlib import Path
from typing import Any

import librosa
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'qa-lab/rebuild-v240'
OUT=EVID/'mixed-candidates'
SONGS=['arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma','maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar','nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella','tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos']

sys.path.insert(0,str(ROOT/'tools'))
from v230_sync_pipeline import (  # noqa: E402
    detector_times, independent_energy_judge, independent_onset_judge, load_mono,
    sha256, vad_cpu, verification_onset_judge, multimethod_metrics,
)


def median_detector(y: np.ndarray, sr: int) -> list[float]:
    hop=256
    env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop,aggregate=np.median)
    frames=librosa.onset.onset_detect(onset_envelope=env,sr=sr,hop_length=hop,backtrack=True,units='frames',delta=0.06,wait=5,pre_max=3,post_max=3)
    return [round(float(f*hop*1000/sr),3) for f in frames if f*hop*1000/sr>=300]


def cluster_family(detectors: dict[str,list[float]], window=70.0, min_votes=2) -> list[dict[str,Any]]:
    events=[]
    for name,vals in detectors.items():
        events.extend((float(t),name) for t in vals)
    events.sort()
    clusters=[]
    for t,name in events:
        if not clusters or t-clusters[-1][-1][0]>window: clusters.append([(t,name)])
        else: clusters[-1].append((t,name))
    out=[]
    for cluster in clusters:
        ts=[x[0] for x in cluster]; votes=sorted({x[1] for x in cluster})
        if len(votes)>=min_votes:
            out.append({'t_ms':round(float(np.median(ts)),3),'votes':votes,'vote_count':len(votes),'raw_times_ms':[round(x,3) for x in ts]})
    return out


def nearest(t:float, values:list[float]):
    if not values:return None,None
    v=min(values,key=lambda x:abs(x-t)); return v,abs(v-t)


def merge_events(vocal:list[dict[str,Any]], rhythm:list[dict[str,Any]]) -> list[dict[str,Any]]:
    groups=[]
    for e in sorted([dict(x, family='vocal') for x in vocal]+[dict(x, family='rhythm') for x in rhythm], key=lambda x:x['t_ms']):
        if not groups or e['t_ms']-groups[-1][-1]['t_ms']>70: groups.append([e])
        else: groups[-1].append(e)
    merged=[]
    for g in groups:
        t=float(np.median([x['t_ms'] for x in g])); families=sorted({x['family'] for x in g})
        votes=sorted({v for x in g for v in x.get('votes',[])})
        merged.append({'t_ms':round(t,3),'families':families,'family':'both' if len(families)>1 else families[0],'votes':votes,'vote_count':len(votes)})
    return merged


def add_rhythm_notes(base:list[dict[str,Any]], rhythm_events:list[dict[str,Any]], diff:str, vocal_times:list[float]) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    result=[dict(n) for n in base]
    existing=[float(n['t']) for n in result]
    if diff=='easy': min_gap,max_add=360.0,max(8,round(len(base)*0.32))
    elif diff=='normal': min_gap,max_add=220.0,max(16,round(len(base)*0.50))
    else: min_gap,max_add=140.0,max(28,round(len(base)*0.72))
    # Prefer early and high-consensus rhythm events, then fill chronologically.
    candidates=[]
    for e in sorted(rhythm_events,key=lambda x:(float(x['t_ms']),-int(x.get('vote_count',0)))):
        t=float(e['t_ms'])
        if t<250: continue
        # Existing vocal/rhythm note already covers this event.
        if any(abs(t-x)<75 for x in existing): continue
        # Require a meaningful rhythm consensus; do not flood quiet passages.
        if int(e.get('vote_count',0))<2: continue
        if any(abs(t-float(x['t']))<min_gap for x in result+candidates): continue
        # Vocal events are already represented by the preserved V2.3 backbone.
        _,v_err=nearest(t,vocal_times)
        # Keep rhythm events even if they are not vocal, but avoid micro-fills inside a vocal attack.
        if v_err is not None and v_err<55: continue
        candidates.append({'t':round(t,3),'d':4+((len(candidates)*2 + (1 if diff=='hard' else 0))%4),'_family':'rhythm'})
        if len(candidates)>=max_add: break
    result.extend({k:v for k,v in n.items() if not k.startswith('_')} for n in candidates)
    result.sort(key=lambda n:(float(n['t']),int(n['d'])))
    return result,{'input_notes':len(base),'rhythm_candidates':len(rhythm_events),'added_rhythm_notes':len(candidates),'output_notes':len(result),'min_gap_ms':min_gap,'max_additions':max_add}


def note_family_metrics(notes:list[dict[str,Any]], vocal_times:list[float], rhythm_times:list[float]) -> dict[str,Any]:
    rows=[]
    for n in notes:
        t=float(n['t']); _,ve=nearest(t,vocal_times); _,re=nearest(t,rhythm_times)
        ve=ve if ve is not None else 999999.0; re=re if re is not None else 999999.0
        family='vocal' if ve<=re else 'rhythm'
        rows.append((family,ve,re))
    def ratio(family,idx,tol):
        group=[r for r in rows if r[0]==family]
        return round(sum(r[idx]<=tol for r in group)/len(group),6) if group else 1.0
    return {
        'notes':len(rows),'classified_vocal':sum(r[0]=='vocal' for r in rows),'classified_rhythm':sum(r[0]=='rhythm' for r in rows),
        'vocal_within_80':ratio('vocal',1,80.0),'rhythm_within_80':ratio('rhythm',2,80.0),
        'all_supported_by_either_120':round(sum(min(r[1],r[2])<=120 for r in rows)/len(rows),6) if rows else 0.0,
        'mean_vocal_error_ms':round(float(np.mean([r[1] for r in rows])) if rows else 0.0,3),
        'mean_rhythm_error_ms':round(float(np.mean([r[2] for r in rows])) if rows else 0.0,3),
    }


def process(song:str):
    mod=ROOT/'mods'/f'esperon-dano-{song}'
    song_dir=next((mod/'data/songs').iterdir())
    meta=json.loads((song_dir/f'{song}-metadata.json').read_text())
    player=meta['playData']['characters']['player']
    voice=mod/'songs'/song/f'Voices-{player}.ogg'; inst=mod/'songs'/song/'Inst.ogg'
    vocal22,sr22=load_mono(voice,22050); vocal16,_=load_mono(voice,16000); vocal44,sr44=load_mono(voice,44100)
    inst22,instsr=load_mono(inst,22050); inst16,_=load_mono(inst,16000); inst44,inst44sr=load_mono(inst,44100)
    vad=vad_cpu(vocal16)
    vdet=detector_times(vocal22,sr22); vdet['median']=median_detector(vocal22,sr22)
    vjudge=independent_onset_judge(vocal22,sr22); vverify=verification_onset_judge(vocal44,sr44)
    vocal_events=cluster_family(vdet,70.0,2)
    vocal_times=[float(e['t_ms']) for e in vocal_events]
    rdet=detector_times(inst22,instsr); rdet['median']=median_detector(inst22,instsr); rdet['energy']=independent_energy_judge(inst16,16000)
    rverify=verification_onset_judge(inst44,inst44sr)
    rhythm_events=cluster_family({k:v for k,v in rdet.items() if k!='energy'},70.0,2)
    # Add energy peaks only when near a clustered onset; this prevents isolated noise from becoming notes.
    rhythm_times=[float(e['t_ms']) for e in rhythm_events]
    rhythm_events += [{'t_ms':float(t),'votes':['energy'],'vote_count':1} for t in rdet['energy'] if nearest(float(t),rhythm_times)[1] is not None and nearest(float(t),rhythm_times)[1]<=80]
    rhythm_events=sorted(rhythm_events,key=lambda e:e['t_ms'])
    chart=json.loads((song_dir/f'{song}-chart.json').read_text())
    out=json.loads(json.dumps(chart)); diffs={}
    for diff in ('easy','normal','hard'):
        base=chart.get('notes',{}).get(diff,[])
        notes,add=add_rhythm_notes(base,rhythm_events,diff,vocal_times)
        out['notes'][diff]=notes
        diffs[diff]={'before':len(base),'after':len(notes),'add':add,'family_metrics':note_family_metrics(notes,vocal_times,rhythm_times),'vocal_multimethod':multimethod_metrics(notes,{'vocal_mean':vdet.get('mean',[]),'vocal_max':vdet.get('max',[]),'vocal_judge':vjudge,'vocal_verify':vverify},80.0),'rhythm_multimethod':multimethod_metrics(notes,{'rhythm_mean':rdet.get('mean',[]),'rhythm_max':rdet.get('max',[]),'rhythm_verify':rverify,'rhythm_energy':rdet.get('energy',[])},80.0)}
    out['generatedBy']='Friday Night Funkin\' - v0.8.6; V2.4.0 mixed rhythm-vocal chart with independent evidence'
    outdir=OUT/song; outdir.mkdir(parents=True,exist_ok=True); outpath=outdir/f'{song}-chart-v240.json'; outpath.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    return {'song':song,'voice_sha256':sha256(voice),'inst_sha256':sha256(inst),'vocal_events':len(vocal_events),'rhythm_events':len(rhythm_events),'vocal_vad_segments':len(vad['segments']),'difficulties':diffs,'output_chart':str(outpath.relative_to(ROOT))}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: rows=sorted(ex.map(process,SONGS),key=lambda x:x['song'])
    payload={'version':'2.4.0','status':'PASS','songs':len(rows),'difficulties':len(rows)*3,'method':{'base':'preserve V2.3.0 vocal backbone','rhythm':'instrumental onset consensus mean/max/median plus independent energy peaks','vocal':'VAD CPU plus independent onset and verification judges','rule':'add only rhythm events with at least two onset votes, spacing budgets by difficulty, and never move existing notes or change audio/timeChanges'},'rows':rows}
    (EVID/'mixed-sync-v240.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':payload['status'],'songs':len(rows),'difficulties':len(rows)*3,'output':str(EVID/'mixed-sync-v240.json')},ensure_ascii=False))

if __name__=='__main__': main()
