#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SONGS=["arcoloria","cortamos-y-volvemos","dano","dias-magicos","eclipsis","fango","luma","maraton-de-peliculas","me-voy-a-morir-si-no-me-besas-ahora-mismo","meteora","mi-hogar","nubia","nuestro-amor-no-es-normal","peligrosa","rompecabezas","solare","tristella","tu-dealer-de-nostalgia","un-poco-bien-un-poco-mal","volver-a-vernos"]

def main():
    for song in SONGS:
        p=ROOT/'mods'/f'esperon-dano-{song}'/'_polymod_meta.json'
        d=json.loads(p.read_text(encoding='utf-8'))
        d['mod_version']='2.5.0'
        d['description']='Esperón FNF Mobile V-Slice 0.8.6 — V2.5.0 voice-first charts; official player lanes 0-3'
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('manifests_bumped=20')

if __name__=='__main__': main()
