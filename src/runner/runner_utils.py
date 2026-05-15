import json
import os
from datetime import datetime
from typing import Any

from src.engine.validator import ToolCallValidator
from src.models.registry import build_handler
from src.prompts.base_prompt import build_messages, build_note_update_messages
from src.prompts.prompt_config import DEFAULT_PROMPT_CONFIG, PromptConfig
from src.prompts.presets import DEFAULT_PRESET_NAME
from src.runtime_paths import get_runs_dir


DEFAULT_CHARACTER_ID = "knight.bram"
DEFAULT_SCENE_ID = "scene.goblin_den.001_outer_watch"
DEFAULT_CAMPAIGN_ID = "campaign.goblin_den_v1"


def load_preset(preset_name: str) -> PromptConfig:
    try:
        from src.prompts import presets  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import src/prompts/presets.py. "
            f"Create it (or use --preset {DEFAULT_PRESET_NAME}). "
            f"Original error: {e}"
        )

    if not hasattr(presets, preset_name):
        available = sorted(
            [
                k
                for k in dir(presets)
                if k.isupper() and isinstance(getattr(presets, k), PromptConfig)
            ]
        )
        raise ValueError(f"Unknown preset '{preset_name}'. Available presets: {available}")

    cfg = getattr(presets, preset_name)
    if not isinstance(cfg, PromptConfig):
        raise TypeError(f"Preset '{preset_name}' exists but is not a PromptConfig.")
    return cfg


