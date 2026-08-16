from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.7.2"
GENERATED_BY = "Friday Night Funkin' - 0.8.6; V2.7.2 syllable-accurate vocal chart player lanes d=0..3"
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
config["chart_generation_mode"] = "V272_SYLLABLE_ACCURATE_VOCAL_ONLY_PLAYER_LANES_0_3"
audio_policy = config.setdefault("audio_policy", {})
audio_policy["chart_generation_mode"] = "V272_SYLLABLE_ACCURATE_VOCAL_ONLY_PLAYER_LANES_0_3"
audio_policy["instrumental_can_generate_notes"] = False
config["chart_syllable_policy"] = {
    "one_note_per_syllable": True,
    "close_syllables_remain_separate": True,
    "interjections_are_separate_notes": True,
    "holds_from_measured_sustained_vocal_duration": True,
    "holds_not_synthesized_by_density_reduction": True,
    "engine_same_lane_collision_ms": 12,
    "low_confidence_requires_manual_review": True,
}
config["complete_delivery_zip"] = "Esperon-Completo.zip"
config["freeplay_capsule_policy"] = "LEVEL_TITLE_ASSET_AND_ALBUM_ROLL_VERIFIED"
config["player_lane_contract"] = "d=0..3 with vowel mapping A=0,E=2,I=3,O/U=1; repeated same-vowel attacks balance lanes"
contracts = config.setdefault("contracts", {})
contracts["player_lanes"] = [0, 1, 2, 3]
contracts["opponent_lanes"] = [4, 5, 6, 7]
release_policy = config.setdefault("release_policy", {})
release_policy["current_mod_version"] = VERSION
release_policy["change_summary"] = "V2.7.2 syllable-accurate vocal charts; close attacks preserved as separate player notes; measured holds only; 21 mods"
qa_policy = config.setdefault("qa_policy", {})
qa_policy["playstate_required_chart_generatedBy"] = GENERATED_BY
qa_policy["vocal_hold_threshold_ms"] = 180
qa_policy["vocal_density_500ms"] = "observed_only_no_collapse"
qa_policy["vocal_density_1000ms"] = "observed_only_no_deletion"
config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print({"mods": len(mods), "mod_version": VERSION, "songs_count": config["songs_count"], "player_lanes": contracts["player_lanes"]})
