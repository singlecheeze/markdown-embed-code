#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

DIRECTIVE = re.compile(
    r"^\s*<!--\s*embed-code:\s*(.+?)\s*-->\s*$"
)

FENCE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>`{3,}).*$"
)


def is_closing_fence(line: str, fence: str) -> bool:
    stripped = line.strip()

    return (
        len(stripped) >= len(fence)
        and stripped
        and set(stripped) == {"`"}
    )


def embed(markdown: Path) -> tuple[bool, int]:
    markdown = markdown.resolve()

    if not markdown.is_file():
        raise ValueError(
            f"Markdown file not found: {markdown}"
        )

    original = markdown.read_text(encoding="utf-8")
    had_final_newline = original.endswith("\n")
    lines = original.splitlines()

    output: list[str] = []
    embedded = 0
    i = 0

    while i < len(lines):
        match = DIRECTIVE.match(lines[i])

        if not match:
            output.append(lines[i])
            i += 1
            continue

        output.append(lines[i])

        if i + 1 >= len(lines):
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "embed directive has no code block"
            )

        opening = FENCE.match(lines[i + 1])

        if not opening:
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "embed directive must be immediately "
                "followed by a fenced code block"
            )

        output.append(lines[i + 1])

        closing = i + 2

        while closing < len(lines):
            if is_closing_fence(
                lines[closing],
                opening.group("fence"),
            ):
                break

            closing += 1

        if closing == len(lines):
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "code block has no closing fence"
            )

        source = Path(match.group(1))

        if source.is_absolute():
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "embed path must be relative"
            )

        # Source paths are relative to the Markdown file.
        source = (markdown.parent / source).resolve()

        if not source.is_file():
            raise ValueError(
                f"{markdown}:{i + 1}: "
                f"source file not found: {source}"
            )

        source_lines = (
            source.read_text(encoding="utf-8")
            .rstrip("\n")
            .splitlines()
        )

        indent = opening.group("indent")

        output.extend(
            f"{indent}{line}"
            for line in source_lines
        )

        output.append(lines[closing])

        embedded += 1
        i = closing + 1

    updated = "\n".join(output)

    if had_final_newline:
        updated += "\n"

    changed = updated != original

    if changed:
        markdown.write_text(
            updated,
            encoding="utf-8",
        )

    return changed, embedded


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Embed local files into Markdown "
            "fenced code blocks."
        )
    )

    parser.add_argument(
        "markdown",
        type=Path,
        help="Markdown file to update",
    )

    args = parser.parse_args()

    try:
        changed, count = embed(args.markdown)

    except ValueError as exc:
        print(
            f"error: {exc}",
            file=sys.stderr,
        )
        return 1

    status = "updated" if changed else "unchanged"

    print(
        f"{args.markdown}: "
        f"{status} "
        f"({count} embedded block(s))"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())