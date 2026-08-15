#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def one(root:Path,song:str)->dict:
    mod=root/f"mods/esperon-dano-{song}"
    stem=root/f"sync-candidates/vocal-stems/{song}/vocals.wav"
    chart=root/f"sync-candidates/voice-aligned-charts/{song}/{song}-chart.json"
    out=root/f"sync-candidates/chart-vocal-candidate-comparisons/{song}.json"
    cmd=[sys.executable,str(root/'tools/compare_chart_audio.py'),str(root),'--mod',str(mod),'--vocal-stem',str(stem),'--chart',str(chart),'--output',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    return {'song':song,'returncode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip(),'output':str(out)}

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); outdir=root/'sync-candidates/chart-vocal-candidate-comparisons'; outdir.mkdir(parents=True,exist_ok=True)
    results=[]
    with ProcessPoolExecutor(max_workers=min(8,len(SONGS),os.cpu_count() or 2)) as pool:
        futs={pool.submit(one,root,s):s for s in SONGS}
        for fut in as_completed(futs):
            item=fut.result(); results.append(item); print(json.dumps(item,ensure_ascii=False),flush=True)
    results.sort(key=lambda x:x['song']); payload={'status':'PASS' if all(x['returncode']==0 for x in results) else 'ERRORS_FOUND','songs':len(results),'results':results,'evidence_only':True}
    out=root/'qa-lab/rebuild-v221/chart-vocal-candidate-comparison-summary.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':payload['status'],'songs':len(results),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
