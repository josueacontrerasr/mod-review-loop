from pathlib import Path
import json
import numpy as np
import librosa
from scipy.signal import find_peaks

ROOT=Path('/home/ubuntu/mod-review-loop-production')
for song in ['arcoloria','solare','luma','meteora','fango']:
    mod=ROOT/f'mods/esperon-dano-{song}'
    meta=next((mod/'data/songs').iterdir())/f'{song}-metadata.json'
    player=json.loads(meta.read_text())['playData']['characters']['player']
    path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=librosa.load(path,sr=16000,mono=True)
    hop=160; frame=320
    rms=librosa.feature.rms(y=y,frame_length=frame,hop_length=hop,center=False)[0]
    log=np.log(rms+1e-5)
    deriv=np.maximum(0,np.diff(log,prepend=log[0]))
    print(song,end=': ')
    for name,prom,dist in [('p1',0.03,5),('p2',0.05,8),('p3',0.08,10),('p4',0.12,12)]:
        peaks,_=find_peaks(deriv,prominence=prom,distance=dist)
        times=[]
        for p in peaks:
            start=max(0,p-20); q=start+int(np.argmin(log[start:p+1])); t=q*hop*1000/sr
            if t>=300: times.append(t)
        # collapse within 70ms
        out=[]
        for t in times:
            if not out or t-out[-1]>70: out.append(t)
        print(f'{name}={len(out)}',end=' ')
    print()
