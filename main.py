from src.engine.loader import load_gamedata, DataValidationError


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
        print(f"gamedata {gamedata['tools_by_id']}")
    except DataValidationError as e:
        print("✖ Data validation error:")
        print(e)

    except Exception as e:
        print("✖ Unexpected error:")
        print(e)


if __name__ == "__main__":
    main()