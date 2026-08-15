#!/usr/bin/env python3
from __future__ import annotations
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'qa-lab/rebuild-v266/playstate-fix/syllable-candidates-small'
CANON=ROOT/'qa-lab/rebuild-v266/playstate-fix/syllable-candidates'
BACKUP=ROOT/'qa-lab/rebuild-v266/playstate-fix/production-before-v266'

def main():
    rows=[]
    for mod in sorted((ROOT/'mods').glob('esperon-dano-*')):
        songs=sorted(mod.glob('data/songs/*/*-chart.json'))
        if len(songs)!=1: raise SystemExit(f'{mod}: expected one chart, found {len(songs)}')
        prod=songs[0]; song=prod.parent.name; cand=SOURCE/song/'candidate-chart.json'
        if not cand.is_file(): raise SystemExit(f'missing candidate {song}')
        old=json.loads(prod.read_text())
        backup=BACKUP/f'{song}-chart-before-v266.json'; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(prod,backup)
        chart=json.loads(cand.read_text())
        chart['generatedBy']="Friday Night Funkin' - 0.8.6; V2.6.6 vocal syllable vowel-mapped player lanes d=0..3"
        chart.pop('_candidate',None); chart.pop('candidateMetadata',None); chart.pop('analysisEvidence',None)
        prod.write_text(json.dumps(chart,ensure_ascii=False,indent=2)+'\n')
        canonical=CANON/song; canonical.mkdir(parents=True,exist_ok=True)
        for name in ('candidate-chart.json','syllable-alignment.json','candidate-report.json'):
            shutil.copy2(SOURCE/song/name, canonical/name)
        rows.append({'song':song,'production_chart':str(prod.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),'notes':{k:len(v) for k,v in chart['notes'].items()},'old_notes':{k:len(v) for k,v in old.get('notes',{}).items()}})
    report={'scope':'V266_SYLLABLE_CHART_PROMOTION','status':'PASS' if len(rows)==21 else 'FAIL','songs':len(rows),'source':'Whisper small + RMS refinement','rows':rows}
    out=ROOT/'qa-lab/rebuild-v266/playstate-fix/syllable-promotion-v266.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'songs':len(rows),'output':str(out)}))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
