import argparse
import json
import os
from datetime import datetime

from src.engine.loader import DataValidationError, load_gamedata
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
    parser.add_argument("--prompt-format", type=str, default="json_only")
    parser.add_argument("--preset", type=str, default="default")
    parser.add_argument(
        "--model-key",
        type=str,
        default="",
        help="Optional backend override. Defaults to the backend in configs/run_config.json.",
    )
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--save-run",
        type=str,
        default=default_run_path("run_campaign"),
        help="Path to save full campaign run log as JSON. Defaults to runs/run_campaign_<timestamp>.json",
    )
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        cfg = load_preset(args.preset)

        campaign_run = execute_campaign_run(
            gamedata=gamedata,
            campaign_id=args.campaign_id,
            character_id=args.character_id,
            prompt_format=args.prompt_format,
            cfg=cfg,
            model_key=args.model_key,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )

        print("\n=== CAMPAIGN RESULT ===")
        print(
            json.dumps(
                {
                    "campaign_id": campaign_run["campaign_id"],
                    "character_id": campaign_run["character_id"],
                    "final_outcome": campaign_run["final_outcome"],
                    "final_reason": campaign_run["final_reason"],
                    "stop_scene_id": campaign_run["stop_scene_id"],
                    "scene_count_completed": len(campaign_run["scene_runs"]),
                },
                indent=2,
                ensure_ascii=False,
            )
        )

        if args.save_run:
            ensure_dir(os.path.dirname(args.save_run))
            runlog = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data_dir": args.data_dir,
                "campaign_id": args.campaign_id,
                "character_id": args.character_id,
                "preset": args.preset,
                "prompt_format": args.prompt_format,
                **campaign_run,
            }
            with open(args.save_run, "w", encoding="utf-8") as f:
                json.dump(runlog, f, ensure_ascii=False, indent=2)
            print(f"\nSaved campaign run log to: {args.save_run}")

    except DataValidationError as e:
        print("âœ– Data validation error:")
        print(e)
    except Exception as e:
        import traceback

        print("âœ– Unexpected error:")
        print(e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
