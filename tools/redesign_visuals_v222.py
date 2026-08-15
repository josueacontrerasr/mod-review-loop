#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, shutil, xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
DIRS=('left','down','up','right'); ROT={'up':0,'right':1,'down':2,'left':3}; PREFIX={'left':'Left','down':'Down','up':'Up','right':'Right'}

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def rgb(s): s=s.lstrip('#'); return tuple(int(s[i:i+2],16) for i in (0,2,4))
def font(size):
 for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
  if Path(p).is_file(): return ImageFont.truetype(p,size)
 return ImageFont.load_default()
def rot(pt,n,c):
 x,y=pt; cx,cy=c
 for _ in range(n%4): x,y=cx-(y-cy),cy+(x-cx)
 return x,y
def arrow_poly(size,direction,inset=14):
 base=[(size/2,inset),(size-inset,size*.56),(size*.68,size*.56),(size*.68,size-inset),(size*.32,size-inset),(size*.32,size*.56),(inset,size*.56)]
 return [rot(p,ROT[direction],(size/2,size/2)) for p in base]
def draw_arrow(size,direction,primary,secondary,dark,state,idx):
 im=Image.new('RGBA',(size,size),(0,0,0,0)); d=ImageDraw.Draw(im); c=(size/2,size/2)
 if state=='confirm': d.ellipse((6,6,size-6,size-6),fill=(*secondary,72),outline=(*primary,220),width=4)
 elif state=='press': d.ellipse((12,12,size-12,size-12),fill=(*primary,55),outline=(*secondary,190),width=4)
 poly=arrow_poly(size,direction,13 if state!='static' else 16)
 fill=primary if state!='static' else tuple(round((primary[i]*.75)+(dark[i]*.25)) for i in range(3))
 d.polygon(poly,fill=(*fill,255),outline=(*dark,255)); d.line(poly+[poly[0]],fill=(*dark,255),width=5,joint='curve')
 # One restrained per-song motif keeps silhouettes readable on mobile.
 v=idx%5
 if v==0: d.ellipse((size*.35,size*.35,size*.65,size*.65),fill=(*secondary,235))
 elif v==1: d.line((size*.28,size*.70,size*.50,size*.30,size*.72,size*.70),fill=(*secondary,235),width=5,joint='curve')
 elif v==2: d.rectangle((size*.37,size*.37,size*.63,size*.63),fill=(*secondary,235))
 elif v==3: d.polygon([(size*.50,size*.28),(size*.68,size*.50),(size*.50,size*.72),(size*.32,size*.50)],fill=(*secondary,235))
 else: d.ellipse((size*.30,size*.30,size*.70,size*.70),outline=(*secondary,235),width=5)
 if state=='confirm': d.line(poly+[poly[0]],fill=(*secondary,255),width=2,joint='curve')
 return im
