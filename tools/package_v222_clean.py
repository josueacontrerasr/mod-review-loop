#!/usr/bin/env python3
from __future__ import annotations
import json, shutil, sys
from pathlib import Path
VERSION='2.2.2'; ALLOWED_ROOT_FILES={'_polymod_meta.json'}; ALLOWED_DIRS={'data','images','scripts','shared','songs'}
def write(p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve(); runtime=json.loads((root/'qa-lab/rebuild-v222/runtime-contract-v222.json').read_text()); visual=json.loads((root/'qa-lab/rebuild-v222/visual-redesign-v222.json').read_text()); charts=json.loads((root/'qa-lab/rebuild-v222/chart-promotion-v222.json').read_text());
 for x,n in ((runtime,20),(visual,20),(charts,20)):
  if x.get('status') not in ('PASS','APPLIED') or x.get('songs',x.get('mods'))!=n: raise RuntimeError('Gates V2.2.2 incompletos')
 delivery=root/'Mods .zip terminados'; delivery.mkdir(exist_ok=True); [p.unlink() for p in delivery.glob('*.zip')]; staging=root/'qa-lab/rebuild-v222/package-staging'; shutil.rmtree(staging,ignore_errors=True); staging.mkdir(parents=True,exist_ok=True); packages=[]
 for mod in sorted((root/'mods').glob('esperon-dano-*')):
  if not mod.is_dir(): continue
  dest=staging/mod.name; dest.mkdir()
  for p in mod.iterdir():
   if p.name in ALLOWED_ROOT_FILES: shutil.copy2(p,dest/p.name)
   elif p.name in ALLOWED_DIRS: shutil.copytree(p,dest/p.name)
  manifest=json.loads((dest/'_polymod_meta.json').read_text()); manifest['mod_version']=VERSION; manifest['description']=f'Mod FNF Mobile V-Slice 0.8.6 {mod.name.removeprefix("esperon-dano-")}: StageData/personajes reparados, flechas y carátula V2.2.2; chart cross-validado; requiere Audio Sync Test móvil.'; (dest/'_polymod_meta.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
  song=next((dest/'data/songs').iterdir()).name; display='-'.join(x[:1].upper()+x[1:] for x in song.split('-') if x); zip_path=delivery/f'Mod-{display}-V{VERSION}.zip'; shutil.make_archive(str(zip_path.with_suffix('')),'zip',root_dir=dest.parent,base_dir=dest.name); packages.append({'mod':mod.name,'song':song,'zip':str(zip_path.relative_to(root)),'version':VERSION})
 report={'status':'PASS','version':VERSION,'packages':packages,'runtime_policy':{'root_files':sorted(ALLOWED_ROOT_FILES),'directories':sorted(ALLOWED_DIRS),'auxiliary_files_excluded':True},'gates':{'runtime_contract':'PASS','visual_redesign':'PASS','chart_promotion':'APPLIED'}}; out=root/'qa-lab/rebuild-v222/package-manifest-v222.json'; write(out,report); print(json.dumps({'status':'PASS','version':VERSION,'packages':len(packages),'delivery':str(delivery),'report':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
