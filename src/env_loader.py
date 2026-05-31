import os


def get_default_env_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))


def load_local_env(env_path: str | None = None) -> dict[str, str]:
    resolved_env_path = os.path.abspath(env_path or get_default_env_path())
    loaded: dict[str, str] = {}

    if not os.path.exists(resolved_env_path):
        return loaded

    with open(resolved_env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            parsed = _parse_env_line(raw_line)
            if parsed is None:
                continue

            key, value = parsed
            if key in os.environ:
                continue

            os.environ[key] = value
            loaded[key] = value

    return loaded


def _parse_env_line(raw_line: str) -> tuple[str, str] | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None

    if line.startswith("export "):
        line = line[len("export "):].strip()

    if "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    if not key or any(char.isspace() for char in key):
        return None

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]

    return key, value
