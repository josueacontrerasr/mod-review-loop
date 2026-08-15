#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json
from pathlib import Path
import librosa, numpy as np
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def one(root,song):
 mod=root/f'mods/esperon-dano-{song}'; meta=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-metadata.json').read_text()); player=meta['playData']['characters']['player']; path=mod/f'songs/{song}/Voices-{player}.ogg'; y,sr=librosa.load(path,sr=22050,mono=True); hop=256; onset_env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop,aggregate=np.median); frames=librosa.onset.onset_detect(onset_envelope=onset_env,sr=sr,hop_length=hop,backtrack=True,units='frames',pre_max=3,post_max=3,delta=0.06,wait=5); times=[round(float(t*hop*1000/sr),3) for t in frames if t*hop*1000/sr>=800]; return {'song':song,'audio':str(path.relative_to(root)),'sr':sr,'hop':hop,'onsets_ms':times,'method':'independent librosa onset_strength median aggregate, backtrack, delta .06, wait 5'}
def main():
 root=Path('/home/ubuntu/mod-review-loop-production'); out=root/'qa-lab/rebuild-v222/independent-onsets'; out.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(lambda s:one(root,s),SONGS))
 rows.sort(key=lambda x:x['song']);
 for r in rows: (out/f'{r["song"]}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 payload={'status':'PASS','songs':len(rows),'workers':4,'rows':[{'song':r['song'],'onsets':len(r['onsets_ms'])} for r in rows]}; (root/'qa-lab/rebuild-v222/independent-onsets-summary.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS','songs':len(rows),'output':str(root/'qa-lab/rebuild-v222/independent-onsets-summary.json')},ensure_ascii=False))
if __name__=='__main__': main()
