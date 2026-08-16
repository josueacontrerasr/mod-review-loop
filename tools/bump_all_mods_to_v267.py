#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.6.7"
GENERATED_BY = "Friday Night Funkin' - 0.8.6; V2.6.7 vocal RMS-VAD retimed holds and repetition-balanced player lanes d=0..3"
mods = sorted((ROOT / "mods").glob("esperon-dano-*"))

for mod in mods:
    manifest_path = mod / "_polymod_meta.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["mod_version"] = VERSION
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

config_path = ROOT / "config" / "fnf_target.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
config["fnf_version"] = "0.8.6"
config["api_version"] = "0.8.6"
config["mod_version"] = VERSION
config["songs_count"] = 21
config["mods_per_qa_round"] = 21
config["qa_rounds"] = 20
config["qa_reviews_expected"] = 420
config["chart_generation_mode"] = "VOCAL_SYLLABLE_ALIGNED_VOWEL_MAPPED_PLAYER_LANES_0_3"
audio_policy = config.setdefault("audio_policy", {})
audio_policy["chart_generation_mode"] = "VOCAL_SYLLABLE_ALIGNED_VOWEL_MAPPED_PLAYER_LANES_0_3"
audio_policy["instrumental_can_generate_notes"] = False
config["chart_syllable_policy"] = {
    "one_note_per_syllable": True,
    "interjections_are_separate_notes": True,
    "holds_from_measured_vocal_duration": True,
    "low_confidence_requires_manual_review": True,
}
config["complete_delivery_zip"] = "Esperon-Completo.zip"
config["freeplay_capsule_policy"] = "LEVEL_TITLE_ASSET_AND_ALBUM_ROLL_VERIFIED"
config["player_lane_contract"] = "d=0..3 with vowel mapping A=0,E=2,I=3,O/U=1"
contracts = config.setdefault("contracts", {})
contracts["player_lanes"] = [0, 1, 2, 3]
contracts["opponent_lanes"] = [4, 5, 6, 7]
release_policy = config.setdefault("release_policy", {})
release_policy["current_mod_version"] = VERSION
release_policy["change_summary"] = "Lanes d=0..3; sincronización RMS-VAD, holds retimed y balanceo de rachas vocálicas; Freeplay AlbumRoll verificado; 21 mods"
qa_policy = config.setdefault("qa_policy", {})
qa_policy["playstate_required_chart_generatedBy"] = GENERATED_BY
qa_policy["vocal_hold_threshold_ms"] = 180
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print({"mods": len(mods), "mod_version": VERSION, "songs_count": config["songs_count"], "player_lanes": contracts["player_lanes"]})
