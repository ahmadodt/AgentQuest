import argparse
import json
from typing import Any, Dict, List

from src.engine.loader import load_gamedata, DataValidationError
from src.prompts.base_prompt import build_messages


def _print_messages(messages: List[Dict[str, str]]) -> None:
    print("\n================ PROMPT PREVIEW ================\n")
    for i, m in enumerate(messages, start=1):
        role = m.get("role", "?")
        content = m.get("content", "")
        print(f"--- message {i} ({role}) ---\n{content}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--character-id", type=str, default="knight.bram")
    parser.add_argument("--scene-id", type=str, default="scene.001.goblin_alley")
    parser.add_argument("--prompt-format", type=str, default="json_only")
    parser.add_argument("--save-json", type=str, default="", help="Optional path to save messages as JSON")
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)

        character = gamedata["characters_by_id"][args.character_id]
        scene = gamedata["scenes_by_id"][args.scene_id]

        visible_tool_ids = character["tool_ids"]
        visible_tools = [gamedata["tools_by_id"][tid] for tid in visible_tool_ids]

        messages = build_messages(
            scene=scene,
            character=character,
            visible_tools=visible_tools,
            prompt_format=args.prompt_format,
        )

        _print_messages(messages)

        if args.save_json:
            with open(args.save_json, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            print(f"\nSaved messages JSON to: {args.save_json}")

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)
    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()