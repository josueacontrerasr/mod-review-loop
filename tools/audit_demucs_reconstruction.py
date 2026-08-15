#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path
import librosa, numpy as np

def probe(p:Path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=sample_rate,channels','-of','json',str(p)]))

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); rows=[]
    for mod in sorted((root/'mods').glob('esperon-dano-*')):
        song=next((mod/'data/songs').iterdir()).name; src=next(root.glob(f'Esperón*{song.replace("-"," ")}*.m4a'),None)
        # Use the stem evidence manifest for the exact source path when accents/case differ.
        ev=json.loads((root/f'sync-candidates/vocal-stems/{song}/stem-evidence.json').read_text()); src=root/ev['source_m4a']['path']
        demucs_dir=next((root/f'sync-candidates/vocal-stems/{song}/demucs-work/htdemucs').iterdir())
        vocal=demucs_dir/'vocals.wav'; instrumental=demucs_dir/'no_vocals.wav'
        reference_audio=mod/f'songs/{song}/Inst.ogg'
        a,sr=librosa.load(reference_audio,sr=22050,mono=True); v,_=librosa.load(vocal,sr=22050,mono=True); n,_=librosa.load(instrumental,sr=22050,mono=True)
        length=min(len(a),len(v),len(n)); a=a[:length]; recon=(v[:length]+n[:length]);
        corr=float(np.corrcoef(a,recon)[0,1]) if np.std(a)>0 and np.std(recon)>0 else 0.0
        rms=float(np.sqrt(np.mean(a*a))); residual=float(np.sqrt(np.mean((a-recon)**2)))
        rows.append({'song':song,'source_duration_s':float(probe(src)['format']['duration']),'vocal_duration_s':float(probe(vocal)['format']['duration']),'no_vocals_duration_s':float(probe(instrumental)['format']['duration']),'sample_rate':'22050_analysis','correlation':round(corr,6),'residual_rms_over_source_rms':round(residual/max(rms,1e-9),6),'source':str(src.relative_to(root)),'runtime_reference':str(reference_audio.relative_to(root)),'vocals':str(vocal.relative_to(root)),'no_vocals':str(instrumental.relative_to(root))})
    payload={'status':'PASS' if len(rows)==20 else 'ERRORS_FOUND','songs':len(rows),'rows':rows,'limitations':['Demucs reconstruction quality is not a human listening judgement.','The stems may contain bleeding or artifacts.','This audit does not certify semantic singer/strumline assignment.']}
    out=root/'qa-lab/rebuild-v221/demucs-reconstruction-audit.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
