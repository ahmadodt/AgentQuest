import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.engine.loader import DataValidationError, load_gamedata
from src.env_loader import load_local_env
from src.models.config import load_runtime_model_config, load_runtime_prompt_config
from src.runtime_paths import get_data_dir
from src.runner.benchmark_service import run_benchmark, spec_from_runtime_config


def _parse_multi_option(values: list[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        for part in value.split(","):
            normalized = part.strip()
            if normalized:
                items.append(normalized)
    return items


def _resolve_campaign_ids(gamedata: dict, args) -> list[str]:
    if args.all_campaigns:
        return sorted(gamedata["campaigns_by_id"].keys())
    if args.campaign_id:
        return [args.campaign_id]
    raise ValueError("Provide --campaign-id or --all-campaigns.")


def _resolve_character_ids(gamedata: dict, args) -> list[str]:
    if args.all_characters:
        return sorted(gamedata["characters_by_id"].keys())
    if args.character_id:
        return [args.character_id]
    raise ValueError("Provide --character-id or --all-characters.")


def _resolve_presets(runtime_prompt_cfg, args) -> list[str]:
    presets = _parse_multi_option(args.preset)
    return presets or [runtime_prompt_cfg.preset_name]


def _resolve_prompt_formats(runtime_prompt_cfg, args) -> list[str]:
    prompt_formats = _parse_multi_option(args.prompt_format)
    return prompt_formats or [runtime_prompt_cfg.prompt_format]


def _resolve_model_names(runtime_model_cfg, args) -> list[str]:
    models = _parse_multi_option(args.model)
    return models or [runtime_model_cfg.model_name]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default=get_data_dir())
    parser.add_argument("--campaign-id", type=str, default="")
    parser.add_argument("--all-campaigns", action="store_true")
    parser.add_argument("--character-id", type=str, default="")
    parser.add_argument("--all-characters", action="store_true")
    parser.add_argument("--preset", action="append", default=[])
    parser.add_argument("--prompt-format", action="append", default=[])
    parser.add_argument("--model", action="append", default=[], help="Catalog model name. Repeat or comma-separate for a model matrix.")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--self-learning", action="store_true")
    parser.add_argument("--per-scene-retry-limit", type=int, default=3)
    parser.add_argument("--total-retry-limit", type=int, default=20)
    parser.add_argument("--initial-notes", type=str, default="")
    parser.add_argument("--output-dir", type=str, default="")
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        runtime_prompt_cfg = load_runtime_prompt_config()
        runtime_model_cfg = load_runtime_model_config()

        spec = spec_from_runtime_config(
            data_dir=args.data_dir,
            campaign_ids=_resolve_campaign_ids(gamedata, args),
            character_ids=_resolve_character_ids(gamedata, args),
            preset_names=_resolve_presets(runtime_prompt_cfg, args),
            prompt_formats=_resolve_prompt_formats(runtime_prompt_cfg, args),
            runtime_model_cfg=runtime_model_cfg,
            model_names=_resolve_model_names(runtime_model_cfg, args),
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            self_learning_enabled=args.self_learning,
            per_scene_retry_limit=args.per_scene_retry_limit,
            total_retry_limit=args.total_retry_limit,
            initial_notes=args.initial_notes,
            output_dir=args.output_dir,
        )
        result = run_benchmark(gamedata=gamedata, spec=spec)
        summary = result["summary"]

        print("Benchmark complete")
        print(f"Output: {result['output_dir']}")
        if result.get("latest_dir"):
            print(f"Latest: {result['latest_dir']}")
        print(f"Dataset: {summary['dataset_id']}")
        print(f"Total scenes: {summary['total_scenes']}")
        print(f"Passed: {summary['passed_scenes']}")
        print(f"Failed: {summary['failed_scenes']}")
        print(f"Parse failures: {summary['parse_failures']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        if summary["first_failed_scene"]:
            print(
                "First failed scene: "
                f"{summary['first_failed_scene']['campaign_id']} / "
                f"{summary['first_failed_scene']['scene_id']} / "
                f"{summary['first_failed_scene']['character_id']} / "
                f"{summary['first_failed_scene']['preset']}"
            )
        else:
            print("First failed scene: none")

        return 0

    except DataValidationError as error:
        print("Data validation error:")
        print(error)
        return 1
    except Exception as error:
        import traceback

        print("Unexpected error:")
        print(error)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    load_local_env()
    sys.exit(main())
