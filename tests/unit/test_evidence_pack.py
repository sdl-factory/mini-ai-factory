"""Tests for the evidence pack: the audit logic, with API responses recorded as fixtures."""

import hashlib
import subprocess

import pytest

import governance.evidence_pack as ep

HEAD = "6cdd27a" + "0" * 33
OLD = "1111111" + "0" * 33


def review(user, state, commit, at="2026-10-19T19:50:00Z"):
    return {"user": {"login": user}, "state": state, "commit_id": commit, "submitted_at": at}


def facts(author="sdl-factory-agent", reviews=(), body="Implements: specs/001-note-tags.md"):
    return {
        "repo": "org/repo",
        "pr": {
            "number": 5,
            "title": "Add note tags",
            "html_url": "https://github.com/org/repo/pull/5",
            "body": body,
            "user": {"login": author},
            "merged_at": "2026-10-19T19:53:02Z",
            "merged_by": {"login": "delorenzostefano"},
            "merge_commit_sha": "40e31fc",
            "head": {"sha": HEAD},
            "base": {"sha": "f24ac98"},
            "labels": [],
        },
        "reviews": list(reviews),
        "commits": [
            {
                "sha": HEAD,
                "author": None,
                "commit": {"author": {"name": "mini-factory-agent", "email": "a@example.com"}},
            }
        ],
        "files": [{"filename": "app/main.py"}, {"filename": "tests/acceptance/test_x.py"}],
        "checks": [{"name": "quality", "conclusion": "success", "html_url": "https://ci/1"}],
    }


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("## Spec\n\nImplements: specs/001-note-tags.md\n", ("spec", "specs/001-note-tags.md")),
        ("No spec: control-layer tooling.\n\n## What", ("no-spec", "control-layer tooling.")),
        ("Fixes a typo", ("missing", "")),
        (None, ("missing", "")),
    ],
)
def test_spec_link_is_parsed_from_the_pr_body(body, expected):
    assert ep.spec_link(body) == expected


def test_approval_on_the_final_commit_counts():
    result = ep.approvals([review("human", "APPROVED", HEAD)], "agent", HEAD)
    assert ep.approved_on_final_commit(result)


def test_approval_of_an_earlier_commit_does_not_count():
    result = ep.approvals([review("human", "APPROVED", OLD)], "agent", HEAD)
    assert result[0]["on_final_commit"] is False
    assert not ep.approved_on_final_commit(result)


def test_authors_cannot_approve_their_own_change():
    assert ep.approvals([review("agent", "APPROVED", HEAD)], "agent", HEAD) == []


def test_latest_decisive_review_per_reviewer_wins():
    reviews = [
        review("human", "APPROVED", HEAD, at="2026-10-19T10:00:00Z"),
        review("human", "COMMENTED", HEAD, at="2026-10-19T11:00:00Z"),
        review("human", "CHANGES_REQUESTED", HEAD, at="2026-10-19T12:00:00Z"),
    ]
    assert ep.approvals(reviews, "agent", HEAD) == []


def test_protected_paths_are_listed():
    assert ep.protected_paths(facts()["files"]) == ["tests/acceptance/test_x.py"]


def test_pack_flags_a_merge_without_approval_and_an_unlinked_commit():
    pack = ep.render(facts(), "exit code 0", "implemented")
    assert "Approval of the final commit by someone other than the author: **NO**" in pack
    assert "merged through a ruleset bypass" in pack
    assert "`sdl-factory-agent` (agent)" in pack
    assert "| **no** |" in pack
    assert "status at the merge commit: implemented" in pack


def test_pack_records_an_approval_on_the_final_commit():
    pack = ep.render(facts(reviews=[review("human", "APPROVED", HEAD)]), "ok", "implemented")
    assert "other than the author: yes" in pack
    assert "`human` at 2026-10-19T19:50:00Z; on the final commit: yes" in pack


def test_pack_without_spec_link_says_so():
    assert "No spec link and no reason given" in ep.render(facts(body="typo"), "ok", "")
    assert "Reason given: tooling" in ep.render(facts(body="No spec: tooling"), "ok", "")


def test_pack_hash_covers_its_content():
    pack = ep.render(facts(), "exit code 0", "implemented")
    body, footer = pack.split("\n---\n")
    assert hashlib.sha256(body.encode()).hexdigest() in footer


def test_collect_reads_the_pull_request_and_its_final_commit_checks():
    calls = []

    def api(path):
        calls.append(path)
        if path.endswith("/pulls/5"):
            return {"head": {"sha": HEAD}}
        if "check-runs" in path:
            return {"check_runs": []}
        return []

    result = ep.collect("org/repo", 5, api=api)
    assert result["checks"] == []
    assert f"repos/org/repo/commits/{HEAD}/check-runs" in calls


def test_spec_status_reads_the_spec_at_the_merge_commit():
    def show(*args):
        return "# 001\n\nStatus: implemented\n"

    assert ep.spec_status("abc", "specs/001.md", show=show) == "implemented"
    assert ep.spec_status("abc", "specs/x.md", show=lambda *a: "no status") == "no Status line"


def test_spec_status_when_the_file_is_missing():
    def show(*args):
        raise subprocess.CalledProcessError(128, "git")

    assert "not found" in ep.spec_status("abc", "specs/x.md", show=show)


def test_main_writes_the_pack(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ep, "OUTPUT_DIR", tmp_path)
    code = ep.main(
        ["5"],
        collect_facts=lambda repo, n: facts(),
        guard=lambda base, head: "exit code 0",
        status_of=lambda sha, path: "implemented",
    )
    assert code == 0
    assert (tmp_path / "pr-5.md").read_text().startswith("# Evidence pack")
    assert "written" in capsys.readouterr().out


def test_main_rejects_bad_arguments():
    assert ep.main(["five"]) == 2
