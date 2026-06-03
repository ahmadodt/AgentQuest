import json
import os

from src.engine.loader import load_gamedata
from src.prompts.base_prompt import build_messages, build_note_update_messages
from src.prompts.prompt_config import PromptConfig


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _base_custom_dataset() -> dict:
    return {
        "tools": {
            "version": "1.0",
            "tools": [
                {
                    "tool_id": "mage.arc_bolt",
                    "label": "Arc Bolt",
                    "description": "A short custom attack.",
                    "category": "attack",
                    "args": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                    "constraints": {
                        "allowed_classes": ["Mage"],
                        "required_inventory": [],
                        "forbidden_traits": [],
                    },
                    "effects": {"damage_type": "force", "base_power": 4},
                }
            ],
        },
        "characters": {
            "version": "1.0",
            "characters": [
                {
                    "character_id": "mage.aria",
                    "name": "Aria",
                    "class": "Mage",
                    "inventory": [],
                    "traits": [],
                    "tool_ids": ["mage.arc_bolt"],
                }
            ],
        },
        "monsters": {
            "version": "1.0",
            "monsters": [
                {
                    "monster_id": "custom.slime",
                    "name": "Custom Slime",
                    "type": "ooze",
                    "description": "Sticky but simple.",
                    "tags": ["ooze"],
                    "weaknesses": ["fire"],
                    "resistances": [],
                    "immunities": [],
                    "special_rules": [],
                    "damage_profile": "custom.profile.slime",
                    "damage_modifier_overrides": {"fire": 2.0},
                    "interactions": {
                        "min_power_to_defeat": 2,
                        "knowledge_tools_help": False,
                        "escape_allowed": True,
                    },
                }
            ],
        },
        "scenes": {
            "version": "1.0",
            "scenes": [
                {
                    "scene_id": "scene.slime",
                    "title": "Slime Cellar",
                    "location": "Cellar",
                    "monster_id": "custom.slime",
                    "narrative": "A slime blocks the path.",
                    "knowledge_level": "basic",
                    "constraints": {},
                    "success_condition": {"type": "defeat_monster"},
                    "failure_condition": {"type": "stuck"},
                }
            ],
        },
        "campaigns": {
            "version": "1.0",
            "campaigns": [
                {
                    "campaign_id": "campaign.slime",
                    "name": "Slime Trial",
                    "description": "One slime scene.",
                    "type": "tutorial",
                    "scene_ids": ["scene.slime"],
                }
            ],
        },
    }


def _write_runtime_dataset(base_dir: str, dataset: dict, use_custom_subdir: bool = False) -> None:
    root = os.path.join(base_dir, "custom", "agentquest") if use_custom_subdir else base_dir
    _write_json(os.path.join(root, "tools.json"), dataset["tools"])
    _write_json(os.path.join(root, "characters.json"), dataset["characters"])
    _write_json(os.path.join(root, "monsters.json"), dataset["monsters"])
    _write_json(os.path.join(root, "scenes.json"), dataset["scenes"])
    _write_json(os.path.join(root, "campaigns.json"), dataset["campaigns"])
    _write_json(
        os.path.join(root, "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "custom.profile.slime": {},
            },
        },
    )


