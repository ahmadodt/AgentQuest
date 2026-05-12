import json
import os

import pytest

from src.data_pipeline.open5e_converter import (
    CuratedSelectionError,
    average_damage_from_dice_expression,
    build_monster_damage_modifiers,
    convert_curated_open5e_dataset,
    convert_open5e_dataset,
    convert_open5e_monster,
    convert_open5e_weapon,
    determine_weapon_allowed_classes,
)
from src.engine.loader import _validate_tools


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def _build_raw_fixture_files(base_dir: str) -> tuple[str, str]:
    raw_dir = os.path.join(base_dir, "raw", "open5e")
    curated_dir = os.path.join(base_dir, "curated", "open5e")

    _write_json(
        os.path.join(raw_dir, "monsters.json"),
        {
            "results": [
                {
                    "slug": "a-mi-kuk",
                    "name": "A-mi-kuk",
                    "type": "Aberration",
                    "subtype": "",
                    "group": None,
                    "size": "Huge",
                    "desc": "Fear of Flames. The creature fears fire but has no structured vulnerability.",
                    "damage_vulnerabilities": "",
                    "damage_resistances": "acid; bludgeoning, piercing, and slashing from nonmagical attacks",
                    "damage_immunities": "cold",
                    "condition_immunities": "paralyzed, restrained",
                    "challenge_rating": "7",
                    "cr": 7.0,
                },
                {
                    "slug": "ember-beast",
                    "name": "Ember Beast",
                    "type": "Beast",
                    "subtype": "",
                    "group": None,
                    "size": "Medium",
                    "desc": "A snarling creature.",
                    "damage_vulnerabilities": "fire",
                    "damage_resistances": "",
                    "damage_immunities": "",
                    "condition_immunities": "",
                    "challenge_rating": "2",
                    "cr": 2.0,
                },
            ]
        },
    )
    _write_json(
        os.path.join(raw_dir, "spells.json"),
        {
            "results": [
                {
                    "slug": "abhorrent-apparition",
                    "name": "Abhorrent Apparition",
                    "desc": "Each creature within 15 feet takes 6d8 psychic damage.",
                    "higher_level": "",
                    "range": "60 feet",
                    "components": "M",
                    "material": "a gourd",
                    "concentration": "no",
                    "requires_concentration": False,
                    "casting_time": "1 action",
                    "duration": "Instantaneous",
                    "level": "4th-level",
                    "level_int": 4,
                    "spell_level": 4,
                    "school": "illusion",
                    "dnd_class": "Bard, Sorcerer, Wizard",
                    "spell_lists": ["bard", "sorcerer", "wizard"],
                },
                {
                    "slug": "ember-bolt",
                    "name": "Ember Bolt",
                    "desc": "The target takes 2d6 fire damage.",
                    "higher_level": "",
                    "range": "60 feet",
                    "components": "V, S",
                    "material": "",
                    "concentration": "no",
                    "requires_concentration": False,
                    "casting_time": "1 action",
                    "duration": "Instantaneous",
                    "level": "1st-level",
                    "level_int": 1,
                    "spell_level": 1,
                    "school": "evocation",
                    "dnd_class": "Wizard",
                    "spell_lists": ["wizard"],
                },
            ]
        },
    )
    _write_json(
        os.path.join(raw_dir, "weapons.json"),
        {
            "results": [
                {
                    "slug": "battleaxe",
                    "name": "Battleaxe",
                    "category": "Martial Melee Weapons",
                    "cost": "10 gp",
                    "damage_dice": "1d8",
                    "damage_type": "slashing",
                    "weight": "4 lb.",
                    "properties": ["versatile (1d10)"],
                },
                {
                    "slug": "dagger",
                    "name": "Dagger",
                    "category": "Simple Melee Weapons",
                    "cost": "2 gp",
                    "damage_dice": "1d4",
                    "damage_type": "piercing",
                    "weight": "1 lb.",
                    "properties": ["finesse", "light", "thrown"],
                },
            ]
        },
    )
    _write_json(
        os.path.join(curated_dir, "selected_monsters.json"),
        {
            "version": "1.0",
            "source": "open5e",
            "selected": [
                {
                    "slug": "a-mi-kuk",
                    "notes": "Initial curated monster example",
                }
            ],
        },
    )
    _write_json(
        os.path.join(curated_dir, "selected_spells.json"),
        {
            "version": "1.0",
            "source": "open5e",
            "selected": [
                {
                    "slug": "abhorrent-apparition",
                    "notes": "Initial curated spell example",
                }
            ],
        },
    )
    _write_json(
        os.path.join(curated_dir, "selected_weapons.json"),
        {
            "version": "1.0",
            "source": "open5e",
            "selected": [
                {
                    "slug": "battleaxe",
                    "notes": "Initial curated weapon example",
                }
            ],
        },
    )

    return raw_dir, curated_dir


