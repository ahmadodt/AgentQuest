import argparse
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.runner.benchmark_history import publish_benchmark_showcase


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish a local benchmark as a committed showcase bundle.")
    parser.add_argument("--benchmark-dir", required=True)
    parser.add_argument("--showcase-id", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--showcase-dir", default="")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    kwargs = {
        "showcase_id": args.showcase_id,
        "title": args.title,
        "description": args.description,
    }
    if args.showcase_dir:
        kwargs["showcase_dir"] = args.showcase_dir
    try:
        destination = publish_benchmark_showcase(args.benchmark_dir, **kwargs)
    except Exception as error:
        print(f"Unable to publish showcase: {error}")
        return 1
    print(f"Published benchmark showcase: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
