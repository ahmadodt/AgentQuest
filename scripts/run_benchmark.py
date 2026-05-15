import argparse
import json
import os
import sys
import time
from datetime import datetime

from src.engine.loader import DataValidationError, load_gamedata
from src.engine.validation.report_utils import collect_scene_character_tool_results
from src.models.config import load_runtime_model_config, load_runtime_prompt_config
from src.models.registry import build_handler
from src.runtime_paths import get_data_dir, get_runs_dir
from src.runner.benchmark_utils import aggregate_benchmark_records, build_benchmark_record
from src.runner.runner_utils import ensure_dir, execute_scene_run, get_campaign_scene_ids, load_preset


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
    if presets:
        return presets
    return [runtime_prompt_cfg.preset_name]


def _resolve_prompt_formats(runtime_prompt_cfg, args) -> list[str]:
    prompt_formats = _parse_multi_option(args.prompt_format)
    if prompt_formats:
        return prompt_formats
    return [runtime_prompt_cfg.prompt_format]


def _benchmark_output_dir() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return os.path.join(get_runs_dir(), "benchmarks", timestamp)


def _write_json(path: str, payload: object) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default=get_data_dir())
    parser.add_argument("--campaign-id", type=str, default="")
    parser.add_argument("--all-campaigns", action="store_true")
    parser.add_argument("--character-id", type=str, default="")
    parser.add_argument("--all-characters", action="store_true")
    parser.add_argument("--preset", action="append", default=[])
    parser.add_argument("--prompt-format", action="append", default=[])
    parser.add_argument("--model-key", type=str, default="")
    parser.add_argument("--model-path", type=str, default="")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--output-dir", type=str, default="")
    args = parser.parse_args()

    try:
        gamedata = load_gamedata(args.data_dir)
        runtime_prompt_cfg = load_runtime_prompt_config()
        runtime_model_cfg = load_runtime_model_config(
            model_path_override=args.model_path or None,
        )

        campaign_ids = _resolve_campaign_ids(gamedata, args)
        character_ids = _resolve_character_ids(gamedata, args)
        presets = _resolve_presets(runtime_prompt_cfg, args)
        prompt_formats = _resolve_prompt_formats(runtime_prompt_cfg, args)

        output_dir = os.path.abspath(args.output_dir) if args.output_dir else _benchmark_output_dir()
        ensure_dir(output_dir)

        manifest = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data_dir": os.path.abspath(args.data_dir),
            "campaign_ids": campaign_ids,
            "character_ids": character_ids,
            "presets": presets,
            "prompt_formats": prompt_formats,
            "model": runtime_model_cfg.model_path,
            "backend": runtime_model_cfg.backend,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        }
        _write_json(os.path.join(output_dir, "manifest.json"), manifest)

        records: list[dict] = []
        deterministic_valid_tools: dict[str, list[str]] = {}
        handler = build_handler(
            args.model_key,
            model_path_override=runtime_model_cfg.model_path,
        )

        for campaign_id in campaign_ids:
            scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
            for character_id in character_ids:
                for preset_name in presets:
                    cfg = load_preset(preset_name)
                    for prompt_format in prompt_formats:
                        for scene_index, scene_id in enumerate(scene_ids):
                            valid_tools_key = f"{scene_id}::{character_id}"
                            if valid_tools_key not in deterministic_valid_tools:
                                tool_results = collect_scene_character_tool_results(
                                    gamedata,
                                    scene_id=scene_id,
                                    character_id=character_id,
                                )
                                deterministic_valid_tools[valid_tools_key] = [
                                    item["tool_id"] for item in tool_results["valid_tools"]
                                ]

                            start_time = time.perf_counter()
                            scene_run = execute_scene_run(
                                gamedata=gamedata,
                                campaign_id=campaign_id,
                                character_id=character_id,
                                scene_id=scene_id,
                                scene_index=scene_index,
                                prompt_format=prompt_format,
                                cfg=cfg,
                                model_key=args.model_key,
                                max_tokens=args.max_tokens,
                                temperature=args.temperature,
                                model_path_override=runtime_model_cfg.model_path,
                                handler=handler,
                            )
                            latency_seconds = time.perf_counter() - start_time
                            model_label = scene_run.get("model") or runtime_model_cfg.model_path
                            records.append(
                                build_benchmark_record(
                                    campaign_id=campaign_id,
                                    scene_run=scene_run,
                                    character_id=character_id,
                                    preset=preset_name,
                                    prompt_format=prompt_format,
                                    model=model_label,
                                    valid_tools=deterministic_valid_tools[valid_tools_key],
                                    latency_seconds=latency_seconds,
                                )
                            )

        summary = aggregate_benchmark_records(records)
        _write_json(os.path.join(output_dir, "records.json"), records)
        _write_json(os.path.join(output_dir, "summary.json"), summary)

        print("Benchmark complete")
        print(f"Output: {output_dir}")
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
    sys.exit(main())
