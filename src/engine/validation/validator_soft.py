from src.engine.validation.validator_utils import (
    build_invalid_verdict,
    compute_effective_power,
    get_monster_damage_modifiers,
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

    success_condition = scene.get("success_condition", {}) or {}
    constraints = scene.get("constraints", {}) or {}
    validation_rules = scene.get("validation_rules", {}) or {}
    tool_effects = get_tool_effects(tool)
    interactions = monster.get("interactions", {}) or {}
    effect_tags = set(tool_effects.get("effect_tags", []) or [])
    forbidden_effect_tags = set(validation_rules.get("forbidden_effect_tags", []) or [])
    forbidden_overlap = sorted(forbidden_effect_tags.intersection(effect_tags))

    if forbidden_overlap:
        return build_invalid_verdict(
            f"forbidden_effect_tag: tool uses forbidden effect tag(s) {forbidden_overlap}",
            reason_code="forbidden_effect_tag",
            soft_valid=False,
            outcome="failure",
        )

    if tool_effects.get("escape_attempt") is True:
        if constraints.get("no_escape", False):
            return build_invalid_verdict(
                "escape_not_success: this scene forbids escape",
                reason_code="escape_not_success",
                soft_valid=False,
                outcome="failure",
            )
        if not interactions.get("escape_allowed", False):
            return build_invalid_verdict(
                f"escape_not_success: monster '{scene.get('monster_id')}' cannot be escaped",
                reason_code="escape_not_success",
                soft_valid=False,
                outcome="failure",
            )
        if validation_rules.get("allow_escape_as_success", False):
            return {
                "soft_valid": True,
                "outcome": "success",
                "reason": "Escape attempt succeeded",
            }
        return build_invalid_verdict(
            "escape_not_success: escape is allowed but does not satisfy this scene's success condition",
            reason_code="escape_not_success",
            soft_valid=False,
            outcome="failure",
        )

    success_type = success_condition.get("type")

    if success_type == "solve_encounter":
        required_effect_tags = set(validation_rules.get("required_effect_tags", []) or [])
        missing_required_tags = sorted(required_effect_tags.difference(effect_tags))
        if missing_required_tags:
            return build_invalid_verdict(
                f"missing_required_effect_tag: missing required effect tag(s) {missing_required_tags}",
                reason_code="missing_required_effect_tag",
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
        if tool_effects.get("combat_effect") is not True:
            return build_invalid_verdict(
                "non_combat_tool: selected tool is not a combat effect",
                reason_code="non_combat_tool",
                soft_valid=False,
                outcome="failure",
            )
        if tool_effects.get("damage_type") is None:
            return build_invalid_verdict(
                "missing_damage_type: selected combat tool has no damage_type",
                reason_code="missing_damage_type",
                soft_valid=False,
                outcome="failure",
            )
        if tool_effects.get("base_power") is None:
            return build_invalid_verdict(
                "missing_damage_type: selected combat tool has no base_power",
                reason_code="missing_damage_type",
                soft_valid=False,
                outcome="failure",
            )
        resolved_modifiers = get_monster_damage_modifiers(gamedata, monster)
        if tool_effects["damage_type"] not in resolved_modifiers:
            return build_invalid_verdict(
                f"missing_damage_modifier: monster '{scene.get('monster_id')}' has no modifier for damage type '{tool_effects['damage_type']}'",
                reason_code="missing_damage_modifier",
                soft_valid=False,
                outcome="failure",
            )
        power = compute_effective_power(tool, monster)
        if power is None or power.get("effective_power") is None:
            return build_invalid_verdict(
                "missing_damage_modifier: selected tool cannot resolve effective power for this monster",
                reason_code="missing_damage_modifier",
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
                f"insufficient_effective_power: effective_power={power['effective_power']} "
                f"< min_power_to_defeat={min_power}"
            ),
            reason_code="insufficient_effective_power",
            soft_valid=False,
            outcome="failure",
        )

    return {
        "soft_valid": True,
        "outcome": "success",
        "reason": "No soft validation rule blocked this action",
    }
