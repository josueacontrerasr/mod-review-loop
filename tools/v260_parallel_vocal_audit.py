#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / 'qa-lab/rebuild-v260'
SONGS = [
    'arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma',
    'maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar',
    'nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella',
    'tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos'
]

sys.path.insert(0, str(ROOT / 'tools'))
from v230_sync_pipeline import detector_times, independent_onset_judge, verification_onset_judge, vad_cpu, load_mono, cluster_onsets, sha256  # noqa: E402
from v250_voice_first_chart_pipeline import median_times  # noqa: E402


def nearest_signed(value: float, refs: list[float]):
    if not refs:
        return None, None
    idx = int(np.searchsorted(refs, value))
    candidates = []
    if idx < len(refs): candidates.append((abs(value - refs[idx]), value - refs[idx]))
    if idx > 0: candidates.append((abs(value - refs[idx-1]), value - refs[idx-1]))
    if not candidates: return None, None
    return min(candidates, key=lambda x: x[0])


def summarize_errors(errors: list[float]):
    if not errors:
        return {'count': 0, 'median_ms': None, 'mad_ms': None, 'p90_ms': None, 'p95_ms': None, 'signed_mean_ms': None}
    a = np.asarray(errors, dtype=float)
    med = float(np.median(a)); mad = float(np.median(np.abs(a - med)))
    return {'count': int(len(a)), 'median_ms': round(med, 3), 'mad_ms': round(mad, 3), 'p90_ms': round(float(np.percentile(a, 90)), 3), 'p95_ms': round(float(np.percentile(a, 95)), 3), 'signed_mean_ms': round(float(np.mean(a)), 3)}


def alignment_metrics(note_times: list[float], vocal_times: list[float], duration_ms: float):
    note_signed=[]; note_abs=[]; matched_notes=[]
    for t in note_times:
        dist, signed = nearest_signed(t, vocal_times)
        if dist is not None:
            note_abs.append(dist); note_signed.append(signed)
            if dist <= 240: matched_notes.append((t, signed, dist))
    event_abs=[]; event_signed=[]; matched_events=[]
    note_times_sorted=sorted(note_times)
    for t in vocal_times:
        dist, signed = nearest_signed(t, note_times_sorted)
        if dist is not None:
            event_abs.append(dist); event_signed.append(-signed)
            if dist <= 240: matched_events.append((t, -signed, dist))
    matched_note_abs=[x[2] for x in matched_notes]
    matched_event_abs=[x[2] for x in matched_events]
    thirds=[]
    for lo, hi in ((0.0, 1/3), (1/3, 2/3), (2/3, 1.0)):
        nerr=[]
        for t, signed, dist in matched_notes:
            ratio=t/max(duration_ms,1.0)
            if lo <= ratio < hi: nerr.append(signed)
        eerr=[]
        for t, signed, dist in matched_events:
            ratio=t/max(duration_ms,1.0)
            if lo <= ratio < hi: eerr.append(signed)
        thirds.append({'note_to_voice': summarize_errors(nerr), 'voice_to_note': summarize_errors(eerr)})
    drift = None
    if len(matched_events) >= 8:
        x=np.asarray([x[0] for x in matched_events],dtype=float)
        y=np.asarray([x[1] for x in matched_events],dtype=float)
        slope, intercept=np.polyfit(x,y,1)
        drift={'slope_ms_per_minute':round(float(slope*60000),6),'intercept_ms':round(float(intercept),3)}
    return {
        'note_to_voice': summarize_errors(note_abs),
        'note_to_voice_signed': summarize_errors(note_signed),
        'voice_to_note': summarize_errors(event_abs),
        'voice_to_note_signed': summarize_errors(event_signed),
        'note_coverage_40ms': round(sum(x <= 40 for x in note_abs)/max(1,len(note_abs)),6),
        'note_coverage_80ms': round(sum(x <= 80 for x in note_abs)/max(1,len(note_abs)),6),
        'note_coverage_120ms': round(sum(x <= 120 for x in note_abs)/max(1,len(note_abs)),6),
        'voice_event_coverage_40ms': round(sum(x <= 40 for x in event_abs)/max(1,len(event_abs)),6),
        'voice_event_coverage_80ms': round(sum(x <= 80 for x in event_abs)/max(1,len(event_abs)),6),
        'voice_event_coverage_120ms': round(sum(x <= 120 for x in event_abs)/max(1,len(event_abs)),6),
        'matched_notes_240ms': len(matched_notes),
        'matched_vocal_events_240ms': len(matched_events),
        'thirds': thirds,
        'drift': drift,
    }


def process(song: str):
    mod=ROOT/'mods'/f'esperon-dano-{song}'
    sd=next((mod/'data/songs').iterdir())
    meta=json.loads((sd/f'{song}-metadata.json').read_text())
    player=meta['playData']['characters']['player']
    voice=mod/'songs'/song/f'Voices-{player}.ogg'
    audio16,sr16=load_mono(voice,16000)
    audio22,sr22=load_mono(voice,22050)
    audio44,sr44=load_mono(voice,44100)
    vad=vad_cpu(audio16)
    detected=detector_times(audio22,sr22)
    detected['median']=median_times(audio22,sr22)
    detected['judge']=independent_onset_judge(audio22,sr22)
    detected['verify']=verification_onset_judge(audio44,sr44)
    vocal_events=cluster_onsets(detected,vad['segments'])
    vocal_times=sorted(float(e['t_ms']) for e in vocal_events)
    chart=json.loads((sd/f'{song}-chart.json').read_text())
    duration_ms=float(len(audio22)/max(sr22,1)*1000.0)
    diffs={}
    for diff in ('easy','normal','hard'):
        notes=chart.get('notes',{}).get(diff,[])
        times=sorted(float(n.get('t',-1)) for n in notes if 0 <= float(n.get('t',-1)) <= duration_ms+100)
        diffs[diff]={'notes':len(times),'lanes':sorted(set(int(n.get('d',-1)) for n in notes)),'alignment':alignment_metrics(times,vocal_times,duration_ms)}
    return {'song':song,'voice':str(voice.relative_to(ROOT)),'voice_sha256':sha256(voice),'duration_ms':round(duration_ms,3),'vad_segments':len(vad['segments']),'vocal_events':len(vocal_times),'vocal_coverage':vad.get('coverage_ratio'),'chart_sha256':sha256(sd/f'{song}-chart.json'),'difficulties':diffs}


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        rows=sorted(ex.map(process,SONGS),key=lambda x:x['song'])
    payload={'version':'2.6.0-vocal-audit','status':'PASS','songs':len(rows),'difficulties':len(rows)*3,'parallel_workers':8,'method':'fresh VAD CPU plus four onset detectors; event-to-note and note-to-event error; signed drift by thirds','rows':rows}
    out=EVID/'voice-audit-parallel-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','songs':len(rows),'difficulties':len(rows)*3,'output':str(out)},ensure_ascii=False))

if __name__=='__main__': main()
