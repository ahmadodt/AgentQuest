from src.prompts.prompt_config import PromptConfig

PROMPT_MINIMAL = PromptConfig(
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

PROMPT_WITH_MONSTER_STATS = PromptConfig(
    monster_detail_level="stats",
    tools_include_constraints=False,
    tools_include_effects=False,
)