def ensure_dir(dirpath: str) -> None:
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def default_run_path(prefix: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return os.path.join(get_runs_dir(), f"{prefix}_{timestamp}.json")


def resolve_character(gamedata: dict, character_id: str) -> dict:
    try:
        return gamedata["characters_by_id"][character_id]
    except KeyError as exc:
        raise KeyError(f"Missing character id: {character_id}") from exc


def resolve_scene(gamedata: dict, scene_id: str) -> dict:
    try:
        return gamedata["scenes_by_id"][scene_id]
    except KeyError as exc:
        raise KeyError(f"Missing scene id: {scene_id}") from exc


def resolve_campaign(gamedata: dict, campaign_id: str) -> dict:
    try:
        return gamedata["campaigns_by_id"][campaign_id]
    except KeyError as exc:
        raise KeyError(f"Missing campaign id: {campaign_id}") from exc


def get_campaign_scene_ids(gamedata: dict, campaign_id: str) -> list[str]:
    campaign = resolve_campaign(gamedata, campaign_id)
    scene_ids = list(campaign.get("scene_ids") or [])
    if not scene_ids:
        raise ValueError(f"Campaign has no scenes: {campaign_id}")
    return scene_ids


def get_visible_tools(gamedata: dict, character_id: str) -> tuple[dict, list[str], list[dict]]:
    character = resolve_character(gamedata, character_id)
    visible_tool_ids = list(character["tool_ids"])
    visible_tools = [gamedata["tools_by_id"][tid] for tid in visible_tool_ids]
    return character, visible_tool_ids, visible_tools


def get_model_label(*, metadata: dict[str, Any] | None, model_path_override: str | None = None) -> str:
    if metadata and metadata.get("model_path"):
        return str(metadata["model_path"])
    if model_path_override:
        return os.path.abspath(model_path_override)
    return ""


def scene_status_from_verdict(verdict: dict[str, Any] | None) -> str:
    if not isinstance(verdict, dict):
        return "ERROR"

    outcome = verdict.get("outcome")
    if outcome == "success":
        return "PASS"
    if verdict.get("ast_valid") is False:
        return "PARSE_ERROR"
    if outcome in {"failure", "invalid"}:
        return "FAIL"
    return "ERROR"


def summarize_scene_results(
    scene_results: list[dict[str, Any]],
    *,
    campaign_id: str,
    character_id: str,
    model: str,
    total_scenes: int | None = None,
) -> dict[str, Any]:
    total_scenes = total_scenes if total_scenes is not None else len(scene_results)
    passed_scenes = sum(1 for item in scene_results if item.get("status") == "PASS")
    parse_failures = sum(1 for item in scene_results if item.get("status") == "PARSE_ERROR")
    failed_scenes = sum(1 for item in scene_results if item.get("status") in {"FAIL", "PARSE_ERROR", "ERROR"})
    success_rate = (passed_scenes / total_scenes * 100.0) if total_scenes else 0.0
    first_failed_scene_id = next(
        (item["scene_id"] for item in scene_results if item.get("status") != "PASS"),
        None,
    )

    return {
        "campaign_id": campaign_id,
        "character_id": character_id,
        "model": model,
        "total_scenes": total_scenes,
        "passed_scenes": passed_scenes,
        "failed_scenes": failed_scenes,
        "parse_failures": parse_failures,
        "success_rate": success_rate,
        "first_failed_scene_id": first_failed_scene_id,
        "ordered_scene_results": scene_results,
    }


def _compact_note_update_for_log(note_update: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_id": note_update.get("scene_id"),
        "character_id": note_update.get("character_id"),
        "old_notes": note_update.get("old_notes", ""),
        "updated_notes": note_update.get("updated_notes", ""),
        "raw_model_output": note_update.get("raw_model_output", ""),
    }


def _compact_attempt_for_log(attempt: dict[str, Any]) -> dict[str, Any]:
    compact_attempt = {
        "scene_id": attempt.get("scene_id"),
        "scene_index": attempt.get("scene_index"),
        "attempt_index": attempt.get("attempt_index"),
        "status": attempt.get("status"),
        "reason": attempt.get("reason", ""),
        "raw_model_output": attempt.get("raw_model_output", ""),
        "parsed_tool_call": attempt.get("parsed_tool_call"),
        "validation": attempt.get("validation"),
        "learning_notes": attempt.get("learning_notes", ""),
        "notes_before_attempt": attempt.get("notes_before_attempt", ""),
        "notes_after_attempt": attempt.get("notes_after_attempt", ""),
    }
    if attempt.get("note_update"):
        compact_attempt["note_update"] = _compact_note_update_for_log(attempt["note_update"])
    return compact_attempt


def compact_scene_run_for_log(scene_run: dict[str, Any]) -> dict[str, Any]:
    compact_scene = {
        "scene_id": scene_run.get("scene_id"),
        "scene_index": scene_run.get("scene_index"),
        "scene_title": scene_run.get("scene_title"),
        "status": scene_run.get("status"),
        "reason": scene_run.get("reason", ""),
        "raw_model_output": scene_run.get("raw_model_output", ""),
        "parsed_tool_call": scene_run.get("parsed_tool_call"),
        "validation": scene_run.get("validation"),
    }

    if scene_run.get("visible_tool_ids"):
        compact_scene["visible_tool_ids"] = scene_run.get("visible_tool_ids", [])
    if "learning_notes" in scene_run:
        compact_scene["learning_notes"] = scene_run.get("learning_notes", "")
    if "attempt_index" in scene_run:
        compact_scene["attempt_index"] = scene_run.get("attempt_index")
    if "attempt_count" in scene_run:
        compact_scene["attempt_count"] = scene_run.get("attempt_count")
    if "retry_count" in scene_run:
        compact_scene["retry_count"] = scene_run.get("retry_count")
    if "notes_before_scene" in scene_run:
        compact_scene["notes_before_scene"] = scene_run.get("notes_before_scene", "")
    if "notes_after_scene" in scene_run:
        compact_scene["notes_after_scene"] = scene_run.get("notes_after_scene", "")
    if "resolved_after_learning" in scene_run:
        compact_scene["resolved_after_learning"] = bool(scene_run.get("resolved_after_learning"))
    if scene_run.get("note_update"):
        compact_scene["note_update"] = _compact_note_update_for_log(scene_run["note_update"])
    if scene_run.get("attempts"):
        compact_scene["attempts"] = [
            _compact_attempt_for_log(attempt)
            for attempt in scene_run.get("attempts", [])
        ]

    return compact_scene


def compact_run_result_for_log(run_result: dict[str, Any]) -> dict[str, Any]:
    if "scene_runs" not in run_result and "scene_id" in run_result:
        return compact_scene_run_for_log(run_result)

    compact_result = {
        key: value
        for key, value in run_result.items()
        if key not in {"scene_runs", "ordered_scene_results", "attempts"}
    }

    scene_runs = [
        compact_scene_run_for_log(scene_run)
        for scene_run in run_result.get("scene_runs", [])
    ]
    if "scene_runs" in run_result:
        compact_result["scene_runs"] = scene_runs
    if "ordered_scene_results" in run_result:
        compact_result["ordered_scene_results"] = list(scene_runs)
    if "attempts" in run_result:
        compact_result["attempts"] = [
            _compact_attempt_for_log(attempt)
            for attempt in run_result.get("attempts", [])
        ]

    return compact_result


def _normalize_learning_notes(notes: str, *, max_chars: int = 4000) -> str:
    normalized = (notes or "").strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


def _extract_updated_notes(raw_output: str, existing_notes: str) -> str:
    raw_output = (raw_output or "").strip()
    if not raw_output:
        return existing_notes

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return _normalize_learning_notes(raw_output)

    if isinstance(parsed, dict) and isinstance(parsed.get("notes"), str):
        return _normalize_learning_notes(parsed["notes"])
    return _normalize_learning_notes(raw_output)


def execute_note_update(
    *,
    gamedata: dict,
    character_id: str,
    scene_id: str,
    existing_notes: str,
    scene_run: dict[str, Any],
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    model_path_override: str | None = None,
    handler=None,
) -> dict[str, Any]:
    character = resolve_character(gamedata, character_id)
    scene = resolve_scene(gamedata, scene_id)
    _, _, visible_tools = get_visible_tools(gamedata, character_id)
    messages = build_note_update_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        prompt_format=prompt_format,
        cfg=cfg,
        scene_run=scene_run,
        existing_notes=existing_notes,
    )
    handler = handler or build_handler(model_key, model_path_override=model_path_override)
    gen = handler.generate(messages, max_tokens=max_tokens, temperature=temperature)
    raw = (gen.raw_text or "").strip()
    updated_notes = _extract_updated_notes(raw, existing_notes)
    return {
        "scene_id": scene_id,
        "character_id": character_id,
        "old_notes": existing_notes,
        "updated_notes": updated_notes,
        "raw_model_output": raw,
        "messages": messages,
        "metadata": gen.metadata or {},
    }


