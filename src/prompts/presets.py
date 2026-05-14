from src.prompts.prompt_config import PromptConfig


# Hard / learning mode:
# The agent sees the scene, monster identity/basic description, and normal tool descriptions.
# It does NOT see exact monster stats or tool effects.
# Useful for narrative-only decisions and later "learn from failure" experiments.
BLIND_ADVENTURER = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=True,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=False,
    include_success_condition=True,
    include_failure_condition=False,
    include_scene_constraints=False,

    # basic = monster name/type/description
    monster_detail_level="basic",

    # normal visible tools: id, description, args/schema
    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)


# Tool-focused mode:
# Monster info stays minimal/basic, but the agent sees full tool information.
# Useful to test whether failures come from not understanding the tools.
TOOL_MANUAL = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=True,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=False,
    include_success_condition=True,
    include_failure_condition=False,
    include_scene_constraints=False,

    monster_detail_level="basic",

    tools_include_label_emoji=True,
    tools_include_constraints=True,
    tools_include_effects=True,
)


# Monster-focused mode:
# The agent sees monster stats such as weaknesses, resistances, immunities,
# and special rules, but tool effects are still not shown explicitly.
# Useful to test if the model can map monster weaknesses to tool descriptions.
SCOUT_REPORT = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=True,
    include_location=True,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=True,
    include_success_condition=True,
    include_failure_condition=True,
    include_scene_constraints=False,

    monster_detail_level="stats",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)


# Main benchmark mode:
# The agent sees monster stats and tool effects.
# This should be the default because the correct answer is mechanically inferable.
BATTLE_PLAN = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=True,
    include_location=True,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=True,
    include_success_condition=True,
    include_failure_condition=True,
    include_scene_constraints=False,

    monster_detail_level="stats",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=True,
)


# Full debug / upper-bound mode:
# The agent sees everything: full monster interactions, exact tool constraints,
# exact tool effects, labels, emojis, and all scene metadata.
FULL_INFO = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=True,
    include_title=True,
    include_location=True,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=True,
    include_success_condition=True,
    include_failure_condition=True,
    include_scene_constraints=True,

    monster_detail_level="full",

    tools_include_label_emoji=True,
    tools_include_constraints=True,
    tools_include_effects=True,
)


PRESETS = {
    "blind_adventurer": BLIND_ADVENTURER,
    "tool_manual": TOOL_MANUAL,
    "scout_report": SCOUT_REPORT,
    "battle_plan": BATTLE_PLAN,
    "full_info": FULL_INFO,
}


DEFAULT_PRESET_NAME = "BATTLE_PLAN"
