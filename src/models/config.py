import json
import os
from dataclasses import dataclass

from src.models.catalog import DEFAULT_MODEL_CATALOG_PATH, resolve_model_catalog_entry

DEFAULT_RUNTIME_PRESET_NAME = "BATTLE_PLAN"
DEFAULT_RUNTIME_PROMPT_FORMAT = "json_only"

DEFAULT_RUN_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "configs", "run_config.json")
)


@dataclass(frozen=True)
class RuntimeModelConfig:
    backend: str
    model_name: str
    model_display_name: str
    repo_id: str
    filename: str


@dataclass(frozen=True)
class RuntimePromptConfig:
    preset_name: str
    prompt_format: str


def load_runtime_model_config(
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    *,
    model_name_override: str | None = None,
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> RuntimeModelConfig:
    resolved_config_path = os.path.abspath(config_path)

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    backend = raw.get("backend")
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("run_config.json must contain a non-empty string 'backend'.")

    env_model_name = (os.getenv("AGENTQUEST_MODEL") or "").strip()
    if model_name_override is not None:
        model_name = model_name_override.strip()
    elif env_model_name:
        model_name = env_model_name
    else:
        model_value = raw.get("model")
        if not isinstance(model_value, str) or not model_value.strip():
            raise ValueError("run_config.json must contain a non-empty string 'model'.")
        model_name = model_value.strip()

    entry = resolve_model_catalog_entry(model_name, catalog_path=catalog_path)
    resolved_backend = backend.strip()
    if entry.backend != resolved_backend:
        raise ValueError(
            f"Configured model '{entry.name}' uses backend '{entry.backend}', "
            f"but run_config.json requests '{resolved_backend}'."
        )

    return RuntimeModelConfig(
        backend=resolved_backend,
        model_name=entry.name,
        model_display_name=entry.display_name,
        repo_id=entry.repo_id,
        filename=entry.filename,
    )


def load_runtime_prompt_config(config_path: str = DEFAULT_RUN_CONFIG_PATH) -> RuntimePromptConfig:
    resolved_config_path = os.path.abspath(config_path)

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    preset_name = raw.get("preset", DEFAULT_RUNTIME_PRESET_NAME)
    if not isinstance(preset_name, str) or not preset_name.strip():
        raise ValueError("run_config.json field 'preset' must be a non-empty string when present.")

    prompt_format = raw.get("prompt_format", DEFAULT_RUNTIME_PROMPT_FORMAT)
    if not isinstance(prompt_format, str) or not prompt_format.strip():
        raise ValueError("run_config.json field 'prompt_format' must be a non-empty string when present.")

    return RuntimePromptConfig(
        preset_name=preset_name.strip(),
        prompt_format=prompt_format.strip(),
    )
