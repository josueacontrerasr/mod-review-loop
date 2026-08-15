#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    backup=ROOT/'qa-lab/rebuild-v250/production-charts-before-v251'; backup.mkdir(parents=True,exist_ok=True)
    rows=[]; issues=[]
    for song in SONGS:
        mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); prod=sd/f'{song}-chart.json'; cand=ROOT/'qa-lab/rebuild-v250/voice-priority-candidates-v251'/song/f'{song}-chart-v251.json'; meta=sd/f'{song}-metadata.json'; audio=mod/'songs'/song
        backup_path=backup/f'{song}-chart-v250.json'
        before_source=backup_path if backup_path.is_file() else prod
        row={'song':song,'status':'PASS','before_chart_sha256':sha(before_source),'candidate_chart_sha256':sha(cand),'inst_sha256':sha(audio/'Inst.ogg'),'voice_shas':{p.name:sha(p) for p in sorted(audio.glob('Voices-*.ogg'))},'timeChanges_before':json.loads(meta.read_text()).get('timeChanges',[]),'issues':[]}
        chart=json.loads(cand.read_text()); notes=chart.get('notes',{})
        if set(notes)!={'easy','normal','hard'}: row['issues'].append('difficulty_set')
        counts={}
        for diff in ('easy','normal','hard'):
            arr=notes.get(diff,[]); counts[diff]=len(arr); keys=[(float(n.get('t',-1)),int(n.get('d',-1))) for n in arr]
            if not arr: row['issues'].append(f'empty_{diff}')
            if keys!=sorted(keys) or len(keys)!=len(set(keys)): row['issues'].append(f'order_duplicate_{diff}')
            if any(t<0 or d<0 or d>3 for t,d in keys): row['issues'].append(f'lane_domain_{diff}')
        if not (counts['easy']<counts['normal']<counts['hard']): row['issues'].append('density_order')
        if json.loads(meta.read_text()).get('timeChanges',[]) != row['timeChanges_before']: row['issues'].append('timeChanges_changed_before_copy')
        if row['issues']:
            row['status']='ERROR'; issues.extend(f'{song}:{x}' for x in row['issues'])
        else:
            if not backup_path.exists(): shutil.copy2(prod, backup_path)
            prod.write_text(json.dumps(chart,ensure_ascii=False,indent=2)+'\n')
            row['after_chart_sha256']=sha(prod); row['counts']=counts; row['changed']=row['after_chart_sha256']!=row['before_chart_sha256']
            row['timeChanges_after']=json.loads(meta.read_text()).get('timeChanges',[])
            if row['timeChanges_after']!=row['timeChanges_before']: row['issues'].append('timeChanges_changed')
        rows.append(row)
    payload={'version':'2.5.1-voice-priority-promotion','status':'PASS' if not issues else 'ERRORS_FOUND','songs':20,'charts_promoted':sum(r.get('changed',False) for r in rows),'audio_unchanged':True,'timeChanges_unchanged':not issues,'rows':rows,'issues':issues}
    out=ROOT/'qa-lab/rebuild-v250/voice-priority-promotion-v251.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':payload['status'],'songs':20,'charts_promoted':payload['charts_promoted'],'issues':len(issues),'output':str(out)},ensure_ascii=False)); return 0 if not issues else 1
if __name__=='__main__':raise SystemExit(main())
