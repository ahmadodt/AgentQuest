import argparse
import json

from src.engine.loader import load_gamedata, DataValidationError
from src.models.config import load_runtime_model_config
from src.runtime_paths import get_data_dir
from src.runner.runner_utils import (
    DEFAULT_CHARACTER_ID,
    DEFAULT_SCENE_ID,
    build_run_log_payload,
    execute_scene_run,
    resolve_prompt_settings,
    save_result_run_log,
    write_json_file,
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default=get_data_dir())
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
    default=None,
    help="Optional explicit path to save the run log as JSON. Defaults to results/scenes/<scene_id>/<model>/<timestamp>.json",
    )
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        runtime_model_cfg = load_runtime_model_config()
        prompt_format, preset_name, cfg = resolve_prompt_settings(
            prompt_format=args.prompt_format,
            preset_name=args.preset,
        )

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
        
        runlog = build_run_log_payload(
            run_mode="scene",
            data_dir=args.data_dir,
            preset_name=preset_name,
            prompt_format=prompt_format,
            character_id=args.character_id,
            scene_id=args.scene_id,
            run_result=scene_run,
        )
        if args.save_run is not None:
            write_json_file(args.save_run, runlog)
            print(f"\nSaved run log to: {args.save_run}")
        else:
            save_path = save_result_run_log("scene", runlog, runtime_model_cfg.model_name)
            print(f"\nSaved run log to: {save_path}")

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
