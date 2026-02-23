from src.engine.loader import load_gamedata, DataValidationError
from src.engine.validator_ast import ast_validate_tool_call, AstValidationError


def main():
    print("Loading game data...\n")

    try:
        gamedata = load_gamedata("data")

        print("✔ Game data loaded successfully!\n")
        print("Summary:")
        print(f"- Tools: {len(gamedata['tools_by_id'])}")
        print(f"- Characters: {len(gamedata['characters_by_id'])}")
        print(f"- Monsters: {len(gamedata['monsters_by_id'])}")
        print(f"- Scenes: {len(gamedata['scenes_by_id'])}")
        print(f"Game data structure: {list(gamedata.keys())}")

        print("\n--- AST Validation Test Mode ---\n")

        # Select character
        character_id = "wizard.ember"
        scene_id = "scene.001.goblin_alley"

        print(f"Using character: {character_id}")
        print(f"Using scene: {scene_id}")

        character = gamedata["characters_by_id"][character_id]

        # For now: visible tools = character.tool_ids
        visible_tool_ids = character["tool_ids"]

        print("\nVisible tools:")
        for tid in visible_tool_ids:
            print(f" - {tid}")

        print("\nEnter a tool call JSON (example):")
        print('{"tool_id": "wizard.cast_fireball", "arguments": {"target": "goblin"}}')
        print()

        raw_input_str = input("Tool call > ")

        try:
            parsed = ast_validate_tool_call(
                raw_output=raw_input_str,
                tools_by_id=gamedata["tools_by_id"],
                visible_tool_ids=visible_tool_ids,
            )

            print("\n✔ AST validation passed!")
            print(f"Parsed tool call: {parsed}")

        except AstValidationError as e:
            print("\n✖ AST validation failed:")
            print(e)

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)

    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()