def test_load_gamedata_merges_custom_and_generated_with_custom_precedence(tmp_path):
    dataset = _base_custom_dataset()
    dataset["tools"]["tools"][0]["tool_id"] = "open5e.spell.spark"
    dataset["tools"]["tools"][0]["label"] = "Custom Spark"
    dataset["tools"]["tools"][0]["description"] = "Custom description wins."
    dataset["characters"]["characters"][0]["tool_ids"] = ["open5e.spell.spark"]
    dataset["monsters"]["monsters"][0]["monster_id"] = "open5e.monster.slime"
    dataset["monsters"]["monsters"][0]["name"] = "Custom Slime Boss"
    dataset["scenes"]["scenes"][0]["monster_id"] = "open5e.monster.slime"

    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "tools_spells.json"),
        {
            "version": "1.0",
            "tools": [
                {
                    "tool_id": "open5e.spell.spark",
                    "label": "Generated Spark",
                    "description": "Generated description. Extra sentence.",
                    "category": "attack",
                    "args": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                    "constraints": {
                        "allowed_classes": ["Mage"],
                        "required_inventory": [],
                        "forbidden_traits": [],
                    },
                    "effects": {"damage_type": "fire", "base_power": 2},
                    "spell_details": {"level": "Cantrip"},
                    "source": {"dataset": "open5e"},
                },
                {
                    "tool_id": "open5e.spell.frostbite",
                    "label": "Frostbite",
                    "description": "Freeze a target. Another sentence.",
                    "category": "attack",
                    "args": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                    "constraints": {
                        "allowed_classes": ["Mage"],
                        "required_inventory": [],
                        "forbidden_traits": [],
                    },
                    "effects": {"damage_type": "cold", "base_power": 3},
                },
            ],
        },
    )
    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "monsters.json"),
        {
            "version": "1.0",
            "monsters": [
                {
                    "monster_id": "open5e.monster.slime",
                    "name": "Generated Slime",
                    "type": "ooze",
                    "description": "Generated lore.",
                    "tags": ["generated"],
                    "weaknesses": [],
                    "resistances": [],
                    "immunities": [],
                    "special_rules": [],
                    "damage_profile": "open5e.profile.slime",
                    "damage_modifier_overrides": {},
                    "interactions": {
                        "min_power_to_defeat": 1,
                        "knowledge_tools_help": False,
                    },
                },
                {
                    "monster_id": "open5e.monster.bat",
                    "name": "Generated Bat",
                    "type": "beast",
                    "description": "Bat lore.",
                    "tags": ["flying"],
                    "weaknesses": [],
                    "resistances": [],
                    "immunities": [],
                    "special_rules": [],
                    "damage_profile": "open5e.profile.bat",
                    "damage_modifier_overrides": {},
                    "interactions": {
                        "min_power_to_defeat": 1,
                        "knowledge_tools_help": False,
                    },
                },
            ],
        },
    )
    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "open5e.profile.slime": {},
                "open5e.profile.bat": {},
            },
        },
    )

    gamedata = load_gamedata(str(tmp_path))

    assert set(gamedata["tools_by_id"]) == {"open5e.spell.spark", "open5e.spell.frostbite"}
    assert gamedata["tools_by_id"]["open5e.spell.spark"]["label"] == "Custom Spark"
    assert gamedata["tools_by_id"]["open5e.spell.spark"]["origin"] == "custom"
    assert gamedata["tools_by_id"]["open5e.spell.frostbite"]["origin"] == "generated"
    assert gamedata["tools_by_id"]["open5e.spell.frostbite"]["tool_family"] == "spell"

    assert set(gamedata["monsters_by_id"]) == {"open5e.monster.slime", "open5e.monster.bat"}
    assert gamedata["monsters_by_id"]["open5e.monster.slime"]["name"] == "Custom Slime Boss"
    assert gamedata["monsters_by_id"]["open5e.monster.bat"]["origin"] == "generated"
    assert set(gamedata["campaigns_by_id"]) == {"campaign.slime"}


def test_generated_monsters_are_normalized_for_runtime_and_projected_for_llm(tmp_path):
    dataset = _base_custom_dataset()
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "monsters.json"),
        {
            "version": "1.0",
            "monsters": [
                {
                    "monster_id": "open5e.monster.mud_mephit",
                    "name": "Mud Mephit",
                    "type": "elemental",
                    "description": "A muddy pest.",
                    "tags": ["small", "flying"],
                    "weaknesses": ["fire"],
                    "resistances": ["poison"],
                    "immunities": ["mud"],
                    "condition_immunities": ["poisoned"],
                    "special_rules": ["messy"],
                    "cr": 1.0,
                    "damage_profile": "open5e.profile.mud_mephit",
                    "damage_modifier_overrides": {"fire": 2.0},
                    "source": {"dataset": "open5e"},
                    "interactions": {
                        "min_power_to_defeat": 1,
                        "knowledge_tools_help": True,
                    },
                }
            ],
        },
    )
    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "open5e.profile.mud_mephit": {},
            },
        },
    )

    gamedata = load_gamedata(str(tmp_path))
    monster = gamedata["monsters_by_id"]["open5e.monster.mud_mephit"]
    llm_monster = gamedata["llm_monsters_by_id"]["open5e.monster.mud_mephit"]

    assert monster["interactions"]["escape_allowed"] is True
    assert llm_monster["interactions"] == {
        "min_power_to_defeat": 1,
        "knowledge_tools_help": True,
        "escape_allowed": True,
    }
    assert llm_monster["resolved_damage_modifiers"]["fire"] == 2.0
    assert llm_monster["description"] == "A muddy pest."
    assert "source" not in llm_monster
    assert "cr" not in llm_monster
    assert "condition_immunities" not in llm_monster


