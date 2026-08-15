#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import librosa
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PREFIX='esperon-dano-'

def onset_times(path: Path):
    y,sr=librosa.load(path,sr=22050,mono=True)
    y=y[:int(min(len(y),sr*20))]
    onset_env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=256)
    frames=librosa.onset.onset_detect(onset_envelope=onset_env,sr=sr,hop_length=256,backtrack=False,pre_max=3,post_max=3,wait=5,delta=0.08)
    return librosa.frames_to_time(frames,sr=sr,hop_length=256).tolist()

def main():
    rows=[]
    for mod in sorted((ROOT/'mods').glob(PREFIX+'*')):
        if not mod.is_dir(): continue
        song=mod.name.removeprefix(PREFIX)
        chart=json.loads((mod/'data/songs'/song/f'{song}-chart.json').read_text())
        inst=mod/'songs'/song/'Inst.ogg'; vocals=list((mod/'songs'/song).glob('Voices-*.ogg'))
        inst_onsets=onset_times(inst) if inst.is_file() else []
        vocal_onsets=onset_times(vocals[0]) if vocals else []
        notes=chart.get('notes',{}).get('normal',[])
        first_chart=min((float(n['t']) for n in notes),default=None)
        rows.append({'song':song,'first_chart_ms':first_chart,'first_inst_onsets_s':inst_onsets[:8],'first_vocal_onsets_s':vocal_onsets[:8],'first_inst_onset_s':inst_onsets[0] if inst_onsets else None,'first_vocal_onset_s':vocal_onsets[0] if vocal_onsets else None,'chart_gap_after_first_inst_s':(first_chart/1000-inst_onsets[0]) if first_chart is not None and inst_onsets else None})
    out={'version':'2.4.0-intro-visibility','mods':len(rows),'rows':rows}
    path=ROOT/'qa-lab/rebuild-v240/intro-visibility-v240.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in rows: print(r['song'], 'chart_first_s=',None if r['first_chart_ms'] is None else round(r['first_chart_ms']/1000,3), 'inst=',[round(x,3) for x in r['first_inst_onsets_s'][:4]], 'vocal=',[round(x,3) for x in r['first_vocal_onsets_s'][:4]])
    print('output=',path)

if __name__=='__main__': main()
