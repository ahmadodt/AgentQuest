import argparse
import json
import os
from datetime import datetime

from src.engine.loader import load_gamedata, DataValidationError
from src.models.config import load_runtime_prompt_config
from src.runner.runner_utils import (
    DEFAULT_CHARACTER_ID,
    DEFAULT_SCENE_ID,
    default_run_path,
    ensure_dir,
    execute_scene_run,
    load_preset,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--character-id", type=str, default=DEFAULT_CHARACTER_ID)
    parser.add_argument("--scene-id", type=str, default=DEFAULT_SCENE_ID)
    parser.add_argument("--prompt-format", type=str, default="")
    parser.add_argument("--preset", type=str, default="")

    # model calling
    parser.add_argument(
        "--model-key",
        type=str,
        default="",
        help="Optional backend override. Defaults to the backend in configs/run_config.json.",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)

    # logging
    parser.add_argument(
    "--save-run",
    type=str,
    default=default_run_path("run_one"),
    help="Path to save full run log as JSON. Defaults to runs/run_one_<timestamp>.json",
    )
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        runtime_prompt_cfg = load_runtime_prompt_config()
        prompt_format = args.prompt_format or runtime_prompt_cfg.prompt_format
        preset_name = args.preset or runtime_prompt_cfg.preset_name

        cfg = load_preset(preset_name)

        scene_run = execute_scene_run(
            gamedata=gamedata,
            character_id=args.character_id,
            scene_id=args.scene_id,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=args.model_key,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        raw = scene_run["raw_model_output"]
        verdict = scene_run["verdict"]
        metadata = scene_run["metadata"]

        print("\n=== MODEL OUTPUT ===")
        print(raw)

        print("\n=== VERDICT ===")
        print(json.dumps(verdict, indent=2, ensure_ascii=False))

        print("\n=== METADATA ===")
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        if args.save_run:
            ensure_dir(os.path.dirname(args.save_run))
            runlog = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_dir": args.data_dir,
                "character_id": args.character_id,
                "scene_id": args.scene_id,
                "preset": preset_name,
                "prompt_format": prompt_format,
                **scene_run,
            }
            with open(args.save_run, "w", encoding="utf-8") as f:
                json.dump(runlog, f, ensure_ascii=False, indent=2)
            print(f"\nSaved run log to: {args.save_run}")

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)
    except Exception as e:
        import traceback
        print("✖ Unexpected error:")
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