def test_monster_vulnerability_becomes_damage_modifier_and_weakness():
    monster = convert_open5e_monster(
        {
            "slug": "ember-beast",
            "name": "Ember Beast",
            "type": "Beast",
            "desc": "A snarling creature.",
            "damage_vulnerabilities": "fire",
            "damage_resistances": "",
            "damage_immunities": "",
            "condition_immunities": "",
            "challenge_rating": "2",
            "cr": 2.0,
        }
    )

    assert monster["weaknesses"] == ["fire"]
    assert monster["interactions"]["damage_type_modifiers"]["fire"] == 2.0


def test_monster_resistance_becomes_damage_modifier_and_resistance():
    monster = convert_open5e_monster(
        {
            "slug": "ash-shell",
            "name": "Ash Shell",
            "type": "Elemental",
            "desc": "A burning shell.",
            "damage_vulnerabilities": "",
            "damage_resistances": "fire",
            "damage_immunities": "",
            "condition_immunities": "",
            "challenge_rating": "3",
            "cr": 3.0,
        }
    )

    assert monster["resistances"] == ["fire"]
    assert monster["interactions"]["damage_type_modifiers"]["fire"] == 0.5


def test_monster_immunity_becomes_damage_modifier_and_immunity():
    monster = convert_open5e_monster(
        {
            "slug": "frost-heart",
            "name": "Frost Heart",
            "type": "Undead",
            "desc": "A silent frost spirit.",
            "damage_vulnerabilities": "",
            "damage_resistances": "",
            "damage_immunities": "cold",
            "condition_immunities": "",
            "challenge_rating": "5",
            "cr": 5.0,
        }
    )

    assert monster["immunities"] == ["cold"]
    assert monster["interactions"]["damage_type_modifiers"]["cold"] == 0.0


def test_monster_description_does_not_create_inferred_fire_weakness():
    monster = convert_open5e_monster(
        {
            "slug": "a-mi-kuk",
            "name": "A-mi-kuk",
            "type": "Aberration",
            "desc": "Fear of Flames. The creature fears fire but has no structured vulnerability.",
            "damage_vulnerabilities": "",
            "damage_resistances": "acid; bludgeoning, piercing, and slashing from nonmagical attacks",
            "damage_immunities": "cold",
            "condition_immunities": "paralyzed, restrained",
            "challenge_rating": "7",
            "cr": 7.0,
        }
    )

    assert "fire" not in monster["weaknesses"]
    assert "fire" not in monster["interactions"]["damage_type_modifiers"]


def test_monster_description_is_copied_fully():
    description = "First paragraph.\n\nSecond paragraph.\nThird line."
    monster = convert_open5e_monster(
        {
            "slug": "scribe-beast",
            "name": "Scribe Beast",
            "type": "Beast",
            "desc": description,
            "damage_vulnerabilities": "",
            "damage_resistances": "",
            "damage_immunities": "",
            "condition_immunities": "",
            "challenge_rating": "1",
            "cr": 1.0,
        }
    )

    assert monster["description"] == description


def test_monster_interactions_no_longer_include_escape_allowed():
    monster = convert_open5e_monster(
        {
            "slug": "ember-beast",
            "name": "Ember Beast",
            "type": "Beast",
            "desc": "A snarling creature.",
            "damage_vulnerabilities": "",
            "damage_resistances": "",
            "damage_immunities": "",
            "condition_immunities": "",
            "challenge_rating": "2",
            "cr": 2.0,
        }
    )

    assert "escape_allowed" not in monster["interactions"]


def test_weapon_damage_dice_parsing_handles_common_forms():
    assert average_damage_from_dice_expression("1d8") == 5
    assert average_damage_from_dice_expression("2d6") == 7
    assert average_damage_from_dice_expression("1d10") == 6


