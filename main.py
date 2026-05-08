from src.engine.loader import load_gamedata, DataValidationError
from src.engine.validator import ToolCallValidator


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

        print("\n--- AST + HARD + SOFT Validation Test Mode ---\n")

        # Choose character + scene
        # characters: "wizard.ember" or "knight.bram"
        character_id = "knight.bram"
        scene_id = "scene.001.goblin_alley"

        print(f"Using character: {character_id}")
        print(f"Using scene: {scene_id}")

        character = gamedata["characters_by_id"][character_id]

        # Optional manual trait testing:
        # character["traits"] = ["low_mana"]
        # character["traits"] = ["silenced"]

        # For now: visible tools = character.tool_ids
        visible_tool_ids = character["tool_ids"]

        print("\nVisible tools:")
        for tid in visible_tool_ids:
            print(f" - {tid}")

        print("\nEnter a tool call JSON (example):")
        print('{"tool_id": "knight.sword_slash", "arguments": {"target": "goblin"}}')
        print()

        raw_input_str = input("Tool call > ")

        validator = ToolCallValidator(
            gamedata=gamedata,
            character_id=character_id,
            scene_id=scene_id,
            visible_tool_ids=visible_tool_ids,
        )

        verdict = validator.validate(raw_input_str)

        if verdict.get("ast_valid") is False:
            print("\n✖ AST validation failed:")
            print(verdict["reason"])
            return

        if verdict.get("hard_valid") is False:
            print("\n✖ Hard validation failed:")
            print(verdict["reason"])
            print(verdict)
            return

        print("\n✔ Hard validation passed!")

        if verdict.get("soft_valid") is False:
            print("\n✖ Soft validation failed:")
            print(verdict["reason"])
            print(verdict)
            return

        print("\n✔ Soft validation passed!")
        print("\nFinal verdict:")
        print(verdict)

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)

    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()