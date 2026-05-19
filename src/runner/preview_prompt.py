import argparse
import json
from typing import Dict, List

from src.engine.loader import DataValidationError, load_gamedata
from src.prompts.base_prompt import build_messages
from src.prompts.presets import DEFAULT_PRESET_NAME
from src.runner.runner_utils import DEFAULT_CHARACTER_ID, DEFAULT_SCENE_ID, get_visible_tools, load_preset, write_json_file


def _print_messages(messages: List[Dict[str, str]]) -> None:
    print("\n================ PROMPT PREVIEW ================\n")
    for index, message in enumerate(messages, start=1):
        role = message.get("role", "?")
        content = message.get("content", "")
        print(f"--- message {index} ({role}) ---\n{content}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--character-id", type=str, default=DEFAULT_CHARACTER_ID)
    parser.add_argument("--scene-id", type=str, default=DEFAULT_SCENE_ID)
    parser.add_argument("--prompt-format", type=str, default="json_only")
    parser.add_argument(
        "--preset",
        type=str,
        default=DEFAULT_PRESET_NAME,
        help="Prompt preset name. Use an uppercase preset variable from src/prompts/presets.py",
    )
    parser.add_argument("--save-json", type=str, default="", help="Optional path to save messages as JSON")
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        character = gamedata["characters_by_id"][args.character_id]
        scene = gamedata["scenes_by_id"][args.scene_id]

        _, _, visible_tools = get_visible_tools(gamedata, args.character_id)
        cfg = load_preset(args.preset)

        messages = build_messages(
            scene=scene,
            character=character,
            visible_tools=visible_tools,
            gamedata=gamedata,
            prompt_format=args.prompt_format,
            cfg=cfg,
        )

        print(f"\nPreset: {args.preset}")
        _print_messages(messages)

        if args.save_json:
            write_json_file(args.save_json, messages)
            print(f"\nSaved messages JSON to: {args.save_json}")

    except DataValidationError as error:
        print("Data validation error:")
        print(error)
    except Exception as error:
        print("Unexpected error:")
        print(error)


if __name__ == "__main__":
    main()
