#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
EVID=ROOT/'qa-lab/rebuild-v260'
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def read_json(p): return json.loads(p.read_text(encoding='utf-8'))
def resolve_asset(mod, asset):
    if not isinstance(asset,str): return None
    if asset.startswith('shared:') or asset.startswith(('characters/','stages/','notes/','ui/')): return mod/'shared'/'images'/asset.removeprefix('shared:')
    return mod/'images'/asset

def atlas(mod, asset):
    base=resolve_asset(mod,asset)
    if base is None: return {'png':False,'xml':False,'frames':[],'error':'assetPath_missing'}
    png=base.with_suffix('.png'); xml=base.with_suffix('.xml'); frames=[]; err=None
    try:
        if xml.is_file(): frames=[n.attrib.get('name','') for n in ET.parse(xml).getroot().findall('.//SubTexture')]
    except Exception as exc: err=str(exc)
    return {'png':png.is_file(),'xml':xml.is_file(),'frames':frames,'error':err,'path':str(base.relative_to(mod))}

def has_prefix(frames,prefix): return any(x==prefix or x.startswith(prefix) for x in frames)

def one(song):
    mod=ROOT/'mods'/f'esperon-dano-{song}'; issues=[]; warnings=[]; counts={}
    all_files=list(p for p in mod.rglob('*') if p.is_file())
    for p in all_files:
        try:
            if p.suffix.lower()=='.json': read_json(p)
            elif p.suffix.lower()=='.xml': ET.parse(p)
            elif p.suffix.lower()=='.png':
                with Image.open(p) as im: im.verify()
            elif p.suffix.lower()=='.ogg' and p.read_bytes()[:4]!=b'OggS': issues.append(f'bad_ogg_header:{p.relative_to(mod)}')
        except Exception as exc: issues.append(f'parse:{p.relative_to(mod)}:{exc}')
    try:
        manifest=read_json(mod/'_polymod_meta.json');
        if manifest.get('api_version')!='0.8.6': issues.append('api_version')
        if manifest.get('mod_version')!='2.5.1': warnings.append('mod_version_not_bumped_to_v260')
        sd=next((mod/'data/songs').iterdir()); meta=read_json(sd/f'{song}-metadata.json'); chart=read_json(sd/f'{song}-chart.json')
        if meta.get('version')!='2.2.4': issues.append('metadata_version')
        if chart.get('version')!='2.0.0': issues.append('chart_version')
        play=meta.get('playData',{}); chars=play.get('characters',{})
        if not isinstance(chars.get('playerVocals'),list) or not chars.get('playerVocals'): issues.append('player_vocals_missing')
        if play.get('stage')!=f'escenario-{song}': issues.append('stage_id')
        if play.get('noteStyle')!=f'esperon-{song}-notes': issues.append('note_style_id')
        if set(chart.get('notes',{}))!={'easy','normal','hard'}: issues.append('difficulty_set')
        for diff in ('easy','normal','hard'):
            notes=chart.get('notes',{}).get(diff,[]); keys=[(round(float(n.get('t',-1)),3),int(n.get('d',-1))) for n in notes]; counts[diff]=len(notes)
            if not notes: issues.append(f'empty:{diff}')
            if keys!=sorted(keys): issues.append(f'unsorted:{diff}')
            if len(keys)!=len(set(keys)): issues.append(f'duplicate:{diff}')
            if any(t<0 or d<0 or d>3 for t,d in keys): issues.append(f'lane_domain:{diff}')
        if not (counts['easy']<counts['normal']<counts['hard']): issues.append('density_order')
        stage=read_json(mod/'data/stages'/f'{play["stage"]}.json');
        if stage.get('directory')!='shared': issues.append('stage_directory')
        if set(stage.get('characters',{}))!={'bf','dad','gf'}: issues.append('stage_character_map')
        for prop in stage.get('props',[]):
            a=prop.get('assetPath',''); info=atlas(mod,a)
            if not info['png'] or info['error']: issues.append(f'stage_asset:{a}')
            if prop.get('animations') and not info['xml']: issues.append(f'stage_animation_xml:{a}')
        for role in ('player','opponent'):
            cid=chars.get(role); cpath=mod/'data/characters'/f'{cid}.json'; char=read_json(cpath); info=atlas(mod,char.get('assetPath'))
            if not info['png'] or not info['xml'] or info['error']: issues.append(f'character_atlas:{role}')
            for anim in char.get('animations',[]):
                if not has_prefix(info['frames'],anim.get('prefix','')): issues.append(f'character_prefix:{role}:{anim.get("prefix")}')
        style=read_json(mod/'data/notestyles'/f'{play["noteStyle"]}.json')
        if style.get('version')!='1.0.0': issues.append('note_style_version')
        if style.get('fallback')!='funkin': issues.append('note_style_fallback')
        for group in ('note','noteStrumline'):
            spec=style.get('assets',{}).get(group,{}); info=atlas(mod,spec.get('assetPath'))
            if not info['png'] or not info['xml'] or info['error']: issues.append(f'note_style_atlas:{group}')
            for dat in spec.get('data',{}).values():
                if isinstance(dat,dict) and not has_prefix(info['frames'],dat.get('prefix','')): issues.append(f'note_style_prefix:{group}:{dat.get("prefix")}')
        album_id=play.get('album'); album=read_json(mod/'data/ui/freeplay/albums'/f'{album_id}.json')
        for key in ('albumArtAsset','albumTitleAsset'):
            asset=album.get(key,'')
            if not isinstance(asset,str) or not asset.startswith('freeplay/albumRoll/'): issues.append(f'album_path:{key}')
            info=atlas(mod,asset)
            if not info['png']: issues.append(f'album_png:{key}')
            if key=='albumTitleAsset' and (not info['xml'] or 'idle0000' not in info['frames'] or 'switch0000' not in info['frames']): issues.append('album_title_frames')
        audio=mod/'songs'/song
        if not (audio/'Inst.ogg').is_file() or not list(audio.glob('Voices-*.ogg')): issues.append('audio_missing')
    except Exception as exc: issues.append(f'contract_exception:{exc}')
    return {'song':song,'status':'PASS' if not issues else 'ERROR','issues':issues,'warnings':warnings,'file_count':len(all_files),'counts':counts}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=sorted(ex.map(one,SONGS),key=lambda x:x['song'])
    payload={'version':'2.6.0-general-audit','status':'PASS' if all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','songs':20,'parallel_workers':8,'rows':rows,'summary':{'passed':sum(r['status']=='PASS' for r in rows),'errors':sum(r['status']!='PASS' for r in rows),'warnings':sum(len(r['warnings']) for r in rows)}}
    out=EVID/'general-audit-v260.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'passed':payload['summary']['passed'],'errors':payload['summary']['errors'],'warnings':payload['summary']['warnings'],'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
