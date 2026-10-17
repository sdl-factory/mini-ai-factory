#!/usr/bin/env bash
# Runs inside the sandbox: prepare a fresh clone on a task branch, then start the agent.
set -euo pipefail

: "${REPO:?REPO (owner/name) is required}"
: "${TASK:?TASK is required}"

git config --global user.name "mini-factory-agent"
git config --global user.email "mini-factory-agent@users.noreply.github.com"
gh auth setup-git   # git uses GH_TOKEN, the agent account's fine-grained token

git clone --quiet "https://github.com/${REPO}.git" repo
cd repo
git switch -c "agent/${TASK}"

python3 -m venv .venv
. .venv/bin/activate
pip install --quiet -r requirements-dev.txt

echo
echo "Sandbox ready on branch agent/${TASK}."
echo "Model calls go through the gateway; this container has no other credentials."
echo
if [ "${1:-}" = "--shell" ]; then
  exec bash
fi
exec claude "$@"
