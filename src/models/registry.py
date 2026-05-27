from src.models.base import ModelHandler
from src.models.backends.llama_cpp import LlamaCppHandler
from src.models.catalog import DEFAULT_MODEL_CATALOG_PATH
from src.models.config import DEFAULT_RUN_CONFIG_PATH, load_runtime_model_config


def build_handler(
    model_key: str | None = None,
    *,
    config_path: str = DEFAULT_RUN_CONFIG_PATH,
    model_name_override: str | None = None,
    catalog_path: str = DEFAULT_MODEL_CATALOG_PATH,
) -> ModelHandler:
    runtime_cfg = load_runtime_model_config(
        config_path,
        model_name_override=model_name_override,
        catalog_path=catalog_path,
    )
    backend_name = (model_key or runtime_cfg.backend).strip()

    if backend_name != runtime_cfg.backend:
        raise ValueError(
            f"Requested backend '{backend_name}' does not match configured backend "
            f"'{runtime_cfg.backend}' in {config_path}."
        )

    if backend_name == "llama_cpp":
        return LlamaCppHandler(
            model_name=runtime_cfg.model_name,
            model_display_name=runtime_cfg.model_display_name,
            repo_id=runtime_cfg.repo_id,
            filename=runtime_cfg.filename,
        )

    raise ValueError(f"Unsupported backend '{backend_name}'.")
