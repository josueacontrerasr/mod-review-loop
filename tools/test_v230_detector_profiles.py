from pathlib import Path
import librosa
import soundfile as sf
import numpy as np

ROOT=Path('/home/ubuntu/mod-review-loop-production')
SONGS=['arcoloria','solare','luma','meteora','fango']
PROFILES=[('low',0.06,5),('medium',0.09,8),('high',0.12,12),('strict',0.16,16)]
for song in SONGS:
    mod=ROOT/f'mods/esperon-dano-{song}'
    meta=next((mod/'data/songs').iterdir())/f'{song}-metadata.json'
    import json
    player=json.loads(meta.read_text())['playData']['characters']['player']
    path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=librosa.load(path,sr=22050,mono=True)
    print(song, end=': ')
    for name,delta,wait in PROFILES:
        env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=256,aggregate=np.median)
        frames=librosa.onset.onset_detect(onset_envelope=env,sr=sr,hop_length=256,backtrack=True,units='frames',delta=delta,wait=wait,pre_max=3,post_max=3)
        times=[float(t*256*1000/sr) for t in frames if t*256*1000/sr>=300]
        print(f'{name}={len(times)}',end=' ')
    print()
