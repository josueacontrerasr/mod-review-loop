#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def main():
 rows=[]; issues=[]
 for song in SONGS:
  mod=ROOT/'mods'/f'esperon-dano-{song}'; p=mod/'_polymod_meta.json'; data=json.loads(p.read_text()); before=data.get('mod_version'); data['mod_version']='2.5.1'; desc=str(data.get('description','')).replace('V2.5.0','V2.5.1'); data['description']=desc; p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); rows.append({'song':song,'before':before,'after':data['mod_version']})
 payload={'version':'2.5.1-meta-bump','status':'PASS' if len(rows)==20 and all(r['after']=='2.5.1' for r in rows) else 'ERRORS_FOUND','mods':len(rows),'rows':rows,'issues':issues}
 out=ROOT/'qa-lab/rebuild-v250/metadata-bump-v251.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'mods':len(rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
