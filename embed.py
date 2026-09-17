#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path

DIRECTIVE = re.compile(
    r"^[ ]{0,3}<!--\s*embed-code:\s*(.+?)\s*-->\s*$"
)

FENCE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$"
)

MARKDOWN_SUFFIXES = {".md", ".markdown"}
IGNORED_DIRECTORIES = {".git"}


def is_closing_fence(line: str, fence: str) -> bool:
    stripped = line.strip()

    return (
        len(stripped) >= len(fence)
        and stripped
        and set(stripped) == {fence[0]}
    )


def find_markdown_files(root: Path):
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in IGNORED_DIRECTORIES
        )

        for filename in sorted(filenames):
            path = Path(directory) / filename

            if path.suffix.lower() in MARKDOWN_SUFFIXES:
                yield path


def render(markdown: Path, repository_root: Path) -> tuple[str, int]:
    original = markdown.read_text(encoding="utf-8")

    if "embed-code:" not in original:
        return original, 0

    newline = "\r\n" if "\r\n" in original else "\n"
    had_final_newline = original.endswith(("\n", "\r\n"))
    lines = original.splitlines()

    output: list[str] = []
    embedded = 0
    i = 0
    enclosing_fence: str | None = None

    while i < len(lines):
        line = lines[i]

        if enclosing_fence is not None:
            output.append(line)

            if is_closing_fence(line, enclosing_fence):
                enclosing_fence = None

            i += 1
            continue

        match = DIRECTIVE.match(line)

        if not match:
            output.append(line)

            opening = FENCE.match(line)
            if opening:
                enclosing_fence = opening.group("fence")

            i += 1
            continue

        output.append(line)

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

        source = Path(match.group(1).strip())

        if source.is_absolute():
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "embed path must be relative"
            )

        source = (markdown.parent / source).resolve()

        if not source.is_relative_to(repository_root):
            raise ValueError(
                f"{markdown}:{i + 1}: "
                "embed path must remain inside the repository"
            )

        if not source.is_file():
            raise ValueError(
                f"{markdown}:{i + 1}: "
                f"source file not found: {source}"
            )

        source_lines = (
            source.read_text(encoding="utf-8")
            .rstrip("\r\n")
            .splitlines()
        )

        indent = opening.group("indent")

        output.extend(
            f"{indent}{source_line}"
            for source_line in source_lines
        )

        output.append(lines[closing])

        embedded += 1
        i = closing + 1

    updated = newline.join(output)

    if had_final_newline:
        updated += newline

    return updated, embedded


def set_github_outputs(
    *,
    changed: bool,
    scanned_files: int,
    files_with_embeds: int,
    files_changed: int,
    embedded_blocks: int,
) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")

    if not output_file:
        return

    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(f"changed={'true' if changed else 'false'}\n")
        handle.write(f"scanned_files={scanned_files}\n")
        handle.write(f"files_with_embeds={files_with_embeds}\n")
        handle.write(f"files_changed={files_changed}\n")
        handle.write(f"embedded_blocks={embedded_blocks}\n")


def main() -> int:
    repository_root = Path(
        sys.argv[1] if len(sys.argv) > 1 else "."
    ).resolve()

    if not repository_root.is_dir():
        print(
            f"error: repository root not found: {repository_root}",
            file=sys.stderr,
        )
        return 1

    pending_updates: list[tuple[Path, str, int]] = []
    errors: list[str] = []

    scanned_files = 0
    files_with_embeds = 0
    embedded_blocks = 0

    for markdown in find_markdown_files(repository_root):
        scanned_files += 1

        try:
            original = markdown.read_text(encoding="utf-8")
            updated, count = render(
                markdown,
                repository_root,
            )
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
            continue

        if count == 0:
            continue

        files_with_embeds += 1
        embedded_blocks += count

        if updated != original:
            pending_updates.append(
                (markdown, updated, count)
            )

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)

        print(
            f"Embedding failed with {len(errors)} error(s). "
            "No files were changed.",
            file=sys.stderr,
        )
        return 1

    for markdown, updated, count in pending_updates:
        markdown.write_text(
            updated,
            encoding="utf-8",
        )

        relative = markdown.relative_to(repository_root)

        print(
            f"updated: {relative} "
            f"({count} embedded block(s))"
        )

    files_changed = len(pending_updates)
    changed = files_changed > 0

    set_github_outputs(
        changed=changed,
        scanned_files=scanned_files,
        files_with_embeds=files_with_embeds,
        files_changed=files_changed,
        embedded_blocks=embedded_blocks,
    )

    print()
    print("Markdown embed summary")
    print(f"  Markdown files scanned: {scanned_files}")
    print(f"  Files with embeds:      {files_with_embeds}")
    print(f"  Embedded blocks:        {embedded_blocks}")
    print(f"  Files changed:          {files_changed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
