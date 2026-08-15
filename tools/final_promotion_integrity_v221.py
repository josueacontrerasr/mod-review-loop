#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess
from pathlib import Path

def probe(p:Path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,sample_rate,channels','-of','json',str(p)]))

def main():
    root=Path('/home/ubuntu/mod-review-loop-production'); rows=[]; errors=[]
    for mod in sorted((root/'mods').glob('esperon-dano-*')):
        song=next((mod/'data/songs').iterdir()).name; meta=json.loads((mod/f'data/songs/{song}/{song}-metadata.json').read_text()); chart=json.loads((mod/f'data/songs/{song}/{song}-chart.json').read_text()); chars=meta['playData']['characters']; player=chars['player']; inst=mod/f'songs/{song}/Inst.ogg'; voices=mod/f'songs/{song}/Voices-{player}.ogg'
        issues=[]
        if chars.get('playerVocals') != [player]: issues.append(f'playerVocals={chars.get("playerVocals")}')
        if chars.get('opponentVocals') != []: issues.append(f'opponentVocals={chars.get("opponentVocals")}')
        for diff, notes in chart.get('notes',{}).items():
            if any(not (4 <= int(n.get('d',-1)) <= 7) for n in notes): issues.append(f'{diff} has non-player direction')
            if any(i and float(notes[i]['t']) < float(notes[i-1]['t']) for i in range(1,len(notes))): issues.append(f'{diff} unsorted')
        if not voices.is_file(): issues.append('missing Voices OGG')
        else:
            pi=probe(inst); pv=probe(voices); di=abs(float(pi['format']['duration'])-float(pv['format']['duration']))
            if di > 0.02: issues.append(f'duration_delta={di:.6f}s')
            for label,p in [('Inst',pi),('Voices',pv)]:
                if not p.get('streams') or p['streams'][0].get('codec_name') != 'vorbis': issues.append(f'{label} not vorbis')
            rows.append({'song':song,'player':player,'player_vocals':chars.get('playerVocals'),'chart_notes':{k:len(v) for k,v in chart.get('notes',{}).items()},'inst_duration_s':round(float(pi['format']['duration']),3),'voices_duration_s':round(float(pv['format']['duration']),3),'duration_delta_s':round(di,6),'issues':issues})
        if issues: errors.extend([f'{song}: {x}' for x in issues])
    payload={'status':'PASS' if len(rows)==20 and not errors else 'ERRORS_FOUND','mods':len(rows),'passed':sum(not r['issues'] for r in rows),'errors':errors,'rows':rows,'limitations':['Audio Sync Test y playtest móvil siguen siendo necesarios para confirmación humana final.']}
    out=root/'qa-lab/rebuild-v221/final-promotion-integrity-v221.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'mods':payload['mods'],'passed':payload['passed'],'errors':len(errors),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
