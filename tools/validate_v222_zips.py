#!/usr/bin/env python3
from __future__ import annotations
import json, zipfile, sys
from pathlib import Path
ALLOWED={'_polymod_meta.json','data','images','scripts','shared','songs'}
def main():
 root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); delivery=root/'Mods .zip terminados'; zips=sorted(delivery.glob('Mod-*-V2.2.2.zip')); rows=[]
 for z in zips:
  issues=[]
  with zipfile.ZipFile(z) as q:
   bad=q.testzip(); names=[n.rstrip('/') for n in q.namelist() if n.rstrip('/')]; roots=sorted({n.split('/')[0] for n in names if n}); root_name=roots[0] if len(roots)==1 else None; top=sorted({n.split('/')[1] for n in names if '/' in n and n.split('/')[0]==root_name}) if root_name else []
   if bad: issues.append('crc:'+bad)
   if len(roots)!=1: issues.append('root_count')
   if root_name and any(x not in ALLOWED for x in top): issues.append('unexpected_top:'+','.join(x for x in top if x not in ALLOWED))
   if root_name and f'{root_name}/_polymod_meta.json' not in q.namelist(): issues.append('missing_manifest')
  rows.append({'zip':str(z.relative_to(root)),'size_bytes':z.stat().st_size,'root':root_name,'top_level':top,'status':'PASS' if not issues else 'ERROR','issues':issues})
 payload={'status':'PASS' if len(rows)==20 and all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','zips':len(rows),'rows':rows,'runtime_policy':sorted(ALLOWED)}; out=root/'qa-lab/rebuild-v222/zip-validation-v222.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'zips':len(rows),'errors':sum(r['status']!='PASS' for r in rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
