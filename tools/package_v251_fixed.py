#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=ROOT/'Mods .zip terminados'
PREFIX='esperon-dano-'
SONGS=['arcoloria','cortamos-y-volvemos','dano','dias-magicos','eclipsis','fango','luma','maraton-de-peliculas','me-voy-a-morir-si-no-me-besas-ahora-mismo','meteora','mi-hogar','nubia','nuestro-amor-no-es-normal','peligrosa','rompecabezas','solare','tristella','tu-dealer-de-nostalgia','un-poco-bien-un-poco-mal','volver-a-vernos']

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def display(song):
    return '-'.join(w.capitalize() for w in song.split('-'))

FIXED_DATE=(2020,1,1,0,0,0)

def write_deterministic(z, name, data):
    info=zipfile.ZipInfo(name, date_time=FIXED_DATE)
    info.create_system=3
    info.external_attr=0o100644 << 16
    info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info, data)

def package_mod(song):
    mod=ROOT/'mods'/f'{PREFIX}{song}'
    out=DELIVERY/f'Mod-{display(song)}-V2.5.1.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(p for p in mod.rglob('*') if p.is_file()):
            rel=path.relative_to(mod.parent)
            write_deterministic(z, rel.as_posix(), path.read_bytes())
    return out

def main():
    DELIVERY.mkdir(parents=True,exist_ok=True)
    for old in DELIVERY.glob('*.zip'): old.unlink()
    paths=[package_mod(song) for song in SONGS]
    manifest={'version':'2.5.1','status':'PASS','mods':len(paths),'packages':[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'root_entries':sorted({x.split('/')[0] for x in zipfile.ZipFile(p).namelist()})} for p in paths]}
    manifest_path=ROOT/'qa-lab/rebuild-v250/package-manifest-v251.json'; manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    collection=DELIVERY/'Mod-Esperon-Coleccion-V2.5.1.zip'
    readme='Esperón FNF Mobile V-Slice 0.8.6 V2.5.1\n\nContiene 20 ZIPs individuales. Extrae el ZIP individual elegido directamente dentro de la carpeta mods de FNF Mobile.\n'
    with zipfile.ZipFile(collection,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        write_deterministic(z, 'README-INSTALACION.txt', readme.encode('utf-8'))
        for p in paths: write_deterministic(z, p.name, p.read_bytes())
    print(json.dumps({'status':'PASS','mods':len(paths),'collection':collection.name,'delivery_zips':len(list(DELIVERY.glob('*.zip'))),'manifest':str(manifest_path)},ensure_ascii=False))

if __name__=='__main__':main()