def test_load_gamedata_resolves_damage_profile_modifiers(tmp_path):
    dataset = _base_custom_dataset()
    dataset["monsters"]["monsters"][0].pop("interactions")
    dataset["monsters"]["monsters"][0]["damage_profile"] = "slime_profile"
    dataset["monsters"]["monsters"][0]["damage_modifier_overrides"] = {"force": 1.5}
    dataset["monsters"]["monsters"][0]["interactions"] = {
        "min_power_to_defeat": 2,
        "knowledge_tools_help": False,
        "escape_allowed": True,
    }
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)
    _write_json(
        os.path.join(tmp_path, "custom", "agentquest", "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "slime_profile": {
                    "fire": 2.0,
                    "force": 1.0,
                }
            },
        },
    )

    gamedata = load_gamedata(str(tmp_path))
    monster = gamedata["monsters_by_id"]["custom.slime"]

    assert gamedata["damage_profiles_by_id"]["slime_profile"]["fire"] == 2.0
    assert monster["resolved_damage_modifiers"]["fire"] == 2.0
    assert monster["resolved_damage_modifiers"]["force"] == 1.5


def test_load_gamedata_rejects_legacy_damage_modifier_field(tmp_path):
    dataset = _base_custom_dataset()
    monster = dataset["monsters"]["monsters"][0]
    monster.pop("damage_profile")
    monster.pop("damage_modifier_overrides")
    monster["interactions"]["damage_type_modifiers"] = {"fire": 2.0}
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    try:
        load_gamedata(str(tmp_path))
        assert False, "Expected load_gamedata to reject legacy damage_type_modifiers"
    except Exception as error:
        assert "monster must define damage_profile" in str(error)


def test_llm_tool_projection_shortens_generated_spell_description_and_prompt_uses_it(tmp_path):
    dataset = _base_custom_dataset()
    dataset["characters"]["characters"][0]["tool_ids"] = ["open5e.spell.spark"]
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    _write_json(
        os.path.join(tmp_path, "generated", "open5e", "tools_spells.json"),
        {
            "version": "1.0",
            "tools": [
                {
                    "tool_id": "open5e.spell.spark",
                    "label": "Spark",
                    "description": "A sharp bolt of light. It also startles nearby foes.",
                    "category": "attack",
                    "args": {
                        "type": "object",
                        "properties": {"target": {"type": "string"}},
                        "required": ["target"],
                    },
                    "constraints": {
                        "allowed_classes": ["Mage"],
                        "required_inventory": [],
                        "forbidden_traits": [],
                    },
                    "effects": {"damage_type": "radiant", "base_power": 5},
                    "spell_details": {"range": "60 feet"},
                    "source": {"dataset": "open5e"},
                }
            ],
        },
    )

    gamedata = load_gamedata(str(tmp_path))
    llm_tool = gamedata["llm_tools_by_id"]["open5e.spell.spark"]

    assert llm_tool["description"] == "A sharp bolt of light."
    assert "spell_details" not in llm_tool
    assert "source" not in llm_tool

    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]
    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=PromptConfig(tools_include_constraints=True, tools_include_effects=True),
    )

    user_message = messages[1]["content"]
    assert "A sharp bolt of light." in user_message
    assert "It also startles nearby foes." not in user_message
    assert "spell_details" not in user_message
    assert "source" not in user_message


