import json
import os


class DataValidationError(Exception):
    """Raised when game data is invalid (missing fields, bad references, duplicates)."""
    pass


def _load_json_file(path: str) -> dict:
    if not os.path.exists(path):
        raise DataValidationError(f"Missing file: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise DataValidationError(f"Invalid JSON in {path}: {e}") from e


def _require(obj: dict, key: str, ctx: str):
    if key not in obj:
        raise DataValidationError(f"Missing required field '{key}' in {ctx}")


def _require_type(value, expected_type, ctx: str, key: str):
    if not isinstance(value, expected_type):
        raise DataValidationError(
            f"Field '{key}' has wrong type in {ctx}. Expected {expected_type.__name__}, got {type(value).__name__}"
        )


def _index_by_id(items: list, id_key: str, ctx: str) -> dict:
    seen = set()
    out = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise DataValidationError(f"Item #{i} in {ctx} must be an object/dict.")
        _require(item, id_key, f"{ctx}[{i}]")
        _require_type(item[id_key], str, f"{ctx}[{i}]", id_key)

        _id = item[id_key]
        if _id in seen:
            raise DataValidationError(f"Duplicate {id_key} '{_id}' in {ctx}")
        seen.add(_id)
        out[_id] = item
    return out


def _validate_tools(tools_root: dict) -> dict:
    ctx = "tools.json"
    _require(tools_root, "tools", ctx)
    _require_type(tools_root["tools"], list, ctx, "tools")

    tools = tools_root["tools"]
    tools_by_id = _index_by_id(tools, "tool_id", ctx)

    # Validate each tool structure
    for tool_id, tool in tools_by_id.items():
        tctx = f"{ctx}:{tool_id}"

        for key in ["label", "description", "category", "args", "constraints"]:
            _require(tool, key, tctx)

        _require_type(tool["label"], str, tctx, "label")
        _require_type(tool["description"], str, tctx, "description")
        _require_type(tool["category"], str, tctx, "category")

        # args schema
        args = tool["args"]
        if not isinstance(args, dict):
            raise DataValidationError(f"'args' must be an object in {tctx}")

        _require(args, "type", tctx + ".args")
        _require(args, "properties", tctx + ".args")
        _require(args, "required", tctx + ".args")

        if args["type"] != "object":
            raise DataValidationError(f"{tctx}: args.type must be 'object'")

        if not isinstance(args["properties"], dict):
            raise DataValidationError(f"{tctx}: args.properties must be an object/dict")

        if not isinstance(args["required"], list):
            raise DataValidationError(f"{tctx}: args.required must be a list")

        # required keys must be defined in properties
        prop_keys = set(args["properties"].keys())
        for req_key in args["required"]:
            if not isinstance(req_key, str):
                raise DataValidationError(f"{tctx}: args.required entries must be strings")
            if req_key not in prop_keys:
                raise DataValidationError(
                    f"{tctx}: args.required includes '{req_key}' but it's missing from args.properties"
                )

        # constraints
        constraints = tool["constraints"]
        if not isinstance(constraints, dict):
            raise DataValidationError(f"{tctx}: constraints must be an object/dict")

        for key in ["allowed_classes", "required_inventory", "forbidden_traits"]:
            _require(constraints, key, tctx + ".constraints")
            if not isinstance(constraints[key], list):
                raise DataValidationError(f"{tctx}: constraints.{key} must be a list")

        # Optional sections: effects/ui are allowed but not required
        if "effects" in tool and not isinstance(tool["effects"], dict):
            raise DataValidationError(f"{tctx}: effects must be an object/dict if present")
        if "ui" in tool and not isinstance(tool["ui"], dict):
            raise DataValidationError(f"{tctx}: ui must be an object/dict if present")

    return tools_by_id


def _validate_characters(char_root: dict, tools_by_id: dict) -> dict:
    ctx = "characters.json"
    _require(char_root, "characters", ctx)
    _require_type(char_root["characters"], list, ctx, "characters")

    characters = char_root["characters"]
    chars_by_id = _index_by_id(characters, "character_id", ctx)

    for char_id, ch in chars_by_id.items():
        cctx = f"{ctx}:{char_id}"
        for key in ["name", "class", "inventory", "traits", "tool_ids"]:
            _require(ch, key, cctx)

        _require_type(ch["name"], str, cctx, "name")
        _require_type(ch["class"], str, cctx, "class")

        if not isinstance(ch["inventory"], list):
            raise DataValidationError(f"{cctx}: inventory must be a list")
        if not isinstance(ch["traits"], list):
            raise DataValidationError(f"{cctx}: traits must be a list")
        if not isinstance(ch["tool_ids"], list):
            raise DataValidationError(f"{cctx}: tool_ids must be a list")

        # Check that all tool_ids exist + class is allowed by tool constraints
        for tid in ch["tool_ids"]:
            if not isinstance(tid, str):
                raise DataValidationError(f"{cctx}: tool_ids entries must be strings")
            if tid not in tools_by_id:
                raise DataValidationError(f"{cctx}: unknown tool_id referenced: '{tid}'")

            tool = tools_by_id[tid]
            allowed_classes = tool["constraints"]["allowed_classes"]
            if ch["class"] not in allowed_classes:
                raise DataValidationError(
                    f"{cctx}: character class '{ch['class']}' is not allowed to use tool '{tid}' "
                    f"(allowed_classes={allowed_classes})"
                )

    return chars_by_id


def _validate_monsters(mon_root: dict) -> dict:
    ctx = "monsters.json"
    _require(mon_root, "monsters", ctx)
    _require_type(mon_root["monsters"], list, ctx, "monsters")

    monsters = mon_root["monsters"]
    monsters_by_id = _index_by_id(monsters, "monster_id", ctx)

    for mid, m in monsters_by_id.items():
        mctx = f"{ctx}:{mid}"
        for key in ["name", "type", "description", "interactions"]:
            _require(m, key, mctx)

        _require_type(m["name"], str, mctx, "name")
        _require_type(m["type"], str, mctx, "type")
        _require_type(m["description"], str, mctx, "description")

        interactions = m["interactions"]
        if not isinstance(interactions, dict):
            raise DataValidationError(f"{mctx}: interactions must be an object/dict")

        for key in ["damage_type_modifiers", "min_power_to_defeat", "escape_allowed"]:
            _require(interactions, key, mctx + ".interactions")

        if not isinstance(interactions["damage_type_modifiers"], dict):
            raise DataValidationError(f"{mctx}: interactions.damage_type_modifiers must be an object/dict")

        # allow int or float
        if not isinstance(interactions["min_power_to_defeat"], (int, float)):
            raise DataValidationError(f"{mctx}: interactions.min_power_to_defeat must be a number")

        if not isinstance(interactions["escape_allowed"], bool):
            raise DataValidationError(f"{mctx}: interactions.escape_allowed must be boolean")

    return monsters_by_id


def _validate_scenes(scene_root: dict, monsters_by_id: dict) -> dict:
    ctx = "scenes.json"
    _require(scene_root, "scenes", ctx)
    _require_type(scene_root["scenes"], list, ctx, "scenes")

    scenes = scene_root["scenes"]
    scenes_by_id = _index_by_id(scenes, "scene_id", ctx)

    for sid, s in scenes_by_id.items():
        sctx = f"{ctx}:{sid}"
        for key in [
            "title",
            "location",
            "monster_id",
            "narrative",
            "knowledge_level",
            "constraints",
            "success_condition",
            "failure_condition",
        ]:
            _require(s, key, sctx)

        _require_type(s["title"], str, sctx, "title")
        _require_type(s["location"], str, sctx, "location")
        _require_type(s["monster_id"], str, sctx, "monster_id")
        _require_type(s["narrative"], str, sctx, "narrative")
        _require_type(s["knowledge_level"], str, sctx, "knowledge_level")

        if not isinstance(s["constraints"], dict):
            raise DataValidationError(f"{sctx}: constraints must be an object/dict")
        if not isinstance(s["success_condition"], dict):
            raise DataValidationError(f"{sctx}: success_condition must be an object/dict")
        if not isinstance(s["failure_condition"], dict):
            raise DataValidationError(f"{sctx}: failure_condition must be an object/dict")

        # Reference check (monster only now)
        if s["monster_id"] not in monsters_by_id:
            raise DataValidationError(f"{sctx}: unknown monster_id '{s['monster_id']}'")

        # Consistency: if scene says no_escape, monster must have escape_allowed false
        no_escape = bool(s["constraints"].get("no_escape", False))
        if no_escape:
            monster = monsters_by_id[s["monster_id"]]
            escape_allowed = monster["interactions"]["escape_allowed"]
            if escape_allowed:
                raise DataValidationError(
                    f"{sctx}: constraints.no_escape is true but monster '{s['monster_id']}' "
                    f"has interactions.escape_allowed == true"
                )

    return scenes_by_id

def load_gamedata(data_dir: str = "data") -> dict:
    """
    Loads and validates all game JSON files, returning indexed maps for fast access.
    """
    tools_path = os.path.join(data_dir, "tools.json")
    chars_path = os.path.join(data_dir, "characters.json")
    monsters_path = os.path.join(data_dir, "monsters.json")
    scenes_path = os.path.join(data_dir, "scenes.json")

    tools_root = _load_json_file(tools_path)
    chars_root = _load_json_file(chars_path)
    monsters_root = _load_json_file(monsters_path)
    scenes_root = _load_json_file(scenes_path)

    tools_by_id = _validate_tools(tools_root)
    characters_by_id = _validate_characters(chars_root, tools_by_id)
    monsters_by_id = _validate_monsters(monsters_root)
    scenes_by_id = _validate_scenes(scenes_root, monsters_by_id)

    return {
        "tools_by_id": tools_by_id,
        "characters_by_id": characters_by_id,
        "monsters_by_id": monsters_by_id,
        "scenes_by_id": scenes_by_id,
        "raw": {
            "tools": tools_root.get("tools", []),
            "characters": chars_root.get("characters", []),
            "monsters": monsters_root.get("monsters", []),
            "scenes": scenes_root.get("scenes", []),
        },
    }