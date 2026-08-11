"""One-off script: move the 'production' label between day13-chat prompt versions."""
from __future__ import annotations

import argparse

from langfuse import Langfuse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--labels", nargs="+", required=True)
    args = parser.parse_args()

    client = Langfuse()
    result = client.update_prompt(name="day13-chat", version=args.version, new_labels=args.labels)
    print(f"Updated version={args.version} labels={result.labels}")


if __name__ == "__main__":
    main()
