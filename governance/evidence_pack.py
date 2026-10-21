"""Evidence pack for a merged pull request, written for an auditor.

Answers, for one change: what was intended (the spec), who wrote it (human or agent), who
approved it and whether they approved the code that was merged, which gates passed, and
what the verification guard says when it is run again on the merged code. Facts come from
the GitHub API and from git; the guard is re-run rather than trusted from a CI log.

Usage (from the repository root, with the gh CLI logged in):
    python -m governance.evidence_pack 5
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from scripts.guard_tests import PROTECTED_PREFIXES

AGENT_ACCOUNTS = frozenset(os.environ.get("FACTORY_AGENTS", "sdl-factory-agent").split(","))
OUTPUT_DIR = Path("evidence")


def gh_api(path: str) -> dict | list:
    result = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True)  # noqa: S603, S607
    return json.loads(result.stdout)


def git(*args: str, cwd: str | None = None) -> str:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True, cwd=cwd)  # noqa: S603, S607
    return result.stdout


def collect(repo: str, number: int, api: Callable = gh_api) -> dict:
    base = f"repos/{repo}/pulls/{number}"
    pr = api(base)
    return {
        "repo": repo,
        "pr": pr,
        "reviews": api(f"{base}/reviews?per_page=100"),
        "commits": api(f"{base}/commits?per_page=100"),
        "files": api(f"{base}/files?per_page=100"),
        "checks": api(f"repos/{repo}/commits/{pr['head']['sha']}/check-runs")["check_runs"],
    }


def spec_link(body: str | None) -> tuple[str, str]:
    """('spec', path), ('no-spec', reason) or ('missing', '')."""
    body = body or ""
    if match := re.search(r"Implements:\s*(specs/\S+\.md)", body):
        return "spec", match.group(1)
    if match := re.search(r"^No spec:\s*(.+)$", body, re.MULTILINE):
        return "no-spec", match.group(1).strip()
    return "missing", ""


def approvals(reviews: list[dict], author: str, head_sha: str) -> list[dict]:
    """Each reviewer's latest decisive review; approvals by the author don't count."""
    latest: dict[str, dict] = {}
    for review in sorted(reviews, key=lambda r: r.get("submitted_at") or ""):
        if review["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[review["user"]["login"]] = review
    return [
        {
            "reviewer": login,
            "at": review["submitted_at"],
            "on_final_commit": review["commit_id"] == head_sha,
        }
        for login, review in latest.items()
        if review["state"] == "APPROVED" and login != author
    ]


def approved_on_final_commit(approved: list[dict]) -> bool:
    return any(a["on_final_commit"] for a in approved)


def protected_paths(files: list[dict]) -> list[str]:
    return [f["filename"] for f in files if f["filename"].startswith(PROTECTED_PREFIXES)]


def spec_status(merge_sha: str, path: str, show: Callable = git) -> str:
    try:
        text = show("show", f"{merge_sha}:{path}")
    except subprocess.CalledProcessError:
        return "spec file not found at the merge commit"
    match = re.search(r"^Status:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "no Status line"


def rerun_guard(base_sha: str, head_sha: str) -> str:
    """Run the guard on the PR's final commit in a throwaway worktree."""
    merge_base = git("merge-base", base_sha, head_sha).strip()
    with tempfile.TemporaryDirectory() as tmp:
        worktree = str(Path(tmp) / "pr")
        git("worktree", "add", "--detach", worktree, head_sha)
        try:
            result = subprocess.run(  # noqa: S603
                [sys.executable, "scripts/guard_tests.py", "--base", merge_base],
                cwd=worktree,
                capture_output=True,
                text=True,
            )
        finally:
            git("worktree", "remove", "--force", worktree)
    return f"exit code {result.returncode}\n\n{result.stdout.strip()}"


