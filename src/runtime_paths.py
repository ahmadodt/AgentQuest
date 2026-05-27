import os


_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_DEFAULT_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
_DEFAULT_LOCAL_MODELS_DIR = os.path.join(_PROJECT_ROOT, "local_models")
_DEFAULT_RUNS_DIR = os.path.join(_PROJECT_ROOT, "runs")


def _resolve_env_path(env_name: str, default_path: str) -> str:
    env_value = (os.getenv(env_name) or "").strip()
    if env_value:
        return os.path.abspath(env_value)
    return os.path.abspath(default_path)


def get_data_dir() -> str:
    return _resolve_env_path("AGENTQUEST_DATA_DIR", _DEFAULT_DATA_DIR)


def get_local_models_dir() -> str:
    return _resolve_env_path("AGENTQUEST_MODELS_DIR", _DEFAULT_LOCAL_MODELS_DIR)


def get_runs_dir() -> str:
    return _resolve_env_path("AGENTQUEST_RUNS_DIR", _DEFAULT_RUNS_DIR)
