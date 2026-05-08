import copy
import json
import os

import pytest

from src.engine.loader import load_gamedata
from src.engine.validator import ToolCallValidator


def project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def data_dir() -> str:
    return os.path.join(project_root(), "data")


def _make_tool_call(tool_id: str, arguments: dict | None = None) -> str:
    return json.dumps(
        {
            "tool_id": tool_id,
            "arguments": arguments if arguments is not None else {},
        },
        ensure_ascii=False,
    )


@pytest.fixture()
def gamedata():
    return load_gamedata(data_dir())


@pytest.fixture()
def gamedata_copy(gamedata):
    return copy.deepcopy(gamedata)


@pytest.fixture()
def make_tool_call():
    return _make_tool_call


@pytest.fixture()
def validator_factory():
    def _build(
        gamedata: dict,
        character_id: str,
        scene_id: str,
        visible_tool_ids: list | None = None,
    ) -> ToolCallValidator:
        character = gamedata["characters_by_id"][character_id]
        return ToolCallValidator(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            visible_tool_ids=visible_tool_ids
            if visible_tool_ids is not None
            else character["tool_ids"],
        )

    return _build