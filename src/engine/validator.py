from agentquest.src.engine.validator_ast import ast_validate_tool_call, AstValidationError
from src.engine.validator_hard import hard_validate_tool_call


def validate(gamedata: dict, scene_id: str, raw_model_output: str) -> dict:
    tools_by_id = gamedata["tools_by_id"]

    # Stage 1: AST/shape validation (+ arg key checks)
    try:
        parsed = ast_validate_tool_call(raw_model_output, tools_by_id)
    except AstValidationError as e:
        return {
            "ast_valid": False,
            "hard_valid": None,
            "outcome": "invalid",
            "reason": f"AST error: {e}",
            "parsed_tool_call": None,
        }

    # Stage 2: Hard feasibility checks (character/tool constraints)
    verdict = hard_validate_tool_call(
        gamedata=gamedata,
        scene_id=scene_id,
        tool_id=parsed["tool_id"],
        arguments=parsed["arguments"],
    )
    verdict["ast_valid"] = True
    verdict["parsed_tool_call"] = parsed
    return verdict