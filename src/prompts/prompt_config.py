from dataclasses import dataclass


@dataclass(frozen=True)
class PromptConfig:
    # Character
    include_inventory: bool = True
    include_traits: bool = True

    # Scene
    include_scene_id: bool = True
    include_title: bool = True
    include_location: bool = True
    include_narrative: bool = True
    include_monster_id: bool = True
    include_knowledge_level: bool = True
    include_success_condition: bool = True
    include_failure_condition: bool = True
    include_scene_constraints: bool = False
    include_validation_rules: bool = False

    # Monster detail: none | basic | stats | full
    monster_detail_level: str = "none"  # start conservative

    # Tools
    tools_include_label_emoji: bool = False
    tools_include_constraints: bool = False
    tools_include_effects: bool = False


DEFAULT_PROMPT_CONFIG = PromptConfig()
