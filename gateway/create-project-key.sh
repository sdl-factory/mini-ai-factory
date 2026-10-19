#!/usr/bin/env bash
# Onboard a project onto the model gateway: one virtual key per project, limited to the
# models that project is allowed to use, with a hard budget and a rate limit. Agents get
# this key, never the real provider key, so it can be revoked or capped at any time.
#
# Usage: ./create-project-key.sh [project-name] [budget-in-usd] [comma-separated models]
#   e.g. an on-premises-only project: ./create-project-key.sh client-onprem 1 local-qwen3-8b
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

PROJECT="${1:-mini-factory}"
BUDGET="${2:-5}"
MODELS="${3:-claude-sonnet-5-5,claude-haiku-5-5}"
MODELS_JSON=$(MODELS="$MODELS" python3 -c 'import json, os; print(json.dumps(os.environ["MODELS"].split(",")))')

curl -sS -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d @- <<JSON
{
  "key_alias": "${PROJECT}-agent",
  "models": ${MODELS_JSON},
  "max_budget": ${BUDGET},
  "budget_duration": "30d",
  "rpm_limit": 30,
  "metadata": {"project": "${PROJECT}", "plane": "generation"}
}
JSON
echo
echo "Copy the \"key\" value above: it is shown only once. Give it to the agent sandbox as AGENT_GATEWAY_KEY."
