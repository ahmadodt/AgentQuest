import json
import sys
import types

import pytest

from src.models.config import load_runtime_model_config, load_runtime_prompt_config
from src.models.registry import build_handler


def _write_model_catalog(tmp_path):
    catalog_path = tmp_path / "model_catalog.json"
    catalog_path.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "name": "test_model",
                        "display_name": "Test Model",
                        "backend": "llama_cpp",
                        "repo_id": "org/test-model-gguf",
                        "filename": "test-model-q4.gguf",
                    },
                    {
                        "name": "other_backend_model",
                        "display_name": "Other Backend Model",
                        "backend": "other_backend",
                        "repo_id": "org/other-model",
                        "filename": "other-model.gguf",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return catalog_path


def _write_run_config(
    tmp_path,
    *,
    backend="llama_cpp",
    model="test_model",
    preset="BATTLE_PLAN",
    prompt_format="json_only",
):
    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": backend,
                "model": model,
                "preset": preset,
                "prompt_format": prompt_format,
            }
        ),
        encoding="utf-8",
    )
    return config_path


def test_load_runtime_model_config_resolves_catalog_entry(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path)

    cfg = load_runtime_model_config(str(config_path), catalog_path=str(catalog_path))

    assert cfg.backend == "llama_cpp"
    assert cfg.model_name == "test_model"
    assert cfg.model_display_name == "Test Model"
    assert cfg.repo_id == "org/test-model-gguf"
    assert cfg.filename == "test-model-q4.gguf"


def test_load_runtime_model_config_rejects_unknown_model_name(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path, model="missing_model")

    with pytest.raises(ValueError, match="Unknown model"):
        load_runtime_model_config(str(config_path), catalog_path=str(catalog_path))


def test_load_runtime_model_config_rejects_backend_mismatch(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path, backend="llama_cpp", model="other_backend_model")

    with pytest.raises(ValueError, match="uses backend"):
        load_runtime_model_config(str(config_path), catalog_path=str(catalog_path))


def test_load_runtime_model_config_uses_agentquest_model_env(monkeypatch, tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path, model="other_backend_model")
    monkeypatch.setenv("AGENTQUEST_MODEL", "test_model")

    cfg = load_runtime_model_config(str(config_path), catalog_path=str(catalog_path))

    assert cfg.backend == "llama_cpp"
    assert cfg.model_name == "test_model"


def test_build_handler_uses_llama_cpp_backend(monkeypatch, tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path)

    class FakeLlama:
        @classmethod
        def from_pretrained(cls, *, repo_id, filename, n_ctx, n_gpu_layers, verbose):
            instance = cls()
            instance.repo_id = repo_id
            instance.filename = filename
            instance.n_ctx = n_ctx
            instance.n_gpu_layers = n_gpu_layers
            instance.verbose = verbose
            instance.closed = False
            return instance

        def close(self):
            self.closed = True

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

    handler = build_handler(config_path=str(config_path), catalog_path=str(catalog_path))
    result = handler.generate(
        [{"role": "user", "content": "hello"}],
        max_tokens=32,
        temperature=0.25,
    )

    assert handler._client.repo_id == "org/test-model-gguf"
    assert handler._client.filename == "test-model-q4.gguf"
    assert handler._client.n_ctx == 4096
    assert handler._client.n_gpu_layers == -1
    assert handler._client.verbose is False
    assert result.raw_text == '{"tool_id":"common.run","arguments":{}}'
    assert result.metadata["backend"] == "llama_cpp"
    assert result.metadata["model"] == "test_model"
    assert result.metadata["repo_id"] == "org/test-model-gguf"
    assert result.metadata["filename"] == "test-model-q4.gguf"
    assert result.metadata["finish_reason"] == "stop"

    handler.close()

    assert handler._client.closed is True


def test_build_handler_rejects_backend_mismatch(tmp_path):
    catalog_path = _write_model_catalog(tmp_path)
    config_path = _write_run_config(tmp_path)

    with pytest.raises(ValueError, match="does not match configured backend"):
        build_handler("other_backend", config_path=str(config_path), catalog_path=str(catalog_path))


def test_load_runtime_prompt_config_uses_run_config_fields(tmp_path):
    config_path = _write_run_config(
        tmp_path,
        preset="FULL_INFO",
        prompt_format="json_only",
    )

    cfg = load_runtime_prompt_config(str(config_path))

    assert cfg.preset_name == "FULL_INFO"
    assert cfg.prompt_format == "json_only"


def test_load_runtime_prompt_config_defaults_when_fields_missing(tmp_path):
    config_path = tmp_path / "run_config.json"
    config_path.write_text(
        json.dumps({"backend": "llama_cpp", "model": "test_model"}),
        encoding="utf-8",
    )

    cfg = load_runtime_prompt_config(str(config_path))

    assert cfg.preset_name == "BATTLE_PLAN"
    assert cfg.prompt_format == "json_only"
