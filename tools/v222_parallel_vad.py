#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, math
from pathlib import Path
import numpy as np
import soundfile as sf

SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def resample(x,sr,target=16000):
    if sr==target: return x
    n=max(1,round(len(x)*target/sr)); old=np.linspace(0,1,len(x),endpoint=False); new=np.linspace(0,1,n,endpoint=False); return np.interp(new,old,x).astype(np.float32)

def one(root,song):
    mod=root/f'mods/esperon-dano-{song}'; meta=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-metadata.json').read_text()); player=meta['playData']['characters']['player']; path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=sf.read(path,always_2d=False,dtype='float32'); y=y.mean(axis=1) if getattr(y,'ndim',1)>1 else y; y=resample(y,int(sr)); frame=320; count=len(y)//frame; y=y[:count*frame]; rms=np.sqrt(np.mean(y.reshape(count,frame)**2,axis=1)+1e-12); sorted_rms=np.sort(rms); noise=float(np.median(sorted_rms[:max(1,int(count*0.2))])); threshold=float(max(0.015,noise*4.0)); mask=rms>=threshold; hang=max(1,round(0.2/(frame/16000))); padded=mask.copy();
    if hang>0:
        for i in np.flatnonzero(mask): padded[max(0,i-hang):min(len(mask),i+hang+1)]=True
    segments=[]; i=0
    while i<len(padded):
        if not padded[i]: i+=1; continue
        st=i
        while i<len(padded) and padded[i]: i+=1
        en=i; start=st*20; end=en*20
        if end-start>=120: segments.append({'start_ms':start,'end_ms':end,'duration_ms':end-start})
    onsets=[s['start_ms'] for s in segments]; out={'song':song,'audio':str(path.relative_to(root)),'sample_rate_hz':16000,'frame_ms':20,'noise_floor_rms':noise,'energy_threshold':threshold,'hangover_ms':200,'min_speech_ms':120,'duration_ms':round(len(y)/16,3),'segments':segments,'onsets_ms':onsets,'coverage_ratio':round(float(sum(s['duration_ms'] for s in segments)/max(1,len(y)/16)),6),'method':'CPU RMS VAD calibrated to lower-quintile noise floor; candidate evidence only'}; return out

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); outdir=root/'qa-lab/rebuild-v222/vad'; outdir.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(lambda s:one(root,s),SONGS))
    rows.sort(key=lambda x:x['song']);
    for r in rows: (outdir/f'{r["song"]}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    payload={'status':'PASS','songs':len(rows),'workers':4,'method':'audio-vad-cpu','rows':[{'song':r['song'],'segments':len(r['segments']),'onsets':len(r['onsets_ms']),'coverage_ratio':r['coverage_ratio'],'threshold':r['energy_threshold']} for r in rows]}; (root/'qa-lab/rebuild-v222/vad-summary.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'workers':4,'output':str(root/'qa-lab/rebuild-v222/vad-summary.json')},ensure_ascii=False))
if __name__=='__main__': main()
