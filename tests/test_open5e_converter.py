from src.data_pipeline.open5e_converter import (
    average_damage_from_dice_expression,
    build_monster_damage_modifiers,
    convert_open5e_dataset,
    convert_open5e_monster,
)
from src.engine.loader import _validate_monsters, _validate_tools


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


def test_generated_records_match_loader_required_fields(tmp_path):
    raw_dir = tmp_path / "raw" / "open5e"
    output_dir = tmp_path / "generated" / "open5e"
    raw_dir.mkdir(parents=True)

    (raw_dir / "monsters.json").write_text(
        """{
  "results": [
    {
      "slug": "ember-beast",
      "name": "Ember Beast",
      "type": "Beast",
      "subtype": "",
      "group": null,
      "size": "Medium",
      "desc": "A snarling creature.",
      "damage_vulnerabilities": "fire",
      "damage_resistances": "",
      "damage_immunities": "",
      "condition_immunities": "",
      "challenge_rating": "2",
      "cr": 2.0
    }
  ]
}""",
        encoding="utf-8",
    )
    (raw_dir / "spells.json").write_text(
        """{
  "results": [
    {
      "slug": "ember-bolt",
      "name": "Ember Bolt",
      "desc": "The target takes 2d6 fire damage.",
      "higher_level": "",
      "range": "60 feet",
      "components": "V, S",
      "material": "",
      "concentration": "no",
      "requires_concentration": false,
      "casting_time": "1 action",
      "duration": "Instantaneous",
      "level": "1st-level",
      "level_int": 1,
      "spell_level": 1,
      "school": "evocation",
      "dnd_class": "Wizard",
      "spell_lists": ["wizard"]
    }
  ]
}""",
        encoding="utf-8",
    )
    (raw_dir / "weapons.json").write_text(
        """{
  "results": [
    {
      "slug": "battleaxe",
      "name": "Battleaxe",
      "category": "Martial Melee Weapons",
      "cost": "10 gp",
      "damage_dice": "1d8",
      "damage_type": "slashing",
      "weight": "4 lb.",
      "properties": ["versatile (1d10)"]
    }
  ]
}""",
        encoding="utf-8",
    )

    result = convert_open5e_dataset(raw_dir, output_dir)

    _validate_monsters(result["monsters"])
    _validate_tools(result["spells"])
    _validate_tools(result["weapons"])
