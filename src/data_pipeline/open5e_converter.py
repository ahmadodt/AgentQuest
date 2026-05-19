import argparse
import json
import math
import os
import re


DAMAGE_TYPES = [
    "acid",
    "bludgeoning",
    "cold",
    "fire",
    "force",
    "lightning",
    "necrotic",
    "piercing",
    "poison",
    "psychic",
    "radiant",
    "slashing",
    "thunder",
]

SPELL_CLASS_MAP = {
    "artificer": "Artificer",
    "bard": "Bard",
    "cleric": "Cleric",
    "druid": "Druid",
    "fighter": "Fighter",
    "knight": "Knight",
    "paladin": "Paladin",
    "ranger": "Ranger",
    "rogue": "Rogue",
    "sorcerer": "Sorcerer",
    "warlock": "Warlock",
    "wizard": "Wizard",
}

DEFAULT_INPUT_DIR = os.path.join("data", "raw", "open5e")
DEFAULT_CURATED_DIR = os.path.join("data", "curated", "open5e")
DEFAULT_OUTPUT_DIR = os.path.join("data", "generated", "open5e")


class CuratedSelectionError(ValueError):
    """Raised when curated selections cannot be resolved against raw Open5e data."""


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _records_from_payload(payload) -> list[dict]:
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("monsters"), list):
            return payload["monsters"]
        if isinstance(payload.get("tools"), list):
            return payload["tools"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Unsupported Open5e payload format")


def _selected_items_from_payload(payload: dict) -> list[dict]:
    selected = payload.get("selected")
    if not isinstance(selected, list):
        raise ValueError("Curated selection payload must contain a 'selected' list")
    return selected


def normalize_token(value: str) -> str:
    lowered = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def extract_damage_types(raw_value: str | None) -> list[str]:
    text = (raw_value or "").lower()
    found = []
    for damage_type in DAMAGE_TYPES:
        if re.search(rf"\b{re.escape(damage_type)}\b", text):
            found.append(damage_type)
    return found


def round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def average_damage_from_dice_expression(expression: str | None, default: int = 1) -> int:
    text = (expression or "").strip().lower().replace(" ", "")
    if not text:
        return default

    constant_match = re.fullmatch(r"\d+", text)
    if constant_match:
        return int(text)

    dice_match = re.fullmatch(r"(?P<count>\d+)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?", text)
    if not dice_match:
        return default

    count = int(dice_match.group("count"))
    sides = int(dice_match.group("sides"))
    modifier = int(dice_match.group("modifier") or 0)
    average = count * (sides + 1) / 2 + modifier
    return max(1, round_half_up(average))


def _extract_damage_profile_from_spell(description: str) -> tuple[str, int] | None:
    text = description or ""
    damage_alternation = "|".join(DAMAGE_TYPES)
    match = re.search(
        rf"(?P<dice>\d+d\d+(?:\s*[+-]\s*\d+)?)\s+(?P<damage_type>{damage_alternation})\s+damage",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    damage_type = match.group("damage_type").lower()
    dice_expression = re.sub(r"\s+", "", match.group("dice"))
    return damage_type, average_damage_from_dice_expression(dice_expression)


def _normalize_classes_from_spell(record: dict) -> list[str]:
    classes = []
    seen = set()

    for raw_name in record.get("spell_lists") or []:
        normalized = SPELL_CLASS_MAP.get(str(raw_name).strip().lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            classes.append(normalized)

    dnd_class = record.get("dnd_class") or ""
    for raw_name in dnd_class.split(","):
        normalized = SPELL_CLASS_MAP.get(raw_name.strip().lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            classes.append(normalized)

    return classes


def _build_cr_bucket(cr_value: float) -> str:
    if cr_value < 1:
        return "cr_under_1"
    if cr_value < 5:
        return "cr_1_4"
    if cr_value < 11:
        return "cr_5_10"
    if cr_value < 17:
        return "cr_11_16"
    return "cr_17_plus"


def _coerce_cr(record: dict) -> float:
    raw_cr = record.get("cr")
    if isinstance(raw_cr, (int, float)):
        return float(raw_cr)

    challenge_rating = str(record.get("challenge_rating") or "").strip()
    if "/" in challenge_rating:
        numerator, denominator = challenge_rating.split("/", 1)
        try:
            return float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0

    try:
        return float(challenge_rating)
    except ValueError:
        return 0.0


def build_monster_damage_modifiers(record: dict) -> dict:
    modifiers = {}

    for damage_type in extract_damage_types(record.get("damage_vulnerabilities")):
        modifiers[damage_type] = 2.0

    for damage_type in extract_damage_types(record.get("damage_resistances")):
        modifiers[damage_type] = 0.5

    for damage_type in extract_damage_types(record.get("damage_immunities")):
        modifiers[damage_type] = 0.0

    return modifiers


def determine_weapon_allowed_classes(category: str | None) -> list[str]:
    text = (category or "").lower()
    if "simple" in text:
        return ["Knight", "Wizard"]
    if "martial" in text:
        return ["Knight"]
    return ["Knight"]


def _merge_override_values(base_value, override_value):
    if isinstance(base_value, dict) and isinstance(override_value, dict):
        merged = dict(base_value)
        for key, value in override_value.items():
            merged[key] = _merge_override_values(merged.get(key), value)
        return merged
    return override_value


def apply_overrides(record: dict, overrides: dict | None) -> dict:
    if not overrides:
        return record
    return _merge_override_values(record, overrides)


def _select_records(raw_records: list[dict], curated_items: list[dict], category_name: str) -> list[dict]:
    records_by_slug = {}
    for record in raw_records:
        slug = record.get("slug")
        if isinstance(slug, str) and slug:
            records_by_slug[slug] = record

    selected_records = []
    missing_slugs = []

    for item in curated_items:
        slug = item.get("slug")
        if slug not in records_by_slug:
            missing_slugs.append(str(slug))
            continue
        selected_records.append(
            {
                "raw": records_by_slug[slug],
                "selection": item,
            }
        )

    if missing_slugs:
        raise CuratedSelectionError(
            f"Missing selected slug(s) in {category_name}: {', '.join(missing_slugs)}"
        )

    return selected_records


def convert_open5e_monster(record: dict) -> dict:
    slug = record["slug"]
    monster_type = normalize_token(record.get("type") or "unknown")
    cr_value = _coerce_cr(record)
    modifiers = build_monster_damage_modifiers(record)
    tags = []

    for candidate in [
        record.get("type"),
        record.get("subtype"),
        record.get("group"),
        record.get("size"),
        _build_cr_bucket(cr_value),
    ]:
        token = normalize_token(candidate or "")
        if token and token not in tags:
            tags.append(token)

    return {
        "monster_id": f"open5e.monster.{slug}",
        "damage_profile": f"open5e.profile.{slug}",
        "source_slug": slug,
        "name": record.get("name", slug),
        "type": monster_type,
        "description": record.get("desc", ""),
        "tags": tags,
        "challenge_rating": record.get("challenge_rating"),
        "cr": cr_value,
        "weaknesses": extract_damage_types(record.get("damage_vulnerabilities")),
        "resistances": extract_damage_types(record.get("damage_resistances")),
        "immunities": extract_damage_types(record.get("damage_immunities")),
        "condition_immunities": [
            item.strip()
            for item in str(record.get("condition_immunities") or "").split(",")
            if item.strip()
        ],
        "special_rules": [],
        "interactions": {
            "min_power_to_defeat": max(1, math.ceil(cr_value)) if cr_value > 0 else 1,
            "knowledge_tools_help": False,
        },
        "damage_modifier_overrides": modifiers,
        "source": {
            "dataset": "open5e",
            "document_slug": record.get("document__slug"),
            "document_title": record.get("document__title"),
            "document_url": record.get("document__url"),
        },
    }


def convert_open5e_spell(record: dict) -> dict:
    slug = record["slug"]
    description = record.get("desc", "")
    damage_profile = _extract_damage_profile_from_spell(description)
    effects = {}
    category = "utility"

    if damage_profile is not None:
        category = "attack"
        effects["damage_type"] = damage_profile[0]
        effects["base_power"] = damage_profile[1]
    else:
        effects["combat_effect"] = False

    return {
        "tool_id": f"open5e.spell.{slug}",
        "source_slug": slug,
        "label": record.get("name", slug),
        "description": description,
        "category": category,
        "args": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "slot_level": {"type": "integer", "minimum": 0, "maximum": 9},
            },
            "required": ["target"],
        },
        "constraints": {
            "allowed_classes": _normalize_classes_from_spell(record),
            "required_inventory": [],
            "forbidden_traits": [],
        },
        "effects": effects,
        "spell_details": {
            "level": record.get("level"),
            "level_int": record.get("level_int"),
            "spell_level": record.get("spell_level"),
            "school": record.get("school"),
            "range": record.get("range"),
            "casting_time": record.get("casting_time"),
            "duration": record.get("duration"),
            "components": record.get("components"),
            "material": record.get("material"),
            "concentration": record.get("concentration"),
            "requires_concentration": record.get("requires_concentration"),
            "higher_level": record.get("higher_level"),
            "spell_lists": record.get("spell_lists") or [],
        },
        "source": {
            "dataset": "open5e",
            "document_slug": record.get("document__slug"),
            "document_title": record.get("document__title"),
            "document_url": record.get("document__url"),
        },
    }


def convert_open5e_weapon(record: dict) -> dict:
    slug = record["slug"]
    damage_dice = record.get("damage_dice") or ""
    properties = record.get("properties") or []
    description_parts = [
        f"{record.get('category', 'Weapon')}.",
        f"Deals {damage_dice or 'unknown'} {record.get('damage_type', 'physical')} damage.",
    ]
    if properties:
        description_parts.append(f"Properties: {', '.join(properties)}.")

    return {
        "tool_id": f"open5e.weapon.{slug}",
        "source_slug": slug,
        "label": record.get("name", slug),
        "description": " ".join(description_parts),
        "category": "attack",
        "args": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
            },
            "required": ["target"],
        },
        "constraints": {
            "allowed_classes": determine_weapon_allowed_classes(record.get("category")),
            "required_inventory": [slug],
            "forbidden_traits": [],
        },
        "effects": {
            "damage_type": normalize_token(record.get("damage_type") or "physical"),
            "base_power": average_damage_from_dice_expression(damage_dice, default=1),
        },
        "weapon_details": {
            "category": record.get("category"),
            "cost": record.get("cost"),
            "damage_dice": damage_dice,
            "damage_type": record.get("damage_type"),
            "weight": record.get("weight"),
            "properties": properties,
        },
        "source": {
            "dataset": "open5e",
            "document_slug": record.get("document__slug"),
            "document_title": record.get("document__title"),
            "document_url": record.get("document__url"),
        },
    }