def test_full_info_includes_scene_constraints_but_battle_plan_hides_them(tmp_path):
    dataset = _base_custom_dataset()
    dataset["monsters"]["monsters"][0]["special_rules"] = ["messy"]
    dataset["monsters"]["monsters"][0]["interactions"]["escape_allowed"] = False
    dataset["monsters"]["monsters"][0]["damage_profile"] = "slime_profile"
    dataset["monsters"]["monsters"][0]["damage_modifier_overrides"] = {"force": 1.5}
    dataset["scenes"]["scenes"][0]["constraints"] = {
        "exactly_one_tool_call": True,
        "no_escape": True,
    }
    dataset["scenes"]["scenes"][0]["validation_rules"] = {
        "mode": "survival_check",
        "allow_escape_as_success": False,
        "required_effect_tags": ["defense"],
        "forbidden_effect_tags": ["escape"],
    }
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)
    _write_json(
        os.path.join(tmp_path, "custom", "agentquest", "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "slime_profile": {
                    "fire": 2.0,
                    "force": 1.0,
                }
            },
        },
    )

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]

    from src.prompts.presets import BATTLE_PLAN, BLIND_ADVENTURER, FULL_INFO, SCOUT_REPORT

    blind_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=BLIND_ADVENTURER,
    )
    battle_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=BATTLE_PLAN,
    )
    scout_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=SCOUT_REPORT,
    )
    full_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=FULL_INFO,
    )

    assert "- description: Sticky but simple." in blind_messages[1]["content"]
    assert "- weaknesses:" not in blind_messages[1]["content"]
    assert "- validation_rules:" not in blind_messages[1]["content"]
    assert "- resolved_damage_modifiers:" not in blind_messages[1]["content"]
    assert "- constraints:" not in battle_messages[1]["content"]
    assert "- validation_rules:" not in battle_messages[1]["content"]
    assert "- resolved_damage_modifiers:" not in battle_messages[1]["content"]
    assert "- tags:" not in battle_messages[1]["content"]
    assert "- description: Sticky but simple." in battle_messages[1]["content"]
    assert "- special_rules:" not in blind_messages[1]["content"]
    assert "- special_rules:" not in battle_messages[1]["content"]
    assert "- special_rules:" not in scout_messages[1]["content"]
    assert "- special_rules:" not in full_messages[1]["content"]
    assert '- constraints: {"exactly_one_tool_call": true, "no_escape": true}' in full_messages[1]["content"]
    assert (
        '- validation_rules: {"mode": "survival_check", "allow_escape_as_success": false, '
        '"required_effect_tags": ["defense"], "forbidden_effect_tags": ["escape"]}'
    ) in full_messages[1]["content"]
    assert '- resolved_damage_modifiers: {"fire": 2.0, "force": 1.5}' in full_messages[1]["content"]
    assert '- tags: ["ooze"]' in full_messages[1]["content"]
    assert "- description: Sticky but simple." in full_messages[1]["content"]


def test_battle_plan_includes_defeat_objective_guidance_without_debug_fields(tmp_path):
    dataset = _base_custom_dataset()
    dataset["monsters"]["monsters"][0]["interactions"]["escape_allowed"] = True
    dataset["monsters"]["monsters"][0]["damage_profile"] = "slime_profile"
    dataset["monsters"]["monsters"][0]["damage_modifier_overrides"] = {"fire": 2.0}
    dataset["scenes"]["scenes"][0]["validation_rules"] = {
        "mode": "standard",
        "allow_escape_as_success": False,
        "required_effect_tags": [],
        "forbidden_effect_tags": [],
    }
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)
    _write_json(
        os.path.join(tmp_path, "custom", "agentquest", "damage_profiles.json"),
        {
            "version": "1.0",
            "profiles": {
                "slime_profile": {
                    "fire": 2.0,
                    "force": 1.0,
                }
            },
        },
    )

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]

    from src.prompts.presets import BATTLE_PLAN

    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=BATTLE_PLAN,
    )

    user_message = messages[1]["content"]
    assert "OBJECTIVE GUIDANCE:" in user_message
    assert "For defeat_monster, choose a tool with combat_effect: true." in user_message
    assert "Prefer a damage_type that matches visible weaknesses" in user_message
    assert "The success_condition outranks narrative flavor" in user_message
    assert "DECISION POLICY:" in user_message
    assert "First satisfy the scene objective." in user_message
    assert "- validation_rules:" not in user_message
    assert "- resolved_damage_modifiers:" not in user_message
    assert "- tags:" not in user_message


