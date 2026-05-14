import argparse
import json
import os
from datetime import datetime

from src.engine.loader import DataValidationError, load_gamedata
from src.models.config import load_runtime_model_config, load_runtime_prompt_config
from src.runner.runner_utils import (
    DEFAULT_CAMPAIGN_ID,
    DEFAULT_CHARACTER_ID,
    default_run_path,
    ensure_dir,
    execute_campaign_run,
    load_preset,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--campaign-id", type=str, default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--character-id", type=str, default=DEFAULT_CHARACTER_ID)
    parser.add_argument("--prompt-format", type=str, default="")
    parser.add_argument("--preset", type=str, default="")
    parser.add_argument(
        "--model-key",
        type=str,
        default="",
        help="Optional backend override. Defaults to the backend in configs/run_config.json.",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running remaining scenes after a scene fails.",
    )
    parser.add_argument(
        "--save-run",
        type=str,
        default=default_run_path("run_campaign"),
        help="Path to save full campaign run log as JSON. Defaults to runs/run_campaign_<timestamp>.json",
    )
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        runtime_prompt_cfg = load_runtime_prompt_config()
        runtime_model_cfg = load_runtime_model_config()
        prompt_format = args.prompt_format or runtime_prompt_cfg.prompt_format
        preset_name = args.preset or runtime_prompt_cfg.preset_name
        cfg = load_preset(preset_name)

        campaign_run = execute_campaign_run(
            gamedata=gamedata,
            campaign_id=args.campaign_id,
            character_id=args.character_id,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=args.model_key,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            continue_on_failure=args.continue_on_failure,
        )

        print(f"Campaign: {campaign_run['campaign_id']}")
        print(f"Character: {campaign_run['character_id']}")
        print(f"Model: {campaign_run.get('model') or runtime_model_cfg.model_path}")
        print(f"Continue on failure: {str(args.continue_on_failure).lower()}")
        print("")

        total_scenes = campaign_run.get("total_scenes", len(campaign_run["scene_runs"]))
        for index, scene_run in enumerate(campaign_run["scene_runs"], start=1):
            print(f"[{index}/{total_scenes}] {scene_run['scene_id']}: {scene_run.get('status', 'ERROR')}")

        print("\nSummary:")
        print(f"Passed: {campaign_run.get('passed_scenes', 0)}")
        print(f"Failed: {campaign_run.get('failed_scenes', 0)}")
        print(f"Parse failures: {campaign_run.get('parse_failures', 0)}")
        print(f"Success rate: {campaign_run.get('success_rate', 0.0):.1f}%")
        if campaign_run.get("stop_scene_id"):
            print(f"Stopped at: {campaign_run['stop_scene_id']}")
        elif campaign_run.get("first_failed_scene_id"):
            print(f"First failed scene: {campaign_run['first_failed_scene_id']}")

        if args.save_run:
            ensure_dir(os.path.dirname(args.save_run))
            runlog = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_dir": args.data_dir,
                "campaign_id": args.campaign_id,
                "character_id": args.character_id,
                "preset": preset_name,
                "prompt_format": prompt_format,
                **campaign_run,
            }
            with open(args.save_run, "w", encoding="utf-8") as f:
                json.dump(runlog, f, ensure_ascii=False, indent=2)
            print(f"\nSaved campaign run log to: {args.save_run}")

    except DataValidationError as e:
        print("Data validation error:")
        print(e)
    except Exception as e:
        import traceback

        print("Unexpected error:")
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