def _finalize_scene_result(
    *,
    scene_result: dict[str, Any],
    scene_attempts: list[dict[str, Any]],
    notes_before_scene: str,
    notes_after_scene: str,
    retries_used: int,
) -> dict[str, Any]:
    final_scene_result = dict(scene_result)
    final_scene_result["attempts"] = list(scene_attempts)
    final_scene_result["attempt_count"] = len(scene_attempts)
    final_scene_result["retry_count"] = retries_used
    final_scene_result["notes_before_scene"] = notes_before_scene
    final_scene_result["notes_after_scene"] = notes_after_scene
    final_scene_result["resolved_after_learning"] = final_scene_result.get("status") == "PASS" and retries_used > 0
    return final_scene_result


def execute_scene_run(
    *,
    gamedata: dict,
    character_id: str,
    scene_id: str,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    campaign_id: str | None = None,
    scene_index: int | None = None,
    model_path_override: str | None = None,
    learning_notes: str = "",
    attempt_index: int = 1,
    handler=None,
) -> dict:
    cfg = cfg or DEFAULT_PROMPT_CONFIG
    character, visible_tool_ids, visible_tools = get_visible_tools(gamedata, character_id)
    scene = resolve_scene(gamedata, scene_id)

    messages = build_messages(
        scene=scene,
        character=character,
        visible_tools=visible_tools,
        gamedata=gamedata,
        prompt_format=prompt_format,
        cfg=cfg,
        learning_notes=learning_notes,
    )

    handler = handler or build_handler(model_key, model_path_override=model_path_override)
    gen = handler.generate(messages, max_tokens=max_tokens, temperature=temperature)
    raw = (gen.raw_text or "").strip()

    validator = ToolCallValidator(
        gamedata=gamedata,
        character_id=character_id,
        scene_id=scene_id,
        visible_tool_ids=visible_tool_ids,
    )
    verdict = validator.validate(raw)
    status = scene_status_from_verdict(verdict)
    parsed_tool_call = verdict.get("parsed_tool_call")
    metadata = gen.metadata or {}
    model_label = get_model_label(metadata=metadata, model_path_override=model_path_override)

    return {
        "campaign_id": campaign_id,
        "scene_id": scene_id,
        "scene_index": scene_index,
        "character_id": character_id,
        "model": model_label,
        "visible_tool_ids": visible_tool_ids,
        "visible_tools": visible_tools,
        "messages": messages,
        "raw_model_output": raw,
        "parsed_tool_call": parsed_tool_call,
        "validation": verdict,
        "status": status,
        "reason": verdict.get("reason", ""),
        "learning_notes": learning_notes,
        "attempt_index": attempt_index,
        "metadata": metadata,
        "verdict": verdict,
        "scene_title": scene.get("title", scene_id),
    }


