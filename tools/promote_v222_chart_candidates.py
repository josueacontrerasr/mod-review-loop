#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='.'); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); root=Path(args.root).resolve(); before_dir=root/'qa-lab/rebuild-v222/production-charts-before'; before_dir.mkdir(parents=True,exist_ok=True); rows=[]
 for s in SONGS:
  mod=root/f'mods/esperon-dano-{s}'; songdir=next((mod/'data/songs').iterdir()); chart=songdir/f'{s}-chart.json'; cand=root/'qa-lab/rebuild-v222/candidate-charts'/s/f'{s}-chart-candidate.json'; inst=mod/f'songs/{s}/Inst.ogg'; voices=sorted((mod/f'songs/{s}').glob('Voices-*.ogg')); prod=json.loads(chart.read_text()); candidate=json.loads(cand.read_text()); before_chart=sha(chart); before_inst=sha(inst); before_voices=[sha(v) for v in voices];
  if prod.get('version')!=candidate.get('version') or set(prod.get('notes',{}))!=set(candidate.get('notes',{})): raise RuntimeError(f'{s}: candidate schema/difficulty mismatch')
  if args.apply: shutil.copy2(chart,before_dir/f'{s}-chart-before.json'); chart.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'); meta=json.loads((songdir/f'{s}-metadata.json').read_text()); meta['charter']='Manus AI — chart vocalmente alineado por onsets independientes; requiere Audio Sync Test móvil'; meta['generatedBy']='Friday Night Funkin\' - 0.8.6; V2.2.2 chart candidate cross-validated against independent vocal onsets'; (songdir/f'{s}-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
  after_chart=sha(chart); after_inst=sha(inst); after_voices=[sha(v) for v in voices]; rows.append({'song':s,'candidate':str(cand.relative_to(root)),'before_chart_sha256':before_chart,'after_chart_sha256':after_chart,'inst_sha256_unchanged':before_inst==after_inst,'voices_sha256_unchanged':before_voices==after_voices,'chart_changed':before_chart!=after_chart,'applied':args.apply})
 payload={'status':'APPLIED' if args.apply else 'DRY_RUN','songs':len(rows),'rows':rows,'policy':'Promoted after independent onset comparison and candidate integrity; BPM/timeChanges/audio/vocal files untouched. Audio Sync Test and mobile playtest remain required for human certification.'}; out=root/'qa-lab/rebuild-v222/chart-promotion-v222.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'charts_changed':sum(r['chart_changed'] for r in rows),'audio_unchanged':all(r['inst_sha256_unchanged'] and r['voices_sha256_unchanged'] for r in rows),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
