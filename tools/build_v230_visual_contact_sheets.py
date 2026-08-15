from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path('/home/ubuntu/mod-review-loop-production')
SONGS=['arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma','maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar','nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella','tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos']
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',16)

def sheet(kind, path, size):
    cols=4; rows=(len(SONGS)+cols-1)//cols; cellw,cellh=size[0]+24,size[1]+44
    canvas=Image.new('RGB',(cols*cellw,rows*cellh),(18,20,38)); draw=ImageDraw.Draw(canvas)
    for i,song in enumerate(SONGS):
        mod=ROOT/f'mods/esperon-dano-{song}'
        if kind=='covers': src=mod/'images/freeplay/albums'/f'esperon-{song}-art.png'
        elif kind=='stages': src=mod/'shared/images/stages'/f'escenario-{song}.png'
        else: src=mod/'shared/images/characters'/f'esperon-{song}.png'
        with Image.open(src).convert('RGBA') as im:
            if kind=='characters': im.thumbnail(size,Image.Resampling.LANCZOS); box=Image.new('RGBA',size,(0,0,0,0)); box.alpha_composite(im,((size[0]-im.width)//2,(size[1]-im.height)//2)); im=box
            else: im=ImageOps.fit(im,size,method=Image.Resampling.LANCZOS)
            x=(i%cols)*cellw+12; y=(i//cols)*cellh+8
            canvas.paste(im.convert('RGB'),(x,y)); draw.text((x,y+size[1]+6),song,fill=(240,240,248),font=font)
    canvas.save(path,optimize=True)

from PIL import ImageOps
out=ROOT/'qa-lab/rebuild-v230'
sheet('covers',out/'contact-covers-v230.png',(240,240))
sheet('stages',out/'contact-stages-v230.png',(240,135))
sheet('characters',out/'contact-characters-v230.png',(240,120))
print(out)
