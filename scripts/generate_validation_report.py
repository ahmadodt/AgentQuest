import argparse
import sys

from src.engine.loader import load_gamedata
from src.engine.validation.report_utils import collect_scene_character_tool_results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    args = parser.parse_args()

    gamedata = load_gamedata(args.data_dir)
    scenes_by_id = gamedata["scenes_by_id"]
    characters_by_id = gamedata["characters_by_id"]

    failures = []
    total_pairs = 0
    solved_pairs = 0

    for scene_id, scene in scenes_by_id.items():
        print(f"\nScene: {scene_id} ({scene.get('title', scene_id)})")
        for character_id, character in characters_by_id.items():
            total_pairs += 1
            tool_results = collect_scene_character_tool_results(
                gamedata,
                scene_id=scene_id,
                character_id=character_id,
            )
            valid_tools = tool_results["valid_tools"]
            invalid_tools = tool_results["invalid_tools"]

            if valid_tools:
                solved_pairs += 1
                print(f"  {character_id}: OK ({len(valid_tools)} valid / {len(invalid_tools)} invalid)")
            else:
                failures.append(
                    {
                        "scene_id": scene_id,
                        "character_id": character_id,
                        "invalid_tools": invalid_tools,
                    }
                )
                print(f"  {character_id}: FAIL (0 valid / {len(invalid_tools)} invalid)")

            if valid_tools:
                valid_ids = ", ".join(item["tool_id"] for item in valid_tools)
                print(f"    valid: {valid_ids}")
            if invalid_tools:
                for item in invalid_tools:
                    print(
                        f"    invalid: {item['tool_id']} -> "
                        f"{item.get('reason_code') or 'unknown_reason'} | {item['reason']}"
                    )

    print("\nSummary:")
    print(f"  scene-character pairs: {total_pairs}")
    print(f"  solvable pairs: {solved_pairs}")
    print(f"  unsolved pairs: {len(failures)}")

    if failures:
        print("\nUnsolved scene-character pairs:")
        for item in failures:
            print(f"  {item['scene_id']} :: {item['character_id']}")
        return 1

    print("\nEvery scene is solvable by every character.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
