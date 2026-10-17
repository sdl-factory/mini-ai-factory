"""Ties acceptance tests to the status of their spec.

Every acceptance test is marked with @pytest.mark.spec("NNN"). The matching file
specs/NNN-*.md contains a line "Status: pending" or "Status: implemented".

- pending spec      -> its acceptance tests are expected to fail (strict xfail), so main stays green
                       while the work is not done yet.
- implemented spec  -> its acceptance tests must pass.
- pending spec whose tests already pass -> the build fails (XPASS strict), reminding the
  implementer to flip the spec to "Status: implemented" in the same pull request.

This directory belongs to the verification plane: agents must never edit it.
"""

import re
from pathlib import Path

import pytest

SPECS_DIR = Path(__file__).resolve().parents[2] / "specs"
STATUS_LINE = re.compile(r"^Status:\s*(pending|implemented)\s*$", re.IGNORECASE | re.MULTILINE)


def spec_status(spec_id: str) -> str:
    matches = sorted(SPECS_DIR.glob(f"{spec_id}-*.md"))
    if len(matches) != 1:
        raise pytest.UsageError(f"Expected one spec file for {spec_id}, found {len(matches)}")
    found = STATUS_LINE.search(matches[0].read_text(encoding="utf-8"))
    if found is None:
        raise pytest.UsageError(f"{matches[0].name} needs a 'Status: pending|implemented' line")
    return found.group(1).lower()


def pytest_collection_modifyitems(config, items):
    for item in items:
        marker = item.get_closest_marker("spec")
        if marker is None:
            continue
        spec_id = marker.args[0]
        if spec_status(spec_id) == "pending":
            item.add_marker(
                pytest.mark.xfail(
                    strict=True,
                    reason=f"Spec {spec_id} is pending; set 'Status: implemented' when done.",
                )
            )