def _build_monster_payload(monsters: list[dict]) -> dict:
    return {
        "version": "1.0",
        "source": "open5e",
        "generated_from": "local_json",
        "monsters": monsters,
    }


def _build_damage_profile_payload(monsters: list[dict]) -> dict:
    profiles = {}
    for monster in monsters:
        profile_id = monster.get("damage_profile")
        modifiers = monster.get("damage_modifier_overrides", {}) or {}
        if isinstance(profile_id, str) and profile_id:
            profiles[profile_id] = dict(modifiers)
    return {
        "version": "1.0",
        "source": "open5e",
        "generated_from": "local_json",
        "profiles": profiles,
    }


def _build_tool_payload(tools: list[dict]) -> dict:
    return {
        "version": "1.0",
        "source": "open5e",
        "generated_from": "local_json",
        "tools": tools,
    }


def _write_output_payloads(output_dir: str, monsters: list[dict], spells: list[dict], weapons: list[dict]) -> dict:
    monster_payload = _build_monster_payload(monsters)
    damage_profile_payload = _build_damage_profile_payload(monsters)
    spell_payload = _build_tool_payload(spells)
    weapon_payload = _build_tool_payload(weapons)

    _write_json(os.path.join(output_dir, "monsters.json"), monster_payload)
    _write_json(os.path.join(output_dir, "damage_profiles.json"), damage_profile_payload)
    _write_json(os.path.join(output_dir, "tools_spells.json"), spell_payload)
    _write_json(os.path.join(output_dir, "tools_weapons.json"), weapon_payload)

    return {
        "monsters": monster_payload,
        "damage_profiles": damage_profile_payload,
        "spells": spell_payload,
        "weapons": weapon_payload,
        "output_dir": output_dir,
    }


