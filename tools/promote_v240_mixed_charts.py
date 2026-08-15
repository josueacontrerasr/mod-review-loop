#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFIX='esperon-dano-'
SONGS=['arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma','maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar','nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella','tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos']
DIFFS=['easy','normal','hard']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def validate(chart):
    issues=[]
    if chart.get('version')!='2.0.0': issues.append('chart_version')
    if list(chart.get('notes',{}))!=DIFFS: issues.append('difficulty_keys')
    for diff in DIFFS:
        notes=chart.get('notes',{}).get(diff,[])
        if not notes: issues.append(f'{diff}_empty')
        pairs=[]
        for n in notes:
            try: pairs.append((float(n['t']),int(n['d'])))
            except Exception: issues.append(f'{diff}_malformed')
        if pairs!=sorted(pairs): issues.append(f'{diff}_not_sorted')
        if any(t<0 or d<4 or d>7 for t,d in pairs): issues.append(f'{diff}_domain')
        if len(pairs)!=len(set(pairs)): issues.append(f'{diff}_duplicates')
    return sorted(set(issues))

def main():
    rows=[]
    backup=ROOT/'qa-lab/rebuild-v240/production-charts-before'; backup.mkdir(parents=True,exist_ok=True)
    for song in SONGS:
        mod=ROOT/'mods'/f'{PREFIX}{song}'
        chart_path=mod/'data/songs'/song/f'{song}-chart.json'
        candidate=ROOT/'qa-lab/rebuild-v240/mixed-candidates'/song/f'{song}-chart-v240.json'
        meta_path=mod/'data/songs'/song/f'{song}-metadata.json'
        audio=mod/'songs'/song/'Inst.ogg'; vocals=sorted((mod/'songs'/song).glob('Voices-*.ogg'))
        before=json.loads(chart_path.read_text(encoding='utf-8'))
        after=json.loads(candidate.read_text(encoding='utf-8')) if candidate.is_file() else {}
        issues=validate(after) if after else ['candidate_missing']
        before_hash=sha(chart_path); audio_before=sha(audio); vocal_before=[sha(x) for x in vocals]
        meta_before=json.loads(meta_path.read_text(encoding='utf-8'))
        backup_path=backup/f'{song}-chart-v230.json'; shutil.copy2(chart_path,backup_path)
        if not issues:
            chart_path.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:
            after=before
        after_hash=sha(chart_path); audio_after=sha(audio); vocal_after=[sha(x) for x in vocals]
        meta_after=json.loads(meta_path.read_text(encoding='utf-8'))
        counts={d:len(after.get('notes',{}).get(d,[])) for d in DIFFS}
        early={d:sum(float(n.get('t',0))<10000 for n in after.get('notes',{}).get(d,[])) for d in DIFFS}
        rows.append({'song':song,'status':'PASS' if not issues and audio_before==audio_after and vocal_before==vocal_after and meta_before.get('timeChanges')==meta_after.get('timeChanges') else 'ERROR','issues':issues,'production_chart':str(chart_path.relative_to(ROOT)),'backup_chart':str(backup_path.relative_to(ROOT)),'before_sha256':before_hash,'after_sha256':after_hash,'changed':before_hash!=after_hash,'audio_unchanged':audio_before==audio_after,'vocals_unchanged':vocal_before==vocal_after,'time_changes_unchanged':meta_before.get('timeChanges')==meta_after.get('timeChanges'),'counts':counts,'early_notes_under_10s':early})
    out={'version':'2.4.0-mixed-chart-promotion','status':'PASS' if len(rows)==20 and all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','mods':len(rows),'rows':rows}
    path=ROOT/'qa-lab/rebuild-v240/chart-promotion-v240.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'mods':len(rows),'changed':sum(r['changed'] for r in rows),'early_normal_notes':sum(r['early_notes_under_10s']['normal'] for r in rows),'output':str(path)},ensure_ascii=False))

if __name__=='__main__': main()
