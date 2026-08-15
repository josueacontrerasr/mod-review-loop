#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
base=json.loads((ROOT/'qa-lab/rebuild-v260/baseline-v260.json').read_text()); rows=[]; issues=[]
for b in base['rows']:
 song=b['song']; mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); audio=mod/'songs'/song; chart=sd/f'{song}-chart.json'; meta=sd/f'{song}-metadata.json'; voices=sorted(audio.glob('Voices-*.ogg'))
 row={'song':song,'chart_before':b['chart_sha256'],'chart_after':sha(chart),'metadata_before':b['metadata_sha256'],'metadata_after':sha(meta),'inst_before':b['inst_sha256'],'inst_after':sha(audio/'Inst.ogg'),'voices_before':b['voice_shas'],'voices_after':{p.name:sha(p) for p in voices}}
 if row['chart_before']!=row['chart_after']: issues.append(f'{song}:chart_changed')
 if row['metadata_before']!=row['metadata_after']: issues.append(f'{song}:metadata_changed')
 if row['inst_before']!=row['inst_after']: issues.append(f'{song}:inst_changed')
 if row['voices_before']!=row['voices_after']: issues.append(f'{song}:voices_changed')
 rows.append(row)
payload={'version':'2.6.0-regression','status':'PASS' if not issues else 'REGRESSION_FOUND','songs':len(rows),'issues':issues,'rows':rows,'decision':'NO_VERSION_BUMP_REQUIRED' if not issues else 'INVESTIGATE'}
out=ROOT/'qa-lab/rebuild-v260/regression-before-after-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'issues':len(issues),'output':str(out)},ensure_ascii=False)); raise SystemExit(0 if not issues else 1)
