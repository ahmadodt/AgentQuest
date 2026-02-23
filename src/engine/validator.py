from src.engine.validator_ast import ast_validate_tool_call, AstValidationError
from src.engine.validator_hard import hard_validate_tool_call


def validate(
    gamedata: dict,
    character_id: str,
    scene_id: str,
    visible_tool_ids: list,
    raw_model_output: str,
) -> dict:
    """
    Orchestrates validation pipeline:
    Stage 1: AST validation (JSON + tool exists + tool visible + args correct)
    Stage 2: Hard validation (character/tool feasibility: permissions + inventory + traits)

    Soft validation will be added later.
    """
    tools_by_id = gamedata["tools_by_id"]

    # Stage 1: AST validation
    try:
        parsed = ast_validate_tool_call(
            raw_output=raw_model_output,
            tools_by_id=tools_by_id,
            visible_tool_ids=visible_tool_ids,
        )
    except AstValidationError as e:
        return {
            "ast_valid": False,
            "hard_valid": None,
            "outcome": "invalid",
            "reason": f"AST error: {e}",
            "parsed_tool_call": None,
            "character_id": character_id,
            "scene_id": scene_id,
        }

    # Stage 2: Hard validation
    hard_verdict = hard_validate_tool_call(
        gamedata=gamedata,
        character_id=character_id,
        tool_id=parsed["tool_id"],
    )

    hard_verdict["ast_valid"] = True
    hard_verdict["parsed_tool_call"] = parsed
    hard_verdict["character_id"] = character_id
    hard_verdict["scene_id"] = scene_id
    return hard_verdict