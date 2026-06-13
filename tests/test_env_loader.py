import os

import pytest

from src.env_loader import load_local_env


@pytest.fixture(autouse=True)
def restore_environment_after_test():
    original_environment = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_environment)


def test_load_local_env_sets_missing_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# local secrets",
                "HF_TOKEN=hf_example",
                "export AGENTQUEST_MODEL=qwen3_4b_q4_k_m",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("AGENTQUEST_MODEL", raising=False)

    loaded = load_local_env(str(env_path))

    assert os.environ["HF_TOKEN"] == "hf_example"
    assert os.environ["AGENTQUEST_MODEL"] == "qwen3_4b_q4_k_m"
    assert loaded == {
        "HF_TOKEN": "hf_example",
        "AGENTQUEST_MODEL": "qwen3_4b_q4_k_m",
    }


def test_load_local_env_does_not_override_existing_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("HF_TOKEN=from_file\n", encoding="utf-8")
    monkeypatch.setenv("HF_TOKEN", "from_shell")

    loaded = load_local_env(str(env_path))

    assert os.environ["HF_TOKEN"] == "from_shell"
    assert loaded == {}


def test_load_local_env_handles_quoted_values(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        'HF_TOKEN="hf quoted token"\nAGENTQUEST_RUNS_DIR=\'custom runs\'\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("AGENTQUEST_RUNS_DIR", raising=False)

    loaded = load_local_env(str(env_path))

    assert loaded["HF_TOKEN"] == "hf quoted token"
    assert loaded["AGENTQUEST_RUNS_DIR"] == "custom runs"


def test_load_local_env_missing_file_is_noop(tmp_path):
    missing_path = tmp_path / ".env"

    assert load_local_env(str(missing_path)) == {}
