from src.prompts.prompt_config import PromptConfig

# Baseline: minimal narrative + tool schemas (inventory/traits included; as-is)
PRESET_BASELINE_MINIMAL = PromptConfig(
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
PRESET_PLUS_MONSTER_BASIC = PromptConfig(
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
PRESET_PLUS_MONSTER_STATS = PromptConfig(
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
PRESET_PLUS_MONSTER_INTERACTIONS = PromptConfig(
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
PRESET_PLUS_TOOL_CONSTRAINTS = PromptConfig(
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
PRESET_PLUS_TOOL_EFFECTS = PromptConfig(
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
PRESET_OVERLOAD_ALL = PromptConfig(
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
    "PRESET_BASELINE_MINIMAL": PRESET_BASELINE_MINIMAL,
    "PRESET_PLUS_MONSTER_BASIC": PRESET_PLUS_MONSTER_BASIC,
    "PRESET_PLUS_MONSTER_STATS": PRESET_PLUS_MONSTER_STATS,
    "PRESET_PLUS_MONSTER_INTERACTIONS": PRESET_PLUS_MONSTER_INTERACTIONS,
    "PRESET_PLUS_TOOL_CONSTRAINTS": PRESET_PLUS_TOOL_CONSTRAINTS,
    "PRESET_PLUS_TOOL_EFFECTS": PRESET_PLUS_TOOL_EFFECTS,
    "PRESET_OVERLOAD_ALL": PRESET_OVERLOAD_ALL,
}

DEFAULT_PRESET_NAME = "PRESET_BASELINE_MINIMAL"