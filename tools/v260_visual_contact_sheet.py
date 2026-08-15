#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'qa-lab/rebuild-v260'; SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]
W,H=280,190; cols=4; rows=[]; sheet=Image.new('RGB',(cols*W,5*H),(28,28,32)); draw=ImageDraw.Draw(sheet)
for i,song in enumerate(SONGS):
 mod=ROOT/'mods'/f'esperon-dano-{song}'; sd=next((mod/'data/songs').iterdir()); meta=json.loads((sd/f'{song}-metadata.json').read_text()); album=json.loads((mod/'data/ui/freeplay/albums'/f"{meta['playData']['album']}.json").read_text()); asset=mod/'images'/f"{album['albumArtAsset']}.png"; stage=mod/'shared/images/stages'/f'escenario-{song}.png'; char=mod/'shared/images/characters'/f'esperon-{song}.png';
 row=i//cols; col=i%cols
 for p,label,x in ((asset,'album',0),(stage,'stage',90),(char,'char',180)):
  try:
   with Image.open(p) as im:
    rgba=im.convert('RGBA'); alpha=rgba.getchannel('A'); alpha_nonzero=sum(1 for px in alpha.getdata() if px>0); rec={'song':song,'kind':label,'path':str(p.relative_to(ROOT)),'size':im.size,'mode':im.mode,'alpha_nonzero_ratio':round(alpha_nonzero/(im.width*im.height),6)}; rows.append(rec)
    thumb=rgba.copy(); thumb.thumbnail((86,135)); tile=Image.new('RGBA',(86,145),(45,45,50,255)); tile.alpha_composite(thumb,((86-thumb.width)//2,4)); sheet.paste(tile.convert('RGB'),(col*W+x,row*H+22)); draw.text((col*W+x,row*H+4),label,fill='white')
  except Exception as exc: rows.append({'song':song,'kind':label,'path':str(p),'error':str(exc)})
 draw.text((col*W,row*H+168),song[:35],fill='white')
metrics={'version':'2.6.0-visual-assets','status':'PASS' if not any('error' in r for r in rows) else 'ERRORS_FOUND','assets':rows,'errors':[r for r in rows if 'error' in r]}
(OUT/'visual-assets-v260.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n'); sheet.save(OUT/'visual-contact-sheet-v260.png'); print(json.dumps({'status':metrics['status'],'assets':len(rows),'output':str(OUT/'visual-contact-sheet-v260.png')},ensure_ascii=False))
