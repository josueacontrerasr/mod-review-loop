#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFIX='esperon-dano-'

def main():
    rows=[]
    for mod in sorted((ROOT/'mods').glob(PREFIX+'*')):
        if not mod.is_dir(): continue
        song=mod.name.removeprefix(PREFIX)
        album_dirs=sorted((mod/'data/ui/freeplay/albums').glob('*.json'))
        if not album_dirs: rows.append({'song':song,'status':'ERROR','issues':['album_json_missing']}); continue
        album_path=album_dirs[0]; album=json.loads(album_path.read_text(encoding='utf-8'))
        changed=[]; issues=[]
        for key in ('albumArtAsset','albumTitleAsset'):
            value=album.get(key)
            if not isinstance(value,str) or not value:
                issues.append(f'{key}_missing'); continue
            # Official v0.8.6 AlbumRoll keys are relative to images/ and use freeplay/albumRoll.
            new_value=value.replace('freeplay/albums/','freeplay/albumRoll/')
            if not new_value.startswith('freeplay/albumRoll/'):
                stem=Path(value).name
                new_value=f'freeplay/albumRoll/{stem}'
            old_base=mod/'images'/value
            new_base=mod/'images'/new_value
            new_base.parent.mkdir(parents=True,exist_ok=True)
            for suffix in ('.png','.xml'):
                src=old_base.with_suffix(suffix); dst=new_base.with_suffix(suffix)
                if src.is_file(): shutil.copy2(src,dst); changed.append(str(dst.relative_to(mod)))
                elif suffix=='.png': issues.append(f'{key}_png_source_missing')
            album[key]=new_value
        album['generatedBy']='FNF Mobile V-Slice 0.8.6 V2.4.0 Freeplay contract repair'
        album_path.write_text(json.dumps(album,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        # Remove only the obsolete copies now that the corrected asset keys are in place.
        for old_value in [x for x in []]:
            pass
        # Derive old paths from the corrected keys and remove old albums only when they are distinct.
        for key in ('albumArtAsset','albumTitleAsset'):
            new_value=album[key]
            old_value=new_value.replace('freeplay/albumRoll/','freeplay/albums/')
            if old_value==new_value: continue
            old_base=mod/'images'/old_value
            for suffix in ('.png','.xml'):
                old_file=old_base.with_suffix(suffix)
                if old_file.is_file(): old_file.unlink()
        rows.append({'song':song,'status':'PASS' if not issues else 'ERROR','album_json':str(album_path.relative_to(ROOT)),'albumArtAsset':album.get('albumArtAsset'),'albumTitleAsset':album.get('albumTitleAsset'),'copied_assets':changed,'issues':issues})
    out={'version':'2.4.0-freeplay-repair','status':'PASS' if len(rows)==20 and all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','mods':len(rows),'rows':rows}
    path=ROOT/'qa-lab/rebuild-v240/freeplay-repair-v240.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'mods':len(rows),'copied_assets':sum(len(r.get('copied_assets',[])) for r in rows),'output':str(path)},ensure_ascii=False))

if __name__=='__main__': main()