def test_damage_type_extraction_ignores_non_structured_text():
    modifiers = build_monster_damage_modifiers(
        {
            "damage_vulnerabilities": "",
            "damage_resistances": "acid; bludgeoning, piercing, and slashing from nonmagical attacks",
            "damage_immunities": "",
        }
    )

    assert modifiers == {
        "acid": 0.5,
        "bludgeoning": 0.5,
        "piercing": 0.5,
        "slashing": 0.5,
    }


def test_weapon_class_constraints_follow_simple_martial_rule():
    assert determine_weapon_allowed_classes("Simple Melee Weapons") == ["Knight", "Wizard"]
    assert determine_weapon_allowed_classes("Simple Ranged Weapons") == ["Knight", "Wizard"]
    assert determine_weapon_allowed_classes("Martial Melee Weapons") == ["Knight"]
    assert determine_weapon_allowed_classes("Martial Ranged Weapons") == ["Knight"]
    assert determine_weapon_allowed_classes("Unknown Category") == ["Knight"]


def test_converted_weapon_uses_category_constraints():
    weapon = convert_open5e_weapon(
        {
            "slug": "battleaxe",
            "name": "Battleaxe",
            "category": "Martial Melee Weapons",
            "damage_dice": "1d8",
            "damage_type": "slashing",
            "properties": [],
        }
    )

    assert weapon["constraints"]["allowed_classes"] == ["Knight"]


def test_curated_conversion_only_includes_selected_slugs(tmp_path):
    raw_dir, curated_dir = _build_raw_fixture_files(str(tmp_path))
    output_dir = os.path.join(str(tmp_path), "generated", "open5e")

    result = convert_curated_open5e_dataset(raw_dir, curated_dir, output_dir)

    assert [monster["source_slug"] for monster in result["monsters"]["monsters"]] == ["a-mi-kuk"]
    assert [tool["source_slug"] for tool in result["spells"]["tools"]] == ["abhorrent-apparition"]
    assert [tool["source_slug"] for tool in result["weapons"]["tools"]] == ["battleaxe"]


def test_missing_selected_slug_raises_clear_error(tmp_path):
    raw_dir, curated_dir = _build_raw_fixture_files(str(tmp_path))
    output_dir = os.path.join(str(tmp_path), "generated", "open5e")
    _write_json(
        os.path.join(curated_dir, "selected_weapons.json"),
        {
            "version": "1.0",
            "source": "open5e",
            "selected": [{"slug": "missing-weapon"}],
        },
    )

    with pytest.raises(CuratedSelectionError) as error:
        convert_curated_open5e_dataset(raw_dir, curated_dir, output_dir)

    assert "weapons" in str(error.value)
    assert "missing-weapon" in str(error.value)


def test_overrides_are_applied_correctly(tmp_path):
    raw_dir, curated_dir = _build_raw_fixture_files(str(tmp_path))
    output_dir = os.path.join(str(tmp_path), "generated", "open5e")
    _write_json(
        os.path.join(curated_dir, "selected_weapons.json"),
        {
            "version": "1.0",
            "source": "open5e",
            "selected": [
                {
                    "slug": "battleaxe",
                    "overrides": {
                        "constraints": {
                            "allowed_classes": ["Knight"],
                        }
                    },
                }
            ],
        },
    )

    result = convert_curated_open5e_dataset(raw_dir, curated_dir, output_dir)
    weapon = result["weapons"]["tools"][0]

    assert weapon["constraints"]["allowed_classes"] == ["Knight"]
    assert weapon["constraints"]["required_inventory"] == ["battleaxe"]
    assert weapon["constraints"]["forbidden_traits"] == []


def test_full_conversion_still_builds_tools_payloads(tmp_path):
    raw_dir, _ = _build_raw_fixture_files(str(tmp_path))
    output_dir = os.path.join(str(tmp_path), "generated", "open5e")

    result = convert_open5e_dataset(raw_dir, output_dir)

    assert len(result["monsters"]["monsters"]) == 2
    assert len(result["spells"]["tools"]) == 2
    assert len(result["weapons"]["tools"]) == 2
    _validate_tools(result["spells"])
    _validate_tools(result["weapons"])