def convert_open5e_dataset(input_dir: str = DEFAULT_INPUT_DIR, output_dir: str = DEFAULT_OUTPUT_DIR) -> dict:
    monsters = _records_from_payload(_load_json(os.path.join(input_dir, "monsters.json")))
    spells = _records_from_payload(_load_json(os.path.join(input_dir, "spells.json")))
    weapons = _records_from_payload(_load_json(os.path.join(input_dir, "weapons.json")))

    converted_monsters = [convert_open5e_monster(record) for record in monsters]
    converted_spells = [convert_open5e_spell(record) for record in spells]
    converted_weapons = [convert_open5e_weapon(record) for record in weapons]

    return _write_output_payloads(output_dir, converted_monsters, converted_spells, converted_weapons)


def convert_curated_open5e_dataset(
    input_dir: str = DEFAULT_INPUT_DIR,
    curated_dir: str = DEFAULT_CURATED_DIR,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict:
    raw_monsters = _records_from_payload(_load_json(os.path.join(input_dir, "monsters.json")))
    raw_spells = _records_from_payload(_load_json(os.path.join(input_dir, "spells.json")))
    raw_weapons = _records_from_payload(_load_json(os.path.join(input_dir, "weapons.json")))

    selected_monsters = _selected_items_from_payload(
        _load_json(os.path.join(curated_dir, "selected_monsters.json"))
    )
    selected_spells = _selected_items_from_payload(
        _load_json(os.path.join(curated_dir, "selected_spells.json"))
    )
    selected_weapons = _selected_items_from_payload(
        _load_json(os.path.join(curated_dir, "selected_weapons.json"))
    )

    converted_monsters = []
    for item in _select_records(raw_monsters, selected_monsters, "monsters"):
        converted = convert_open5e_monster(item["raw"])
        converted_monsters.append(apply_overrides(converted, item["selection"].get("overrides")))

    converted_spells = []
    for item in _select_records(raw_spells, selected_spells, "spells"):
        converted = convert_open5e_spell(item["raw"])
        converted_spells.append(apply_overrides(converted, item["selection"].get("overrides")))

    converted_weapons = []
    for item in _select_records(raw_weapons, selected_weapons, "weapons"):
        converted = convert_open5e_weapon(item["raw"])
        converted_weapons.append(apply_overrides(converted, item["selection"].get("overrides")))

    return _write_output_payloads(output_dir, converted_monsters, converted_spells, converted_weapons)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert local Open5e JSON files into AgentQuest JSON records.")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--curated-dir", default=DEFAULT_CURATED_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--curated", action="store_true")
    args = parser.parse_args()

    if args.curated:
        result = convert_curated_open5e_dataset(
            input_dir=args.input_dir,
            curated_dir=args.curated_dir,
            output_dir=args.output_dir,
        )
    else:
        result = convert_open5e_dataset(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
        )

    print(
        "Converted Open5e data to AgentQuest JSON: "
        f"{len(result['monsters']['monsters'])} monsters, "
        f"{len(result['spells']['tools'])} spells, "
        f"{len(result['weapons']['tools'])} weapons "
        f"-> {result['output_dir']}"
    )


if __name__ == "__main__":
    main()
