from src.engine.validator_utils import (
    build_invalid_verdict,
    compute_effective_power,
    get_monster_for_scene_or_error,
    get_scene_or_error,
    get_tool_effects,
    get_tool_or_error,
)


def soft_validate_tool_call(gamedata: dict, scene_id: str, tool_id: str) -> dict:
    """
    Stage 3: Soft validator (scene/monster outcome logic).

    This layer answers "does this action work in this situation?" after AST and
    hard validation already passed.

    Current deterministic rules:
    - Escape attempts fail if the scene forbids escape or the monster cannot be escaped
    - Escape attempts otherwise succeed
    - Knowledge encounters succeed only for tools with knowledge_gain
    - Defeat-monster encounters resolve attack power against monster modifiers
    """
    scene, error = get_scene_or_error(gamedata, scene_id)
    if error:
        return error

    tool, error = get_tool_or_error(gamedata, tool_id, layer="soft")
    if error:
        return error

    monster, error = get_monster_for_scene_or_error(gamedata, scene)
    if error:
        return error

    constraints = scene.get("constraints", {}) or {}
    success_condition = scene.get("success_condition", {}) or {}
    tool_effects = get_tool_effects(tool)
    interactions = monster.get("interactions", {}) or {}

    if tool_effects.get("escape_attempt") is True:
        if constraints.get("no_escape", False):
            return build_invalid_verdict(
                "Escape attempt failed: this scene forbids escape",
                soft_valid=False,
                outcome="failure",
            )
        if not interactions.get("escape_allowed", False):
            return build_invalid_verdict(
                f"Escape attempt failed: monster '{scene.get('monster_id')}' cannot be escaped",
                soft_valid=False,
                outcome="failure",
            )
        return {
            "soft_valid": True,
            "outcome": "success",
            "reason": "Escape attempt succeeded",
        }

    success_type = success_condition.get("type")

    if success_type == "solve_encounter":
        preferred_effects = set(success_condition.get("preferred_effects", []))
        if "knowledge_gain" in preferred_effects:
            if tool_effects.get("knowledge_gain") is True:
                return {
                    "soft_valid": True,
                    "outcome": "success",
                    "reason": "Knowledge tool satisfied the encounter objective",
                }
            return build_invalid_verdict(
                "Encounter requires a knowledge-oriented action",
                soft_valid=False,
                outcome="failure",
            )

        return {
            "soft_valid": True,
            "outcome": "success",
            "reason": "Encounter objective satisfied",
        }

    if success_type == "defeat_monster":
        min_power = interactions.get("min_power_to_defeat")
        power = compute_effective_power(tool, monster)
        if power is None:
            return build_invalid_verdict(
                "Selected tool cannot defeat the monster in this encounter",
                soft_valid=False,
                outcome="failure",
            )

        if power["effective_power"] >= min_power:
            return {
                "soft_valid": True,
                "outcome": "success",
                "reason": (
                    f"Monster defeated: effective_power={power['effective_power']} "
                    f"(base_power={power['base_power']}, modifier={power['modifier']})"
                ),
            }

        return build_invalid_verdict(
            (
                f"Attack was too weak: effective_power={power['effective_power']} "
                f"< min_power_to_defeat={min_power}"
            ),
            soft_valid=False,
            outcome="failure",
        )

    return {
        "soft_valid": True,
        "outcome": "success",
        "reason": "No soft validation rule blocked this action",
    }
