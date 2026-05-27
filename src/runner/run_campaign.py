import argparse

from src.engine.loader import DataValidationError, load_gamedata
from src.models.config import load_runtime_model_config
from src.runtime_paths import get_data_dir
from src.runner.runner_utils import (
    DEFAULT_CAMPAIGN_ID,
    DEFAULT_CHARACTER_ID,
    build_run_log_payload,
    default_run_path,
    execute_campaign_run,
    execute_learning_campaign,
    resolve_prompt_settings,
    write_json_file,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default=get_data_dir())
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
        "--self-learning",
        action="store_true",
        help="Enable self-learning retries with note writing after failures.",
    )
    parser.add_argument(
        "--per-scene-retry-limit",
        type=int,
        default=3,
        help="Maximum retries for a single scene in self-learning mode.",
    )
    parser.add_argument(
        "--total-retry-limit",
        type=int,
        default=20,
        help="Maximum retries across the full campaign in self-learning mode.",
    )
    parser.add_argument(
        "--initial-notes",
        type=str,
        default="",
        help="Optional seed notes for self-learning mode.",
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
        runtime_model_cfg = load_runtime_model_config()
        prompt_format, preset_name, cfg = resolve_prompt_settings(
            prompt_format=args.prompt_format,
            preset_name=args.preset,
        )

        if args.self_learning:
            campaign_run = execute_learning_campaign(
                gamedata=gamedata,
                campaign_id=args.campaign_id,
                character_id=args.character_id,
                prompt_format=prompt_format,
                cfg=cfg,
                model_key=args.model_key,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                per_scene_retry_limit=args.per_scene_retry_limit,
                total_retry_limit=args.total_retry_limit,
                initial_notes=args.initial_notes,
            )
        else:
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
        print(f"Model: {campaign_run.get('model') or runtime_model_cfg.model_name}")
        print(f"Continue on failure: {str(args.continue_on_failure).lower()}")
        print(f"Self learning: {str(args.self_learning).lower()}")
        if args.self_learning:
            print(f"Per-scene retry limit: {args.per_scene_retry_limit}")
            print(f"Total retry limit: {args.total_retry_limit}")
        print("")

        total_scenes = campaign_run.get("total_scenes", len(campaign_run["scene_runs"]))
        for index, scene_run in enumerate(campaign_run["scene_runs"], start=1):
            print(f"[{index}/{total_scenes}] {scene_run['scene_id']}: {scene_run.get('status', 'ERROR')}")

        print("\nSummary:")
        print(f"Passed: {campaign_run.get('passed_scenes', 0)}")
        print(f"Failed: {campaign_run.get('failed_scenes', 0)}")
        print(f"Parse failures: {campaign_run.get('parse_failures', 0)}")
        print(f"Success rate: {campaign_run.get('success_rate', 0.0):.1f}%")
        if args.self_learning:
            print(f"Retries used: {campaign_run.get('total_retries_used', 0)}")
        if campaign_run.get("stop_scene_id"):
            print(f"Stopped at: {campaign_run['stop_scene_id']}")
        elif campaign_run.get("first_failed_scene_id"):
            print(f"First failed scene: {campaign_run['first_failed_scene_id']}")
        if args.self_learning:
            print("\nFinal notes:")
            print(campaign_run.get("final_notes", ""))

        if args.save_run:
            runlog = build_run_log_payload(
                run_mode="campaign",
                data_dir=args.data_dir,
                preset_name=preset_name,
                prompt_format=prompt_format,
                character_id=args.character_id,
                campaign_id=args.campaign_id,
                run_result=campaign_run,
            )
            write_json_file(args.save_run, runlog)
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
