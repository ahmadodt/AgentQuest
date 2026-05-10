from typing import List

from src.models.base import ChatMessage, GenerationResult


class LlamaCppHandler:
    def __init__(self, model_path: str):
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is required for the llama_cpp backend. "
                "Install it with `pip install llama-cpp-python`."
            ) from e

        self._model_path = model_path
        self._client = Llama(model_path=model_path, verbose=False)

    def generate(
        self,
        messages: List[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.0,
    ) -> GenerationResult:
        response = self._client.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response["choices"][0]
        message = choice.get("message", {})
        raw_text = (message.get("content") or "").strip()

        metadata = {
            "backend": "llama_cpp",
            "model_path": self._model_path,
            "finish_reason": choice.get("finish_reason"),
            "usage": response.get("usage"),
        }

        return GenerationResult(raw_text=raw_text, metadata=metadata)