def render(facts: dict, guard_output: str, status: str) -> str:
    pr = facts["pr"]
    author = pr["user"]["login"]
    head = pr["head"]["sha"]
    kind, link = spec_link(pr.get("body"))
    approved = approvals(facts["reviews"], author, head)
    protected = protected_paths(facts["files"])
    final_ok = approved_on_final_commit(approved)

    lines = [
        f"# Evidence pack: {facts['repo']} #{pr['number']}",
        "",
        f"**{pr['title']}**  ",
        f"{pr['html_url']}",
        "",
        "## Summary",
        "",
        f"- Merged at: {pr.get('merged_at') or 'not merged'}",
        f"- Merged by: {(pr.get('merged_by') or {}).get('login', '-')}",
        f"- Merge commit: `{pr.get('merge_commit_sha')}`",
        f"- Final commit reviewed and tested: `{head}`",
        "- Approval of the final commit by someone other than the author: "
        + ("yes" if final_ok else "**NO**"),
        "",
        "## Intent",
        "",
    ]
    if kind == "spec":
        lines.append(f"- Implements `{link}`; status at the merge commit: {status}")
    elif kind == "no-spec":
        lines.append(f"- No spec. Reason given: {link}")
    else:
        lines.append("- **No spec link and no reason given**")
    lines += [
        "",
        "## Who wrote it",
        "",
        f"- Pull request author: `{author}` ({'agent' if author in AGENT_ACCOUNTS else 'human'})",
        "",
        "| Commit | Author | Email | Linked to a GitHub account |",
        "|---|---|---|---|",
    ]
    for c in facts["commits"]:
        account = (c.get("author") or {}).get("login")
        lines.append(
            f"| `{c['sha'][:7]}` | {c['commit']['author']['name']} | "
            f"{c['commit']['author']['email']} | {account or '**no**'} |"
        )
    lines += ["", "## Who approved it", ""]
    if approved:
        for a in approved:
            final = "yes" if a["on_final_commit"] else "**no, an earlier commit**"
            lines.append(f"- `{a['reviewer']}` at {a['at']}; on the final commit: {final}")
    else:
        merged = "merged through a ruleset bypass" if pr.get("merged_at") else "not merged"
        lines.append(f"- **No approval** ({merged})")
    lines += ["", "## Gates on the final commit", "", "| Check | Result |", "|---|---|"]
    for check in sorted(facts["checks"], key=lambda c: c["name"]):
        lines.append(f"| [{check['name']}]({check['html_url']}) | {check['conclusion']} |")
    lines += [
        "",
        "## Scope",
        "",
        f"- Files changed: {len(facts['files'])}",
        f"- Protected paths touched: {', '.join(protected) or 'none'}",
        f"- Labels: {', '.join(lab['name'] for lab in pr.get('labels', [])) or 'none'}",
        "",
        "## Verification guard, re-run on the final commit",
        "",
        "```",
        guard_output,
        "```",
        "",
    ]
    body = "\n".join(lines)
    digest = hashlib.sha256(body.encode()).hexdigest()
    return f"{body}\n---\nSHA-256 of the content above: `{digest}`\n"


def main(
    argv: list[str],
    *,
    collect_facts: Callable = collect,
    guard: Callable = rerun_guard,
    status_of: Callable = spec_status,
) -> int:
    if len(argv) != 1 or not argv[0].isdigit():
        print("usage: python -m governance.evidence_pack <pull-request-number>", file=sys.stderr)
        return 2
    repo = os.environ.get("GITHUB_REPOSITORY", "sdl-factory/mini-ai-factory")
    facts = collect_facts(repo, int(argv[0]))
    pr = facts["pr"]
    kind, link = spec_link(pr.get("body"))
    status = status_of(pr["merge_commit_sha"], link) if kind == "spec" else ""
    pack = render(facts, guard(pr["base"]["sha"], pr["head"]["sha"]), status)
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"pr-{pr['number']}.md"
    path.write_text(pack, encoding="utf-8")
    print(f"written {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
