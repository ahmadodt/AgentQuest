from typing import List

from src.models.base import ChatMessage, GenerationResult


class LlamaCppHandler:
    def __init__(
        self,
        *,
        model_name: str,
        model_display_name: str,
        repo_id: str,
        filename: str,
    ):
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is required for the llama_cpp backend. "
                "Install it with `pip install llama-cpp-python`."
            ) from e

        self._model_name = model_name
        self._model_display_name = model_display_name
        self._repo_id = repo_id
        self._filename = filename
        self._client = Llama.from_pretrained(
            repo_id=repo_id,
            filename=filename,
            n_ctx=4096,          # total context window: prompt + output
            n_gpu_layers=-1,     # offload as many layers as possible to GPU
            verbose=False,
        )

    def generate(
        self,
        messages: List[ChatMessage],
        *,
        max_tokens: int = 256,   # output tokens only
        temperature: float = 0.0,
    ) -> GenerationResult:
        response = self._client.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        choice = response["choices"][0]
        message = choice.get("message", {})
        raw_text = (message.get("content") or "").strip()

        metadata = {
            "backend": "llama_cpp",
            "model": self._model_name,
            "model_display_name": self._model_display_name,
            "repo_id": self._repo_id,
            "filename": self._filename,
            "finish_reason": choice.get("finish_reason"),
            "usage": response.get("usage"),
        }

        return GenerationResult(raw_text=raw_text, metadata=metadata)
