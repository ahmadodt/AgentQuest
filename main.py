from src.engine.loader import load_gamedata, DataValidationError
from src.engine.validator_ast import ast_validate_tool_call, AstValidationError
from src.engine.validator_hard import hard_validate_tool_call


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

        print("\n--- AST + HARD Validation Test Mode ---\n")

        # Choose character + scene (scene is not used by hard validator yet)
        # characters "wizard.ember" or "knight.bram"
        character_id = "knight.bram" 
        scene_id = "scene.001.goblin_alley"

        print(f"Using character: {character_id}")
        print(f"Using scene: {scene_id}")

        character = gamedata["characters_by_id"][character_id]
        #character["traits"] =  ["low_mana"] 

        # For now: visible tools = character.tool_ids
        visible_tool_ids = character["tool_ids"]

        print("\nVisible tools:")
        for tid in visible_tool_ids:
            print(f" - {tid}")

        print("\nEnter a tool call JSON (example):")
        print('{"tool_id": "wizard.cast_fireball", "arguments": {"target": "goblin"}}')
        print()

        raw_input_str = input("Tool call > ")

        # ---- Stage 1: AST validation ----
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
            return

        # ---- Stage 2: Hard validation ----
        verdict = hard_validate_tool_call(
            gamedata=gamedata,
            character_id=character_id,
            tool_id=parsed["tool_id"],
        )

        if verdict.get("hard_valid"):
            print("\n✔ Hard validation passed!")
        else:
            print("\n✖ Hard validation failed:")

        print(verdict)

    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)

    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()