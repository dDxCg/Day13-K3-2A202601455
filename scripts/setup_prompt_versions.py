"""One-off script: create day13-chat prompt v1 (baseline/production) and v2 (candidate) in Langfuse."""
from __future__ import annotations

from langfuse import Langfuse

TEMPLATE = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}"
TEMPLATE_V2 = "Feature={{feature}}\nDocs={{docs}}\nQuestion={{message}}\nAnswer in at most 3 sentences."


def main() -> None:
    client = Langfuse()

    v1 = client.create_prompt(
        name="day13-chat",
        prompt=TEMPLATE,
        labels=["baseline", "production"],
        type="text",
        commit_message="v1: baseline template",
    )
    print(f"Created v1: version={v1.version} labels={v1.labels}")

    v2 = client.create_prompt(
        name="day13-chat",
        prompt=TEMPLATE_V2,
        labels=["candidate"],
        type="text",
        commit_message="v2: candidate, capped answer length",
    )
    print(f"Created v2: version={v2.version} labels={v2.labels}")

    client.flush()


if __name__ == "__main__":
    main()
