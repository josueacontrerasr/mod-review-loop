from pathlib import Path
import json
import numpy as np
import librosa
from scipy.signal import find_peaks

ROOT=Path('/home/ubuntu/mod-review-loop-production')
D=json.loads((ROOT/'qa-lab/rebuild-v230/sync-pipeline-v230.json').read_text())

def metrics(notes, peaks):
    errs=[]
    for n in notes:
        if not peaks: continue
        errs.append(min(abs(float(n['t'])-p) for p in peaks))
    a=np.array(errs)
    return float(np.median(a)),float(np.percentile(a,95)),float(np.mean(a<=80)),float(np.max(a))

for row in D['rows']:
    song=row['song']; mod=ROOT/f'mods/esperon-dano-{song}'; meta=next((mod/'data/songs').iterdir())/f'{song}-metadata.json'; player=json.loads(meta.read_text())['playData']['characters']['player']; path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=librosa.load(path,sr=22050,mono=True)
    print(song,end=': ')
    for name,frame,hop,prom,dist in [('e1',512,256,0.02,4),('e2',1024,256,0.04,6),('e3',1024,256,0.08,8),('e4',2048,256,0.06,10)]:
        rms=librosa.feature.rms(y=y,frame_length=frame,hop_length=hop,center=True)[0]
        log=np.log(rms+1e-5)
        diff=np.maximum(0,np.diff(log,prepend=log[0]))
        peaks,_=find_peaks(diff,prominence=prom,distance=dist)
        times=[float(p*hop*1000/sr) for p in peaks if p*hop*1000/sr>=300]
        # use the finished normal chart from V2.3.0 output
        chart=json.loads((ROOT/row['output_chart']).read_text())
        m=metrics(chart['notes']['normal'],times)
        print(f'{name}=count{len(times)}/med{m[0]:.1f}/p95{m[1]:.1f}/w80{m[2]:.2f}',end=' ')
    print()
