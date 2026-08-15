from pathlib import Path
import json
import numpy as np
import librosa

ROOT=Path('/home/ubuntu/mod-review-loop-production')
D=json.loads((ROOT/'qa-lab/rebuild-v230/sync-pipeline-v230.json').read_text())

def times(y,sr,agg,delta,wait,hop,pre,post):
    env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop,aggregate=agg)
    fr=librosa.onset.onset_detect(onset_envelope=env,sr=sr,hop_length=hop,backtrack=True,units='frames',delta=delta,wait=wait,pre_max=pre,post_max=post)
    return [float(t*hop*1000/sr) for t in fr if t*hop*1000/sr>=300]

all_rows=[]
for row in D['rows']:
    song=row['song']; mod=ROOT/f'mods/esperon-dano-{song}'; meta=next((mod/'data/songs').iterdir())/f'{song}-metadata.json'; player=json.loads(meta.read_text())['playData']['characters']['player']; path=mod/f'songs/{song}/Voices-{player}.ogg'
    y,sr=librosa.load(path,sr=22050,mono=True); y44,sr44=librosa.load(path,sr=44100,mono=True)
    methods={
      'mean_gen': times(y,sr,np.mean,0.070,7,256,3,3),
      'max_gen': times(y,sr,np.max,0.100,10,256,3,3),
      'median_repair': times(y,sr,np.median,0.060,5,256,3,3),
      'verify_44k': times(y44,sr44,np.mean,0.075,6,512,4,4),
    }
    chart=json.loads((ROOT/row['output_chart']).read_text())
    for diff in ('easy','normal','hard'):
        notes=chart['notes'][diff]; counts=[]; errors={k:[] for k in methods}
        for n in notes:
            t=float(n['t']); hits=[]
            for k,vals in methods.items():
                e=min(abs(t-v) for v in vals) if vals else 999999
                errors[k].append(e); hits.append(e<=80)
            counts.append(sum(hits)>=2)
        all_rows.append({'song':song,'difficulty':diff,'notes':len(notes),'multi_method_within80':round(float(np.mean(counts)),6) if counts else 0,'methods':{k:{'median':round(float(np.median(v)),3),'p95':round(float(np.percentile(v,95)),3),'within80':round(float(np.mean(np.array(v)<=80)),6)} for k,v in errors.items()}})
for r in all_rows:
    print(r['song'],r['difficulty'],'multi=',r['multi_method_within80'],' '.join(f"{k}:w80={v['within80']},p95={v['p95']}" for k,v in r['methods'].items()))
print('all=',round(float(np.mean([r['multi_method_within80'] for r in all_rows])),6),'min=',min(r['multi_method_within80'] for r in all_rows))
(ROOT/'qa-lab/rebuild-v230/multimethod-consensus-audit-v230.json').write_text(json.dumps({'status':'PASS' if min(r['multi_method_within80'] for r in all_rows)>=0.90 else 'REVIEW_REQUIRED','rows':all_rows},ensure_ascii=False,indent=2)+'\n')