def execute_learning_scene(
    *,
    gamedata: dict,
    campaign_id: str,
    character_id: str,
    scene_id: str,
    scene_index: int,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    current_notes: str = "",
    per_scene_retry_limit: int = 3,
    total_retry_limit_remaining: int = 20,
    model_path_override: str | None = None,
    handler=None,
) -> dict[str, Any]:
    cfg = cfg or DEFAULT_PROMPT_CONFIG
    scene_attempts: list[dict[str, Any]] = []
    notes = _normalize_learning_notes(current_notes)
    notes_before_scene = notes
    retries_used = 0
    handler = handler or build_handler(model_key, model_path_override=model_path_override)

    for attempt_index in range(1, per_scene_retry_limit + 2):
        notes_before_attempt = notes
        scene_run = execute_scene_run(
            gamedata=gamedata,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_id,
            scene_index=scene_index,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
            model_path_override=model_path_override,
            learning_notes=notes_before_attempt,
            attempt_index=attempt_index,
            handler=handler,
        )
        scene_run["notes_before_attempt"] = notes_before_attempt

        if scene_run["status"] == "PASS":
            scene_run["notes_after_attempt"] = notes_before_attempt
            scene_attempts.append(scene_run)
            final_scene_result = _finalize_scene_result(
                scene_result=scene_run,
                scene_attempts=scene_attempts,
                notes_before_scene=notes_before_scene,
                notes_after_scene=notes_before_attempt,
                retries_used=retries_used,
            )
            return {
                "scene_result": final_scene_result,
                "updated_notes": notes_before_attempt,
                "retries_used": retries_used,
            }

        note_update = execute_note_update(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            existing_notes=notes_before_attempt,
            scene_run=scene_run,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max(max_tokens, 256),
            temperature=temperature,
            model_path_override=model_path_override,
            handler=handler,
        )
        notes = note_update["updated_notes"]
        scene_run["note_update"] = note_update
        scene_run["notes_after_attempt"] = notes
        scene_attempts.append(scene_run)

        if retries_used >= per_scene_retry_limit or retries_used >= total_retry_limit_remaining:
            final_scene_result = _finalize_scene_result(
                scene_result=scene_run,
                scene_attempts=scene_attempts,
                notes_before_scene=notes_before_scene,
                notes_after_scene=notes,
                retries_used=retries_used,
            )
            return {
                "scene_result": final_scene_result,
                "updated_notes": notes,
                "retries_used": retries_used,
            }

        retries_used += 1
        if retries_used > total_retry_limit_remaining:
            break

    final_scene_result = _finalize_scene_result(
        scene_result=scene_attempts[-1],
        scene_attempts=scene_attempts,
        notes_before_scene=notes_before_scene,
        notes_after_scene=notes,
        retries_used=retries_used,
    )
    return {
        "scene_result": final_scene_result,
        "updated_notes": notes,
        "retries_used": retries_used,
    }


