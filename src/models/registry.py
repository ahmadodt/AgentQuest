import os

from src.models.backends.openai_compat import OpenAICompatConfig, OpenAICompatHandler

def build_handler(model_key: str):
    if model_key == "openai_compat":
        base_url = os.environ.get("AQ_BASE_URL", "http://localhost:8080")
        api_key = os.environ.get("AQ_API_KEY", "sk-no-key")
        model = os.environ.get("AQ_MODEL", "llama")
        return OpenAICompatHandler(OpenAICompatConfig(base_url=base_url, api_key=api_key, model=model))

    raise ValueError(f"Unknown model_key: {model_key}")