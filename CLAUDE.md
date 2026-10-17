# Claude Code

Read and follow AGENTS.md: it contains this repository's commands, rules and conventions.

@AGENTS.md

## Claude Code specifics

- This repository's `.claude/settings.json` denies reading `.env` files and editing the
  verification plane. Those rules are a convenience, not the security boundary: CI, the
  guard script, CODEOWNERS and branch protection are what actually protect the project.
- Prefer running the test suite over reasoning about whether code works.
