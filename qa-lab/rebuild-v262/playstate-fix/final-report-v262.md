# Informe técnico V2.6.2 — Si Te Vas y reauditoría vocal de Esperón

## Alcance

Se añadió el mod `esperon-dano-si-te-vas` para **Si Te Vas** de Esperón, objetivo FNF Mobile V-Slice oficial `0.8.6`. El nuevo mod se construyó desde un template que ya había superado los contratos V-Slice y el gate PlayState V2.6.1. La entrega se versionó como `2.6.2` porque incorpora un mod nuevo y amplía la colección de 20 a 21 canciones.

## Audio y carátula

El audio fuente utilizado fue `Esperón  Si Te Vas.m4a`, con duración de `225.372880` segundos y metadata `title=Si Te Vas`, `album=Nubia`, `artist=Esperón`. El M4A contiene una imagen PNG embebida de `1000×1000`; esa imagen fue usada como fuente exacta de la carátula de Freeplay y convertida a `512×512 PNG` en `freeplay/albumRoll/esperon-si-te-vas-art.png`.

Demucs `htdemucs` se ejecutó en CPU con `--two-stems=vocals`. El chart se generó únicamente desde `Voices-esperon-si-te-vas.ogg`; `Inst.ogg` no participó en la selección de timestamps. El manifiesto de hashes se encuentra en `si-te-vas-source-manifest-v262.json`.

## Charts y sincronización

Se reanalizaron las 21 fuentes `Voices-*.ogg` con el pipeline vocal-only V2.6.2: RMS/VAD batch, segmentos vocales fusionados, detección de onsets, backtracking al pico RMS local y densidad progresiva `easy < normal < hard`. La comparación candidato-producción obtuvo `21/21` iguales después de promover Si Te Vas.

| Gate | Resultado local |
|---|---:|
| Candidatos vocal-only aislados | 21/21 PASS |
| Diferencia candidato-producción | 0 canciones diferentes después de promoción |
| Notas fuera de segmentos vocales | 0 |
| Metadata de staging filtrada | 0 |
| Lanes inválidos | 0 |
| PlayState | 63/63 PASS |
| Contratos/assets Freeplay | 21/21 PASS |
| Loader headless móvil | 21/21 PASS |
| QA profundo | 420/420 PASS |
| ZIPs individuales | 21/21 PASS |
| `Esperon-Completo.zip` | PASS; 21 mods dentro |

## Entrega

La carpeta `Mods .zip terminados/` contiene 22 ZIPs: `Esperon-Completo.zip` y 21 ZIPs individuales `Mod-<Canción>-V2.6.2.zip`. El empaquetador excluye `.txt`, `.md`, `.log`, `.csv`, `.html` y `.bak` del runtime ZIP, por lo que no se incluyen reportes ni staging dentro de los mods.

## Limitación de certificación

Los gates estáticos y el loader headless confirman estructura, resolución de IDs, contratos, assets, audio OGG, dificultad y límites chart↔vocal. No sustituyen el `Audio Sync Test` dentro del Chart Editor oficial ni un playtest táctil en un teléfono Android/iOS real. La Release debe declarar esta última capa como pendiente mientras no exista una ejecución física documentada.

## Evidencias

Las evidencias JSON V2.6.2 están en `qa-lab/rebuild-v262/playstate-fix/`: resolver PlayState, gate vocal, contratos/assets, paquete, ZIP gate, loader móvil, QA 20×21, comparación candidato-producción y manifiesto de fuente de Si Te Vas.
