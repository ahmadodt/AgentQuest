import json
import os

from src.engine.loader import load_gamedata
from src.prompts.base_prompt import build_messages
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
                    "interactions": {
                        "damage_type_modifiers": {"fire": 2.0},
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
                    "interactions": {
                        "damage_type_modifiers": {},
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
                    "interactions": {
                        "damage_type_modifiers": {},
                        "min_power_to_defeat": 1,
                        "knowledge_tools_help": False,
                    },
                },
            ],
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
                    "source": {"dataset": "open5e"},
                    "interactions": {
                        "damage_type_modifiers": {"fire": 2.0},
                        "min_power_to_defeat": 1,
                        "knowledge_tools_help": True,
                    },
                }
            ],
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
    assert "description" not in llm_monster
    assert "source" not in llm_monster
    assert "cr" not in llm_monster
    assert "condition_immunities" not in llm_monster


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
    dataset["monsters"]["monsters"][0]["interactions"]["escape_allowed"] = False
    dataset["scenes"]["scenes"][0]["constraints"] = {
        "exactly_one_tool_call": True,
        "no_escape": True,
    }
    _write_runtime_dataset(str(tmp_path), dataset, use_custom_subdir=True)

    gamedata = load_gamedata(str(tmp_path))
    character = gamedata["characters_by_id"]["mage.aria"]
    scene = gamedata["scenes_by_id"]["scene.slime"]
    visible_tools = [gamedata["tools_by_id"][tool_id] for tool_id in character["tool_ids"]]

    from src.prompts.presets import BATTLE_PLAN, FULL_INFO

    battle_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=BATTLE_PLAN,
    )
    full_messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        cfg=FULL_INFO,
    )

    assert "- constraints:" not in battle_messages[1]["content"]
    assert '- constraints: {"exactly_one_tool_call": true, "no_escape": true}' in full_messages[1]["content"]


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
    assert "Fire works better on sticky enemies." in messages[1]["content"]


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
