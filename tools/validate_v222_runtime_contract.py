#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, sys, xml.etree.ElementTree as ET
from pathlib import Path
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
def j(p): return json.loads(p.read_text())
def atlas(mod,asset):
 if not isinstance(asset,str): return None,[]
 base=(mod/'shared/images'/asset.removeprefix('shared:')) if asset.startswith('shared:') else (mod/'shared/images'/asset)
 xml=base.with_suffix('.xml'); png=base.with_suffix('.png'); frames=[]; err=None
 if xml.is_file():
  try: frames=[x.attrib.get('name','') for x in ET.parse(xml).getroot().findall('.//SubTexture')]
  except Exception as e: err=str(e)
 return {'png':png.is_file(),'xml':xml.is_file(),'frames':frames,'xml_error':err,'base':str(base.relative_to(mod))},frames
def one(root,s):
 mod=root/f'mods/esperon-dano-{s}'; issues=[]; songdir=next((mod/'data/songs').iterdir()); meta=j(songdir/f'{s}-metadata.json'); chart=j(songdir/f'{s}-chart.json');
 if meta.get('playData',{}).get('stage')!=f'escenario-{s}': issues.append('metadata_stage_mismatch')
 if meta.get('playData',{}).get('difficulties')!=list(chart.get('notes',{}).keys()): issues.append('difficulty_order_mismatch')
 if chart.get('version')!='2.0.0': issues.append('chart_version')
 stage_id=meta['playData']['stage']; sp=mod/f'data/stages/{stage_id}.json'; stage=j(sp) if sp.is_file() else None
 if not stage: issues.append('missing_stage_json')
 else:
  if stage.get('directory')!='shared': issues.append('stage_directory')
  if set(stage.get('characters',{})) != {'bf','dad','gf'}: issues.append('stage_character_map')
  if not stage.get('props'): issues.append('stage_props')
  for prop in stage.get('props',[]):
   a=prop.get('assetPath',''); info,_=atlas(mod,a)
   if a.startswith('shared:'): issues.append('stage_shared_prefix')
   if not info or not info['png']: issues.append('stage_asset_missing')
 chars=[]
 for role in ('player','opponent'):
  cid=meta['playData']['characters'].get(role); cp=mod/f'data/characters/{cid}.json'; cd=j(cp) if cp.is_file() else None
  if not cd: issues.append(f'missing_{role}_character'); continue
  a=cd.get('assetPath',''); info,frames=atlas(mod,a); 
  if a.startswith('shared:'): issues.append(f'{role}_shared_prefix')
  if not info or not info['png'] or not info['xml']: issues.append(f'{role}_atlas_missing')
  for an in cd.get('animations',[]):
   prefix=an.get('prefix','');
   if prefix and not any(f==prefix or f.startswith(prefix+'0') for f in frames): issues.append(f'{role}_prefix_{prefix}')
  chars.append(cid)
 style_id=meta['playData'].get('noteStyle'); stylep=mod/f'data/notestyles/{style_id}.json'; style=j(stylep) if stylep.is_file() else None
 if not style: issues.append('missing_note_style')
 else:
  for group,data in style.get('assets',{}).items():
   if not isinstance(data,dict) or not data.get('assetPath'): continue
   a=data['assetPath']; info,frames=atlas(mod,a)
   if a.startswith('shared:') and (not info or not info['png']): issues.append(f'note_asset_{group}_missing')
   if group in ('note','noteStrumline') and (not info or not info['xml']): issues.append(f'note_asset_{group}_xml_missing')
   for spec in data.get('data',{}).values():
    pref=spec.get('prefix') if isinstance(spec,dict) else None
    if pref and not any(f==pref or f.startswith(pref+'0') for f in frames): issues.append(f'note_prefix_{group}_{pref}')
 album_id=meta['playData'].get('album'); ap=mod/f'data/ui/freeplay/albums/{album_id}.json'; album=j(ap) if ap.is_file() else None
 if not album: issues.append('missing_album_json')
 else:
  for key in ('albumArtAsset','albumTitleAsset'):
   a=album.get(key); base=mod/'images'/a if isinstance(a,str) else None
   if not base or not base.with_suffix('.png').is_file(): issues.append(f'{key}_png_missing')
   if key=='albumTitleAsset' and (not base or not base.with_suffix('.xml').is_file()): issues.append('album_title_xml_missing')
   if key=='albumTitleAsset' and base and base.with_suffix('.xml').is_file():
    frames=[x.attrib.get('name','') for x in ET.parse(base.with_suffix('.xml')).getroot().findall('.//SubTexture')]
    if not any(f.startswith('idle0') for f in frames) or not any(f.startswith('switch0') for f in frames): issues.append('album_title_prefixes')
 notes_summary={}
 for diff,notes in chart.get('notes',{}).items():
  keys=[(round(float(n.get('t',-1)),3),int(n.get('d',-1))) for n in notes]; bad=[]
  if keys!=sorted(keys): bad.append('not_sorted')
  if len(keys)!=len(set(keys)): bad.append('duplicates')
  if any(t<0 or d<4 or d>7 for t,d in keys): bad.append('note_domain')
  if bad: issues.extend([f'{diff}_{x}' for x in bad])
  notes_summary[diff]={'count':len(notes),'first':keys[0][0] if keys else None,'last':keys[-1][0] if keys else None}
 audio=mod/f'songs/{s}'; inst=(audio/'Inst.ogg').is_file(); voices=sorted(audio.glob('Voices-*.ogg'))
 if not inst: issues.append('missing_inst')
 if meta['playData']['characters'].get('playerVocals') and not voices: issues.append('missing_player_voice')
 return {'song':s,'status':'PASS' if not issues else 'ERROR','issues':issues,'stage':stage_id,'characters':chars,'noteStyle':style_id,'album':album_id,'notes':notes_summary,'audio':{'inst':inst,'voices':[v.name for v in voices]}}
def main():
 root=Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve();
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: rows=sorted(list(ex.map(lambda s:one(root,s),SONGS)),key=lambda x:x['song'])
 payload={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'ERRORS_FOUND','songs':len(rows),'workers':8,'rows':rows,'runtime_limit':'Static contract/resolution check; native mobile runtime still needs playtest.'}; out=root/'qa-lab/rebuild-v222/runtime-contract-v222.json'; out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':payload['status'],'songs':len(rows),'pass':sum(r['status']=='PASS' for r in rows),'errors':sum(r['status']!='PASS' for r in rows),'output':str(out)},ensure_ascii=False)); return 0 if payload['status']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
