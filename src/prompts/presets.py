from src.prompts.prompt_config import PromptConfig

# Baseline: minimal narrative + tool schemas (inventory/traits included; as-is)
MINIMAL = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=False,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=False,
    include_success_condition=True,
    include_failure_condition=False,

    monster_detail_level="none",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)

# Baseline + monster basic (name/type/description)
MONSTER_BASIC = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=True,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=True,
    include_success_condition=True,
    include_failure_condition=False,

    monster_detail_level="basic",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)

# Baseline + monster stats (tags/weaknesses/resistances/immunities/special_rules/escape_allowed)
MONSTER_STATS = PromptConfig(
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

    monster_detail_level="stats",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)

# Baseline + monster interactions (everything in interactions beyond escape_allowed)
# (This is what "full" really means in your monster schema.)
MONSTER_FULL = PromptConfig(
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

    monster_detail_level="full",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=False,
)

# Baseline + tool constraints revealed
TOOL_CONSTRAINTS = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=False,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=False,
    include_success_condition=True,
    include_failure_condition=False,

    monster_detail_level="none",

    tools_include_label_emoji=False,
    tools_include_constraints=True,
    tools_include_effects=False,
)

# Baseline + tool effects revealed
TOOL_EFFECTS = PromptConfig(
    include_inventory=True,
    include_traits=True,

    include_scene_id=False,
    include_title=False,
    include_location=False,
    include_narrative=True,
    include_monster_id=True,
    include_knowledge_level=False,
    include_success_condition=True,
    include_failure_condition=False,

    monster_detail_level="none",

    tools_include_label_emoji=False,
    tools_include_constraints=False,
    tools_include_effects=True,
)

# Overload: everything (scene meta + monster interactions + tool constraints + effects + label/emoji)
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

    monster_detail_level="full",

    tools_include_label_emoji=True,
    tools_include_constraints=True,
    tools_include_effects=True,
)

PRESETS = {
    "minimal": MINIMAL,
    "monster_basic": MONSTER_BASIC,
    "monster_stats": MONSTER_STATS,
    "monster_full": MONSTER_FULL,
    "tool_constraints": TOOL_CONSTRAINTS,
    "tool_effects": TOOL_EFFECTS,
    "full_info": FULL_INFO,
}

DEFAULT_PRESET_NAME = "minimal"