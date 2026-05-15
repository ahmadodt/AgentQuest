import argparse
import json
import os
import sys

from src.engine.loader import load_gamedata
from src.engine.validator import ToolCallValidator


def _default_value_for_schema(prop_name: str, spec: dict) -> object:
    if "enum" in spec and isinstance(spec["enum"], list) and spec["enum"]:
        return spec["enum"][0]

    prop_type = spec.get("type")
    if prop_type == "string":
        if prop_name == "direction":
            return "backtrack"
        if prop_name == "surface":
            return "wall"
        return "target"
    if prop_type == "integer":
        return 1
    if prop_type == "number":
        return 1.0
    if prop_type == "boolean":
        return True
    if prop_type == "array":
        return []
    if prop_type == "object":
        return {}
    return "value"


def _build_tool_call(tool: dict) -> str:
    args_schema = tool.get("args", {}) or {}
    properties = args_schema.get("properties", {}) or {}
    required = args_schema.get("required", []) or []
    arguments = {}
    for key in required:
        spec = properties.get(key, {}) if isinstance(properties.get(key), dict) else {}
        arguments[key] = _default_value_for_schema(key, spec)
    return json.dumps({"tool_id": tool["tool_id"], "arguments": arguments}, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    args = parser.parse_args()

    gamedata = load_gamedata(args.data_dir)
    scenes_by_id = gamedata["scenes_by_id"]
    characters_by_id = gamedata["characters_by_id"]
    tools_by_id = gamedata["tools_by_id"]

    failures = []
    total_pairs = 0
    solved_pairs = 0

    for scene_id, scene in scenes_by_id.items():
        print(f"\nScene: {scene_id} ({scene.get('title', scene_id)})")
        for character_id, character in characters_by_id.items():
            total_pairs += 1
            validator = ToolCallValidator(
                gamedata=gamedata,
                character_id=character_id,
                scene_id=scene_id,
                visible_tool_ids=character.get("tool_ids", []),
            )
            valid_tools = []
            invalid_tools = []

            for tool_id in character.get("tool_ids", []):
                tool = tools_by_id[tool_id]
                raw = _build_tool_call(tool)
                verdict = validator.validate(raw)
                result = {
                    "tool_id": tool_id,
                    "reason": verdict.get("reason", ""),
                    "reason_code": verdict.get("reason_code"),
                }
                if verdict.get("outcome") == "success":
                    valid_tools.append(result)
                else:
                    invalid_tools.append(result)

            if valid_tools:
                solved_pairs += 1
                print(f"  {character_id}: OK ({len(valid_tools)} valid / {len(invalid_tools)} invalid)")
            else:
                failures.append(
                    {
                        "scene_id": scene_id,
                        "character_id": character_id,
                        "invalid_tools": invalid_tools,
                    }
                )
                print(f"  {character_id}: FAIL (0 valid / {len(invalid_tools)} invalid)")

            if valid_tools:
                valid_ids = ", ".join(item["tool_id"] for item in valid_tools)
                print(f"    valid: {valid_ids}")
            if invalid_tools:
                for item in invalid_tools:
                    print(
                        f"    invalid: {item['tool_id']} -> "
                        f"{item.get('reason_code') or 'unknown_reason'} | {item['reason']}"
                    )

    print("\nSummary:")
    print(f"  scene-character pairs: {total_pairs}")
    print(f"  solvable pairs: {solved_pairs}")
    print(f"  unsolved pairs: {len(failures)}")

    if failures:
        print("\nUnsolved scene-character pairs:")
        for item in failures:
            print(f"  {item['scene_id']} :: {item['character_id']}")
        return 1

    print("\nEvery scene is solvable by every character.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