def atlas(path,frames,w,h,cols):
 path.parent.mkdir(parents=True,exist_ok=True); rows=math.ceil(len(frames)/cols); sheet=Image.new('RGBA',(cols*w,rows*h),(0,0,0,0)); root=ET.Element('TextureAtlas',{'imagePath':path.name})
 for i,(name,im) in enumerate(frames):
  x=(i%cols)*w; y=(i//cols)*h; sheet.alpha_composite(im,(x,y)); ET.SubElement(root,'SubTexture',{'name':name,'x':str(x),'y':str(y),'width':str(w),'height':str(h),'frameX':'0','frameY':'0','frameWidth':str(w),'frameHeight':str(h)})
 sheet.save(path,optimize=True); ET.indent(root,space='  '); ET.ElementTree(root).write(path.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
def title_case(slug): return ' '.join(w.capitalize() for w in slug.split('-'))
def palette(brief,slug):
 p=brief.get('palette',{}); vals=[]
 for k in ('primary','secondary','dark'):
  v=p.get(k)
  vals.append(rgb(v) if isinstance(v,str) and len(v)>=7 else (50,80,120))
 return vals
def build_cover(mod,slug,pal,art,title):
 primary,secondary,dark=pal; stage=next(iter(sorted((mod/'shared/images/stages').glob('*.png'))),None); base=Image.new('RGBA',(512,512),(*dark,255))
 if stage:
  bg=ImageOps.fit(Image.open(stage).convert('RGBA'),(512,512),method=Image.Resampling.LANCZOS); base.alpha_composite(bg)
 overlay=Image.new('RGBA',(512,512),(*dark,150)); base.alpha_composite(overlay); d=ImageDraw.Draw(base)
 d.ellipse((45,48,305,308),fill=(*primary,190),outline=(*secondary,230),width=8)
 d.polygon([(300,48),(470,300),(245,300)],fill=(*secondary,210),outline=(255,255,255,210))
 d.rounded_rectangle((18,18,494,494),radius=28,outline=(255,255,255,190),width=6)
 d.line((0,420,512,270),fill=(*primary,180),width=18)
 art.parent.mkdir(parents=True,exist_ok=True); base.save(art,optimize=True)
 canvas=Image.new('RGBA',(512,128),(*dark,255)); td=ImageDraw.Draw(canvas); td.rectangle((0,0,512,128),fill=(*primary,245)); td.polygon([(0,0),(210,0),(115,128),(0,128)],fill=(*secondary,225)); label=title_case(slug); size=38 if len(label)<=18 else 28 if len(label)<=28 else 20; f=font(size); box=td.textbbox((0,0),label,font=f,stroke_width=2); tw=box[2]-box[0]; td.text(((512-tw)/2,47),label,font=f,fill=(255,255,255,255),stroke_width=2,stroke_fill=(*dark,255)); td.rectangle((7,7,505,121),outline=(255,255,255,180),width=4); title.parent.mkdir(parents=True,exist_ok=True); canvas.save(title,optimize=True)
 # AlbumRoll expects a Sparrow atlas with idle0/switch0 prefixes.
 atlas_root=ET.Element('TextureAtlas',{'imagePath':title.name})
 for n in ('switch0000','idle0000'): ET.SubElement(atlas_root,'SubTexture',{'name':n,'x':'0','y':'0','width':'512','height':'128','frameX':'0','frameY':'0','frameWidth':'512','frameHeight':'128'})
 ET.indent(atlas_root,space='  '); ET.ElementTree(atlas_root).write(title.with_suffix('.xml'),encoding='utf-8',xml_declaration=True)
def update_style(mod,slug,primary,secondary,dark):
 style_id=f'esperon-{slug}-notes'; nd=mod/'shared/images/notes'; uid=mod/'shared/images/ui'/style_id
 frames=[(f'note{PREFIX[x]}',draw_arrow(128,x,primary,secondary,dark,'press',SONGS.index(slug))) for x in DIRS]; atlas(nd/f'{style_id}-notes.png',frames,128,128,4)
 strum=[]
 for state in ('static','press','confirm'):
  for x in DIRS: strum.append((f'{state}{PREFIX[x]}0',draw_arrow(128,x,primary,secondary,dark,state,SONGS.index(slug))))
 atlas(nd/f'{style_id}-strumline.png',strum,128,128,4)
 uid.mkdir(parents=True,exist_ok=True)
 # Keep fallback-provided judgement/combo assets but ensure visual scale is not oversized.
 p=mod/'data/notestyles'/f'{style_id}.json'; d=json.loads(p.read_text()) if p.is_file() else {'version':'1.0.0','name':style_id,'author':'Manus AI','fallback':'funkin','assets':{}}
 d['version']='1.0.0'; d['fallback']='funkin'; d.setdefault('assets',{}); d['assets']['note']={'assetPath':f'shared:notes/{style_id}-notes','scale':0.82,'data':{x:{'prefix':f'note{PREFIX[x]}'} for x in DIRS}}; d['assets']['noteStrumline']={'assetPath':f'shared:notes/{style_id}-strumline','scale':0.92,'offsets':[0,0],'data':{}}
 for x in DIRS:
  pr=PREFIX[x]; d['assets']['noteStrumline']['data'].update({f'{x}Static':{'prefix':f'static{pr}0'},f'{x}Press':{'prefix':f'press{pr}0'},f'{x}Confirm':{'prefix':f'confirm{pr}0'},f'{x}ConfirmHold':{'prefix':f'confirm{pr}0'}})
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 return {'style_id':style_id,'note_png':str((nd/f'{style_id}-notes.png').relative_to(mod)),'strum_png':str((nd/f'{style_id}-strumline.png').relative_to(mod))}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root',nargs='?',default='.'); ap.add_argument('--songs',nargs='+',default=SONGS); args=ap.parse_args(); root=Path(args.root).resolve(); rows=[]
 for slug in args.songs:
  mod=root/f'mods/esperon-dano-{slug}'; songdir=next((mod/'data/songs').iterdir()); meta_path=songdir/f'{slug}-metadata.json'; chart_path=songdir/f'{slug}-chart.json'; inst=mod/f'songs/{slug}/Inst.ogg'; vocals=sorted((mod/f'songs/{slug}').glob('Voices-*.ogg')); before={'chart':sha(chart_path),'inst':sha(inst),'vocals':[sha(v) for v in vocals]}; briefs=sorted((root/'visual-briefs').glob(f'{slug}.json')); brief=json.loads(briefs[0].read_text()) if briefs else {}; pal=palette(brief,slug); style=update_style(mod,slug,*pal); album_id=f'esperon-{slug}'; art=mod/'images/freeplay/albums'/f'{album_id}-art.png'; title=mod/'images/freeplay/albums'/f'{album_id}-title.png'; build_cover(mod,slug,pal,art,title)
  album=mod/'data/ui/freeplay/albums'/f'{album_id}.json'; ad=json.loads(album.read_text()) if album.is_file() else {'version':'1.0.3','name':title_case(slug),'artists':['Esperón']}; ad.update({'version':'1.0.3','name':title_case(slug),'artists':['Esperón'],'albumArtAsset':f'freeplay/albums/{album_id}-art','albumTitleAsset':f'freeplay/albums/{album_id}-title','albumTitleOffsets':[0,0],'albumTitleAnimations':[],'albumOSTName':'ESPERÓN'}); album.parent.mkdir(parents=True,exist_ok=True); album.write_text(json.dumps(ad,ensure_ascii=False,indent=2)+'\n')
  mp=json.loads(meta_path.read_text()); mp.setdefault('playData',{})['album']=album_id; mp['generatedBy']='Friday Night Funkin\' - 0.8.6; V2.2.2 visual redesign; audio/chart preserved'; meta_path.write_text(json.dumps(mp,ensure_ascii=False,indent=2)+'\n')
  man=mod/'_polymod_meta.json'; md=json.loads(man.read_text()); md['mod_version']='2.2.2'; md['description']=f'Mod V-Slice 0.8.6 de {title_case(slug)}; stages y personajes reparados, visuales V2.2.2 y charts/voces preservados.'; man.write_text(json.dumps(md,ensure_ascii=False,indent=2)+'\n')
  after={'chart':sha(chart_path),'inst':sha(inst),'vocals':[sha(v) for v in vocals]}; rows.append({'song':slug,'palette':{'primary':'#%02X%02X%02X'%pal[0],'secondary':'#%02X%02X%02X'%pal[1],'dark':'#%02X%02X%02X'%pal[2]},'style':style,'album':str(album.relative_to(mod)),'art':str(art.relative_to(mod)),'title':str(title.relative_to(mod)),'protected_before':before,'protected_after':after,'audio_chart_unchanged':before==after})
 out=root/'qa-lab/rebuild-v222/visual-redesign-v222.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'status':'PASS' if all(r['audio_chart_unchanged'] for r in rows) else 'ERROR','songs':len(rows),'rows':rows,'note_frame_size':128,'note_scale':0.82,'strumline_scale':0.92},ensure_ascii=False,indent=2)+'\n'); print(json.dumps({'status':'PASS' if all(r['audio_chart_unchanged'] for r in rows) else 'ERROR','songs':len(rows),'output':str(out)},ensure_ascii=False))
if __name__=='__main__': main()
