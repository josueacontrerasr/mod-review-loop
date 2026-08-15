#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='.'); ap.add_argument('--songs',nargs='+',required=True); ap.add_argument('--apply',action='store_true'); args=ap.parse_args(); root=Path(args.root).resolve(); rows=[]
    for song in args.songs:
        mod=root/f'mods/esperon-dano-{song}'; meta=json.loads(next((mod/'data/songs').iterdir()).joinpath(f'{song}-metadata.json').read_text()); chars=meta['playData']['characters']; changed=[]
        for role in ('player','opponent'):
            cid=chars[role]; path=mod/f'data/characters/{cid}.json'; d=json.loads(path.read_text()); old=d.get('assetPath',''); new=old.removeprefix('shared:'); exists=(mod/'shared/images'/f'{new}.png').is_file() and (mod/'shared/images'/f'{new}.xml').is_file();
            if args.apply and old!=new: d['assetPath']=new; d.setdefault('startingAnimation','idle'); d.setdefault('scale',1.0); d.setdefault('isPixel',False); d.setdefault('danceEvery',1.0); d.setdefault('singTime',8.0); path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
            changed.append({'role':role,'id':cid,'old_assetPath':old,'new_assetPath':new,'atlas_exists':exists,'changed':old!=new,'applied':args.apply and old!=new,'path':str(path.relative_to(root))})
        rows.append({'song':song,'characters':changed})
    out=root/'qa-lab/rebuild-v222/character-path-repair.json'; out.parent.mkdir(parents=True,exist_ok=True); payload={'status':'APPLIED' if args.apply else 'DRY_RUN','songs':len(rows),'rows':rows,'basis':'Paths.getSparrowAtlas(assetPath) in v0.8.6 resolves relative character assets through shared fallback; official character examples use characters/<id> without shared: prefix.'}; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'characters':sum(len(r['characters']) for r in rows),'changed':sum(x['changed'] for r in rows for x in r['characters']),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
