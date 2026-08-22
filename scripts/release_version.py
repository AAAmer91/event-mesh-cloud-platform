"""Calculate release versions from conventional commits."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

_CONVENTIONAL_COMMIT = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]+\))?(?P<breaking>!)?:")


def determine_bump(messages: list[str]) -> str | None:
    bump: str | None = None
    for message in messages:
        first_line = message.splitlines()[0] if message else ""
        match = _CONVENTIONAL_COMMIT.match(first_line)
        if "BREAKING CHANGE:" in message or (match and match.group("breaking")):
            return "major"
        if match and match.group("type") == "feat":
            bump = "minor"
        elif match and match.group("type") in {"fix", "perf", "refactor"} and bump is None:
            bump = "patch"
    return bump


def next_version(current: str | None, bump: str) -> str:
    major, minor, patch = (0, 0, 0)
    if current:
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", current.strip())
        if not match:
            raise ValueError(f"Invalid semantic version: {current}")
        major, minor, patch = (int(value) for value in match.groups())
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    elif bump == "patch":
        patch += 1
    else:
        raise ValueError(f"Unsupported release bump: {bump}")
    return f"v{major}.{minor}.{patch}"


def _git_output(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate the next conventional release")
    parser.add_argument("--github-output", type=Path)
    arguments = parser.parse_args()
    latest_tag = _git_output("describe", "--tags", "--abbrev=0") or None
    revision_range = f"{latest_tag}..HEAD" if latest_tag else "HEAD"
    log_output = _git_output("log", revision_range, "--format=%B%x1e")
    commit_messages = [message.strip() for message in log_output.split("\x1e") if message.strip()]
    release_bump = determine_bump(commit_messages)
    release_tag = next_version(latest_tag, release_bump) if release_bump else ""
    result = f"should_release={'true' if release_bump else 'false'}\ntag={release_tag}\nbump={release_bump or ''}\n"
    if arguments.github_output:
        with arguments.github_output.open("a", encoding="utf-8") as handle:
            handle.write(result)
    print(result, end="")
