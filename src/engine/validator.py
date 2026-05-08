from src.engine.validation.validator_ast import AstValidationError, ast_validate_tool_call
from src.engine.validation.validator_hard import hard_validate_tool_call
from src.engine.validation.validator_soft import soft_validate_tool_call


class ToolCallValidator:
    """
    Orchestrates the validation pipeline:
    Stage 1: AST validation (JSON + tool exists + tool visible + args correct)
    Stage 2: Hard validation (character/tool feasibility: permissions + inventory + traits)
    Stage 3: Soft validation (scene/monster outcome logic)
    """
    def __init__(
        self,
        gamedata: dict,
        character_id: str,
        scene_id: str,
        visible_tool_ids: list,
    ) -> None:
        self.gamedata = gamedata
        self.character_id = character_id
        self.scene_id = scene_id
        self.visible_tool_ids = visible_tool_ids
        self.tools_by_id = gamedata["tools_by_id"]

    def validate(self, raw_model_output: str) -> dict:
        try:
            parsed = ast_validate_tool_call(
                raw_output=raw_model_output,
                tools_by_id=self.tools_by_id,
                visible_tool_ids=self.visible_tool_ids,
            )
        except AstValidationError as e:
            return self._build_ast_error_verdict(e)

        hard_verdict = hard_validate_tool_call(
            gamedata=self.gamedata,
            character_id=self.character_id,
            tool_id=parsed["tool_id"],
        )

        if not hard_verdict.get("hard_valid"):
            return self._attach_context(
                hard_verdict,
                ast_valid=True,
                soft_valid=None,
                parsed_tool_call=parsed,
            )

        soft_verdict = soft_validate_tool_call(
            gamedata=self.gamedata,
            scene_id=self.scene_id,
            tool_id=parsed["tool_id"],
        )
        return self._attach_context(
            soft_verdict,
            ast_valid=True,
            hard_valid=True,
            parsed_tool_call=parsed,
        )

    def _build_ast_error_verdict(self, error: Exception) -> dict:
        return {
            "ast_valid": False,
            "hard_valid": None,
            "soft_valid": None,
            "outcome": "invalid",
            "reason": f"AST error: {error}",
            "parsed_tool_call": None,
            "character_id": self.character_id,
            "scene_id": self.scene_id,
        }

    def _attach_context(self, verdict: dict, **extra_fields) -> dict:
        verdict.update(extra_fields)
        verdict["character_id"] = self.character_id
        verdict["scene_id"] = self.scene_id
        return verdict

