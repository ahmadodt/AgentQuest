import json
import os
from dataclasses import dataclass

from src.runtime_paths import get_local_models_dir

DEFAULT_RUNTIME_PRESET_NAME = "BATTLE_PLAN"
DEFAULT_RUNTIME_PROMPT_FORMAT = "json_only"

DEFAULT_RUN_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "configs", "run_config.json")
)


@dataclass(frozen=True)
class RuntimeModelConfig:
    backend: str
    model_path: str


@dataclass(frozen=True)
class RuntimePromptConfig:
    preset_name: str
    prompt_format: str


def _resolve_model_path(config_path: str, model_path: str) -> str:
    if os.path.isabs(model_path):
        return model_path
    return os.path.abspath(os.path.join(os.path.dirname(config_path), model_path))


def load_runtime_model_config(
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    *,
    model_path_override: str | None = None,
) -> RuntimeModelConfig:
    resolved_config_path = os.path.abspath(config_path)

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    backend = raw.get("backend")
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("run_config.json must contain a non-empty string 'backend'.")

    env_model_path = (os.getenv("AGENTQUEST_MODEL_PATH") or "").strip()

    if model_path_override is not None:
        model_path = os.path.abspath(model_path_override)
    elif env_model_path:
        model_path = os.path.abspath(env_model_path)
    else:
        model_value = raw.get("model")
        if not isinstance(model_value, str) or not model_value.strip():
            raise ValueError("run_config.json must contain a non-empty string 'model'.")
        if model_value.strip().startswith("../local_models/"):
            model_path = os.path.abspath(
                os.path.join(get_local_models_dir(), os.path.basename(model_value.strip()))
            )
        else:
            model_path = _resolve_model_path(resolved_config_path, model_value.strip())

    if not model_path.lower().endswith(".gguf"):
        raise ValueError(f"Configured model path must point to a .gguf file: {model_path}")

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Configured GGUF model file does not exist: {model_path}")

    return RuntimeModelConfig(backend=backend.strip(), model_path=model_path)


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
