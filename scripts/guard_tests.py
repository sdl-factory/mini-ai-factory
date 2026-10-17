#!/usr/bin/env python3
"""Verification-plane guard: detects changes that weaken verification.

Coding agents are rewarded for making checks pass, and sometimes they "pass" by weakening
the checks instead of fixing the code: deleting a failing test, adding a skip marker,
removing assertions, or lowering the coverage threshold. This guard compares a branch
with its base and fails the build when it sees those patterns.

Usage:
    python scripts/guard_tests.py --base origin/main

Protected paths may only change with explicit human approval. In CI that approval is the
pull request label "approved-protected-change", passed in as ALLOW_PROTECTED_CHANGES=true.
The label is only a speed bump: the real control is CODEOWNERS review of those paths.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field

PROTECTED_PREFIXES = (
    "tests/acceptance/",
    ".github/",
    ".claude/",
    "scripts/guard_tests.py",
    "AGENTS.md",
    "CLAUDE.md",
)
SKIP_PATTERN = re.compile(
    r"pytest\.mark\.(skip|skipif|xfail)\b|pytest\.(skip|xfail|importorskip)\(|unittest\.skip"
)


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


GIT = shutil.which("git") or "git"


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    # Arguments are passed as a list (never through a shell) to a resolved git binary, and
    # come from this script or from git's own output, so S603 does not apply here.
    return subprocess.run([GIT, *args], capture_output=True, text=True)  # noqa: S603


def git(*args: str) -> str:
    result = run_git(*args)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def file_at(ref: str, path: str) -> str | None:
    result = run_git("show", f"{ref}:{path}")
    return result.stdout if result.returncode == 0 else None


def is_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.startswith("tests/") and name.startswith("test_") and name.endswith(".py")


def count_tests_and_asserts(source: str | None) -> tuple[int, int]:
    if not source:
        return 0, 0
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0, 0
    tests = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test")
    )
    asserts = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))
    return tests, asserts


def coverage_threshold(source: str | None) -> float | None:
    if not source:
        return None
    try:
        config = tomllib.loads(source)
    except tomllib.TOMLDecodeError:
        return None
    value = config.get("tool", {}).get("coverage", {}).get("report", {}).get("fail_under")
    return float(value) if value is not None else None


def changed_files(base: str) -> list[tuple[str, str, str]]:
    """Return (status, old_path, new_path) for every file changed since the merge base."""
    rows = []
    for line in git("diff", "--name-status", "-M", base, "HEAD").splitlines():
        parts = line.split("\t")
        status = parts[0][0]
        if status == "R":
            rows.append(("R", parts[1], parts[2]))
        else:
            rows.append((status, parts[1], parts[1]))
    return rows


def added_lines(base: str, path: str) -> list[str]:
    diff = git("diff", "-U0", base, "HEAD", "--", path)
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def check(base: str, allow_protected: bool) -> Report:
    report = Report()

    for status, old_path, new_path in changed_files(base):
        for path in {old_path, new_path}:
            if path.startswith(PROTECTED_PREFIXES):
                message = f"Protected path changed: {path}"
                if allow_protected:
                    report.warn(message + " (allowed by human approval label)")
                else:
                    report.fail(message + ". Needs the 'approved-protected-change' label.")

        if is_test_file(old_path) and status == "D":
            report.fail(f"Test file deleted: {old_path}")
            continue

        if is_test_file(new_path) and status in {"M", "R"}:
            old_tests, old_asserts = count_tests_and_asserts(file_at(base, old_path))
            new_tests, new_asserts = count_tests_and_asserts(file_at("HEAD", new_path))
            if new_tests < old_tests:
                report.fail(f"{new_path}: test functions went from {old_tests} to {new_tests}")
            if new_asserts < old_asserts:
                report.fail(f"{new_path}: assertions went from {old_asserts} to {new_asserts}")
            if new_tests >= old_tests and new_asserts >= old_asserts:
                report.warn(f"{new_path}: existing test file modified; review changed expectations")

        if is_test_file(new_path) and status != "D":
            for line in added_lines(base, new_path):
                if SKIP_PATTERN.search(line):
                    report.fail(f"{new_path}: skip/xfail added: {line.strip()}")

    old_threshold = coverage_threshold(file_at(base, "pyproject.toml"))
    new_threshold = coverage_threshold(file_at("HEAD", "pyproject.toml"))
    if old_threshold is not None and (new_threshold is None or new_threshold < old_threshold):
        report.fail(f"Coverage threshold lowered: {old_threshold} -> {new_threshold}")

    return report


def render(report: Report, base: str) -> str:
    lines = [f"## Verification guard (compared with `{base}`)", ""]
    if not report.failures and not report.warnings:
        lines.append("No changes that weaken verification were found.")
    for message in report.failures:
        lines.append(f"- FAIL: {message}")
    for message in report.warnings:
        lines.append(f"- WARN: {message}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main", help="branch or commit to compare with")
    args = parser.parse_args()

    merge_base = git("merge-base", args.base, "HEAD").strip()
    allow = os.environ.get("ALLOW_PROTECTED_CHANGES", "").lower() == "true"
    report = check(merge_base, allow)

    text = render(report, args.base)
    print(text)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(text)
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
