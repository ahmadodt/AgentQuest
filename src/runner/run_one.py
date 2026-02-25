import argparse
import json
import os
from datetime import datetime
from typing import Dict, List

from src.engine.loader import load_gamedata, DataValidationError
from src.engine.validator import validate

from src.prompts.base_prompt import build_messages
from src.prompts.prompt_config import DEFAULT_PROMPT_CONFIG, PromptConfig

from src.models.registry import build_handler


def _load_preset(preset_name: str) -> PromptConfig:
    """
    Same behavior as preview_prompt.py
    """
    if preset_name == "default":
        return DEFAULT_PROMPT_CONFIG

    try:
        from configs import prompt_presets  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import configs/prompt_presets.py. "
            "Create it (or use --preset default). "
            f"Original error: {e}"
        )

    if not hasattr(prompt_presets, preset_name):
        available = sorted(
            [
                k
                for k in dir(prompt_presets)
                if k.isupper() and isinstance(getattr(prompt_presets, k), PromptConfig)
            ]
        )
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available presets: {available} "
            "(Preset names are the UPPERCASE variables in configs/prompt_presets.py)"
        )

    cfg = getattr(prompt_presets, preset_name)
    if not isinstance(cfg, PromptConfig):
        raise TypeError(f"Preset '{preset_name}' exists but is not a PromptConfig.")
    return cfg


def _ensure_dir(dirpath: str) -> None:
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--character-id", type=str, default="knight.bram")
    parser.add_argument("--scene-id", type=str, default="scene.001.goblin_alley")
    parser.add_argument("--prompt-format", type=str, default="json_only")
    parser.add_argument("--preset", type=str, default="default")

    # model calling
    parser.add_argument("--model-key", type=str, default="openai_compat")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)

    # logging
    parser.add_argument("--save-run", type=str, default="", help="Optional path to save full run log as JSON")

    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)

        character = gamedata["characters_by_id"][args.character_id]
        scene = gamedata["scenes_by_id"][args.scene_id]

        # IMPORTANT: identical to preview_prompt.py
        visible_tool_ids = character["tool_ids"]
        visible_tools = [gamedata["tools_by_id"][tid] for tid in visible_tool_ids]

        cfg = _load_preset(args.preset)

        messages = build_messages(
            scene=scene,
            character=character,
            visible_tools=visible_tools,
            gamedata=gamedata,
            prompt_format=args.prompt_format,
            cfg=cfg,
        )

        handler = build_handler(args.model_key)
        gen = handler.generate(
            messages,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        raw = (gen.raw_text or "").strip()

        print("\n=== MODEL OUTPUT ===")
        print(raw)

        verdict = validate(
            gamedata=gamedata,
            character_id=args.character_id,
            scene_id=args.scene_id,
            visible_tool_ids=visible_tool_ids,
            raw_model_output=raw,
        )

        print("\n=== VERDICT ===")
        print(json.dumps(verdict, indent=2, ensure_ascii=False))

        print("\n=== METADATA ===")
        print(json.dumps(gen.metadata, indent=2, ensure_ascii=False))
        
        if args.save_run:
            _ensure_dir(os.path.dirname(args.save_run))
            runlog = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_dir": args.data_dir,
                "character_id": args.character_id,
                "scene_id": args.scene_id,
                "preset": args.preset,
                "prompt_format": args.prompt_format,
                "visible_tool_ids": visible_tool_ids,
                "messages": messages,
                "raw_model_output": raw,
                "metadata": gen.metadata,
                "verdict": verdict,
            }
            with open(args.save_run, "w", encoding="utf-8") as f:
                json.dump(runlog, f, ensure_ascii=False, indent=2)
            print(f"\nSaved run log to: {args.save_run}")

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)
    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()