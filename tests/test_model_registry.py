import json
import sys
import types

import pytest

from src.models.config import load_runtime_model_config, load_runtime_prompt_config
from src.models.registry import build_handler


def _write_run_config(
    tmp_path,
    *,
    backend="llama_cpp",
    model="model.gguf",
    preset="BATTLE_PLAN",
    prompt_format="json_only",
):
    model_path = tmp_path / model
    model_path.write_text("stub", encoding="utf-8")

    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": backend,
                "model": model_path.name,
                "preset": preset,
                "prompt_format": prompt_format,
            }
        ),
        encoding="utf-8",
    )
    return config_path, model_path


def test_load_runtime_model_config_resolves_relative_model_path(tmp_path):
    config_path, model_path = _write_run_config(tmp_path)

    cfg = load_runtime_model_config(str(config_path))

    assert cfg.backend == "llama_cpp"
    assert cfg.model_path == str(model_path)


def test_load_runtime_model_config_rejects_non_gguf_path(tmp_path):
    bad_model_path = tmp_path / "model.bin"
    bad_model_path.write_text("stub", encoding="utf-8")

    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": bad_model_path.name,
                "preset": "BATTLE_PLAN",
                "prompt_format": "json_only",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"\.gguf"):
        load_runtime_model_config(str(config_path))


def test_load_runtime_model_config_rejects_missing_model_file(tmp_path):
    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "llama_cpp",
                "model": "missing.gguf",
                "preset": "BATTLE_PLAN",
                "prompt_format": "json_only",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_runtime_model_config(str(config_path))


def test_build_handler_uses_llama_cpp_backend(monkeypatch, tmp_path):
    config_path, model_path = _write_run_config(tmp_path)

    class FakeLlama:
        def __init__(self, model_path, n_ctx, n_gpu_layers, verbose):
            self.model_path = model_path
            self.n_ctx = n_ctx
            self.n_gpu_layers = n_gpu_layers
            self.verbose = verbose

        def create_chat_completion(
            self,
            *,
            messages,
            max_tokens,
            temperature,
            response_format,
        ):
            assert messages == [{"role": "user", "content": "hello"}]
            assert max_tokens == 32
            assert temperature == 0.25
            assert response_format == {"type": "json_object"}

            return {
                "choices": [
                    {
                        "message": {"content": '{"tool_id":"common.run","arguments":{}}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=FakeLlama))

    handler = build_handler(config_path=str(config_path))
    result = handler.generate(
        [{"role": "user", "content": "hello"}],
        max_tokens=32,
        temperature=0.25,
    )

    assert handler._client.model_path == str(model_path)
    assert handler._client.n_ctx == 4096
    assert handler._client.n_gpu_layers == -1
    assert handler._client.verbose is False

    assert result.raw_text == '{"tool_id":"common.run","arguments":{}}'
    assert result.metadata["backend"] == "llama_cpp"
    assert result.metadata["model_path"] == str(model_path)
    assert result.metadata["finish_reason"] == "stop"

    
def test_build_handler_rejects_backend_mismatch(tmp_path):
    config_path, _ = _write_run_config(tmp_path)

    with pytest.raises(ValueError, match="does not match configured backend"):
        build_handler("other_backend", config_path=str(config_path))


def test_load_runtime_prompt_config_uses_run_config_fields(tmp_path):
    config_path, _ = _write_run_config(
        tmp_path,
        preset="FULL_INFO",
        prompt_format="json_only",
    )

    cfg = load_runtime_prompt_config(str(config_path))

    assert cfg.preset_name == "FULL_INFO"
    assert cfg.prompt_format == "json_only"


def test_load_runtime_prompt_config_defaults_when_fields_missing(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_text("stub", encoding="utf-8")
    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps({"backend": "llama_cpp", "model": model_path.name}),
        encoding="utf-8",
    )

    cfg = load_runtime_prompt_config(str(config_path))

    assert cfg.preset_name == "BATTLE_PLAN"
    assert cfg.prompt_format == "json_only"
