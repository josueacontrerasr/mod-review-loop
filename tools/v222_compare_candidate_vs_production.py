#!/usr/bin/env python3
from __future__ import annotations
import json,statistics
from pathlib import Path

def eval_chart(chart,ons):
 out={}
 for diff,notes in chart.get('notes',{}).items():
  player=[n for n in notes if int(n.get('d',0))>=4]; errs=[min(abs(float(n.get('t',0))-o) for o in ons) for n in player] if player and ons else []
  out[diff]={'notes':len(player),'mean_ms':round(statistics.mean(errs),3) if errs else None,'median_ms':round(statistics.median(errs),3) if errs else None,'within_80ms':round(sum(e<=80 for e in errs)/len(errs),6) if errs else None,'within_120ms':round(sum(e<=120 for e in errs)/len(errs),6) if errs else None,'max_ms':round(max(errs),3) if errs else None}
 return out

def main():
 root=Path('/home/ubuntu/mod-review-loop-production'); song='luma'; mod=root/f'mods/esperon-dano-{song}'; prod=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-chart.json').read_text()); cand=json.loads((root/'qa-lab/rebuild-v222/candidate-charts/luma/luma-chart-candidate.json').read_text()); ons=json.loads((root/'qa-lab/rebuild-v222/independent-onsets/luma.json').read_text())['onsets_ms']; payload={'song':song,'production':eval_chart(prod,ons),'candidate':eval_chart(cand,ons),'status':'REVIEW_ONLY'}; out=root/'qa-lab/rebuild-v222/luma-candidate-vs-production.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(payload,ensure_ascii=False))
if __name__=='__main__': main()
