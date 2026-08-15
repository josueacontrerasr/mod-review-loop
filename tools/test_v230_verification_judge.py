from pathlib import Path
import json
import numpy as np
import librosa

ROOT=Path('/home/ubuntu/mod-review-loop-production')
for song in ['arcoloria','solare','luma','meteora','fango','peligrosa']:
    mod=ROOT/f'mods/esperon-dano-{song}'
    meta=next((mod/'data/songs').iterdir())/f'{song}-metadata.json'
    player=json.loads(meta.read_text())['playData']['characters']['player']
    path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=librosa.load(path,sr=44100,mono=True)
    print(song,end=': ')
    for name,hop,delta,wait,agg in [('v1',512,0.075,6,np.mean),('v2',512,0.10,8,np.median),('v3',384,0.09,7,np.mean),('v4',1024,0.08,5,np.max)]:
        env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop,aggregate=agg)
        frames=librosa.onset.onset_detect(onset_envelope=env,sr=sr,hop_length=hop,backtrack=True,units='frames',delta=delta,wait=wait,pre_max=4,post_max=4)
        times=[float(t*hop*1000/sr) for t in frames if t*hop*1000/sr>=300]
        print(f'{name}={len(times)}',end=' ')
    print()