def execute_campaign_run(
    *,
    gamedata: dict,
    campaign_id: str,
    character_id: str,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    continue_on_failure: bool = False,
    model_path_override: str | None = None,
    handler=None,
) -> dict:
    campaign = resolve_campaign(gamedata, campaign_id)
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    scene_runs = []
    final_outcome = "success"
    final_reason = "Campaign completed successfully"
    stop_scene_id = None

    handler = handler or build_handler(model_key, model_path_override=model_path_override)

    for scene_index, scene_id in enumerate(scene_ids):
        scene_run = execute_scene_run(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
            campaign_id=campaign_id,
            scene_index=scene_index,
            model_path_override=model_path_override,
            handler=handler,
        )
        scene_runs.append(scene_run)

        verdict = scene_run["verdict"]
        if verdict.get("outcome") != "success":
            final_outcome = verdict.get("outcome", "invalid")
            final_reason = verdict.get("reason", "Campaign stopped")
            stop_scene_id = scene_id
            if not continue_on_failure:
                break

    campaign_summary = summarize_scene_results(
        scene_runs,
        campaign_id=campaign_id,
        character_id=character_id,
        model=scene_runs[-1]["model"] if scene_runs else "",
        total_scenes=len(scene_ids),
    )

    if campaign_summary["failed_scenes"] and continue_on_failure:
        final_outcome = "failure"
        final_reason = "Campaign completed with one or more failed scenes"
        stop_scene_id = None
    elif campaign_summary["failed_scenes"] == 0:
        final_outcome = "success"
        final_reason = "Campaign completed successfully"
        stop_scene_id = None

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name", campaign_id),
        "character_id": character_id,
        "model": campaign_summary["model"],
        "scene_ids": scene_ids,
        "scene_runs": scene_runs,
        "ordered_scene_results": scene_runs,
        "continue_on_failure": continue_on_failure,
        "final_outcome": final_outcome,
        "final_reason": final_reason,
        "stop_scene_id": stop_scene_id,
        "first_failed_scene_id": campaign_summary["first_failed_scene_id"],
        "total_scenes": campaign_summary["total_scenes"],
        "passed_scenes": campaign_summary["passed_scenes"],
        "failed_scenes": campaign_summary["failed_scenes"],
        "parse_failures": campaign_summary["parse_failures"],
        "success_rate": campaign_summary["success_rate"],
    }


def execute_learning_campaign(
    *,
    gamedata: dict,
    campaign_id: str,
    character_id: str,
    prompt_format: str,
    cfg: PromptConfig | None,
    model_key: str,
    max_tokens: int,
    temperature: float,
    per_scene_retry_limit: int = 3,
    total_retry_limit: int = 20,
    initial_notes: str = "",
    model_path_override: str | None = None,
    handler=None,
) -> dict[str, Any]:
    campaign = resolve_campaign(gamedata, campaign_id)
    scene_ids = get_campaign_scene_ids(gamedata, campaign_id)
    handler = handler or build_handler(model_key, model_path_override=model_path_override)
    scene_runs: list[dict[str, Any]] = []
    total_retries_used = 0
    notes = _normalize_learning_notes(initial_notes)

    for scene_index, scene_id in enumerate(scene_ids):
        scene_learning = execute_learning_scene(
            gamedata=gamedata,
            campaign_id=campaign_id,
            character_id=character_id,
            scene_id=scene_id,
            scene_index=scene_index,
            prompt_format=prompt_format,
            cfg=cfg,
            model_key=model_key,
            max_tokens=max_tokens,
            temperature=temperature,
            current_notes=notes,
            per_scene_retry_limit=per_scene_retry_limit,
            total_retry_limit_remaining=max(total_retry_limit - total_retries_used, 0),
            model_path_override=model_path_override,
            handler=handler,
        )
        scene_result = scene_learning["scene_result"]
        scene_runs.append(scene_result)
        notes = scene_learning["updated_notes"]
        total_retries_used += scene_learning["retries_used"]

    campaign_summary = summarize_scene_results(
        scene_runs,
        campaign_id=campaign_id,
        character_id=character_id,
        model=scene_runs[-1]["model"] if scene_runs else "",
        total_scenes=len(scene_ids),
    )
    attempts = [attempt for scene_run in scene_runs for attempt in scene_run.get("attempts", [])]

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.get("name", campaign_id),
        "character_id": character_id,
        "model": campaign_summary["model"],
        "scene_ids": scene_ids,
        "scene_runs": scene_runs,
        "ordered_scene_results": scene_runs,
        "attempts": attempts,
        "self_learning_enabled": True,
        "initial_notes": _normalize_learning_notes(initial_notes),
        "final_notes": notes,
        "per_scene_retry_limit": per_scene_retry_limit,
        "total_retry_limit": total_retry_limit,
        "total_retries_used": total_retries_used,
        "final_outcome": "success" if campaign_summary["failed_scenes"] == 0 else "failure",
        "final_reason": (
            "Learning campaign completed successfully"
            if campaign_summary["failed_scenes"] == 0
            else "Learning campaign completed with one or more failed scenes"
        ),
        "stop_scene_id": None,
        "first_failed_scene_id": campaign_summary["first_failed_scene_id"],
        "total_scenes": campaign_summary["total_scenes"],
        "passed_scenes": campaign_summary["passed_scenes"],
        "failed_scenes": campaign_summary["failed_scenes"],
        "parse_failures": campaign_summary["parse_failures"],
        "success_rate": campaign_summary["success_rate"],
    }
