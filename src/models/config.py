import json
import os
from dataclasses import dataclass


DEFAULT_RUN_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "configs", "run_config.json")
)


@dataclass(frozen=True)
class RuntimeModelConfig:
    backend: str
    model_path: str


def _resolve_model_path(config_path: str, model_path: str) -> str:
    if os.path.isabs(model_path):
        return model_path
    return os.path.abspath(os.path.join(os.path.dirname(config_path), model_path))


def load_runtime_model_config(config_path: str = DEFAULT_RUN_CONFIG_PATH) -> RuntimeModelConfig:
    resolved_config_path = os.path.abspath(config_path)

    with open(resolved_config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    backend = raw.get("backend")
    if not isinstance(backend, str) or not backend.strip():
        raise ValueError("run_config.json must contain a non-empty string 'backend'.")

    model_value = raw.get("model")
    if not isinstance(model_value, str) or not model_value.strip():
        raise ValueError("run_config.json must contain a non-empty string 'model'.")

    model_path = _resolve_model_path(resolved_config_path, model_value.strip())

    if not model_path.lower().endswith(".gguf"):
        raise ValueError(f"Configured model path must point to a .gguf file: {model_path}")

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Configured GGUF model file does not exist: {model_path}")

    return RuntimeModelConfig(backend=backend.strip(), model_path=model_path)