def test_solve_encounter_objective_guidance_uses_preferred_effects(tmp_path):
    dataset = _base_custom_dataset()
    dataset["scenes"]["scenes"][0]["success_condition"] = {
        "type": "solve_encounter",
        "preferred_effects": ["mitigation"],
    }
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]
    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=PromptConfig(tools_include_effects=True),
    )

    user_message = messages[1]["content"]
    assert 'For solve_encounter, prefer tools matching preferred_effects: ["mitigation"].' in user_message
    assert "Do not default to attacking unless combat is the objective or the preferred effect." in user_message


def test_build_messages_includes_learning_notes_when_provided(tmp_path):
    dataset = _base_custom_dataset()
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]
    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=PromptConfig(),
        learning_notes="- Fire works better on sticky enemies.",
    )

    assert "CAMPAIGN NOTES:" in messages[1]["content"]
    assert "Treat them as optional hypotheses, not facts." in messages[1]["content"]
    assert "Fire works better on sticky enemies." in messages[1]["content"]


def test_build_note_update_messages_uses_prompt_visible_context_and_grounding_rules(tmp_path):
    dataset = _base_custom_dataset()
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]
    messages = build_note_update_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        scene_run={
            "scene_id": "scene.slime",
            "raw_model_output": '{"tool_id":"mage.arc_bolt","arguments":{"target":"slime"}}',
            "parsed_tool_call": {
                "tool_id": "mage.arc_bolt",
                "arguments": {"target": "slime"},
            },
            "status": "FAIL",
            "reason": "The slime resisted the chosen approach.",
        },
        existing_notes="- Old note",
        gamedata=gamedata,
        cfg=PromptConfig(tools_include_constraints=True, tools_include_effects=True),
    )

    assert "Do not invent or change tool mechanics, damage, power, cooldowns, requirements, hidden stats, or monster rules." in messages[0]["content"]
    assert "Do not introduce numeric thresholds unless they appear explicitly in the provided prompt-visible information." in messages[0]["content"]
    assert "Because these notes carry into later scenes, prefer transferable lessons over enemy-specific instructions whenever possible." in messages[0]["content"]
    assert "Treat the validator reason as evidence, then rewrite it into natural guidance rather than copying it literally." in messages[0]["content"]
    assert "VISIBLE TOOLS (schemas):" in messages[1]["content"]
    assert "A short custom attack." in messages[1]["content"]
    assert '"base_power": 4' in messages[1]["content"]
    assert "FAILED ATTEMPT:" in messages[1]["content"]
    assert "OLD NOTES:\n- Old note" in messages[1]["content"]


def test_load_gamedata_keeps_custom_only_flow_when_generated_content_is_absent(tmp_path):
    dataset = _base_custom_dataset()
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    gamedata = load_gamedata(str(tmp_path))

    assert set(gamedata["tools_by_id"]) == {"mage.arc_bolt"}
    assert set(gamedata["monsters_by_id"]) == {"custom.slime"}
    assert gamedata["llm_tools_by_id"]["mage.arc_bolt"]["description"] == "A short custom attack."


def test_load_gamedata_rejects_missing_custom_runtime_dataset(tmp_path):
    try:
        load_gamedata(str(tmp_path))
        assert False, "Expected load_gamedata to fail when custom dataset is missing"
    except Exception as error:
        assert "Missing required runtime dataset" in str(error)


def test_load_gamedata_rejects_campaign_with_unknown_scene(tmp_path):
    dataset = _base_custom_dataset()
    dataset["campaigns"]["campaigns"][0]["scene_ids"] = ["scene.unknown"]
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    try:
        load_gamedata(str(tmp_path))
        assert False, "Expected load_gamedata to fail for an unknown campaign scene"
    except Exception as error:
        assert "unknown scene_id" in str(error)
