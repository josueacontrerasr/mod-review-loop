#!/usr/bin/env python3
from __future__ import annotations
import json, sys, zipfile
from pathlib import Path

def main():
 root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); delivery=root/'Mods .zip terminados'; items=sorted(delivery.glob('Mod-*-V2.2.2.zip')); items=[p for p in items if p.name!='Mod-Esperon-Coleccion-V2.2.2.zip'];
 if len(items)!=20: raise SystemExit(f'Se esperaban 20 ZIPs individuales, encontrados {len(items)}')
 out=delivery/'Mod-Esperon-Coleccion-V2.2.2.zip'
 if out.exists(): out.unlink()
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in items: z.write(p,arcname=p.name)
 report={'status':'PASS','version':'2.2.2','individual_zips':len(items),'collection':str(out.relative_to(root)),'members':[p.name for p in items]}; rp=root/'qa-lab/rebuild-v222/collection-manifest-v222.json'; rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS','individual_zips':len(items),'collection':str(out),'size_bytes':out.stat().st_size,'report':str(rp)},ensure_ascii=False))
if __name__=='__main__': main()
