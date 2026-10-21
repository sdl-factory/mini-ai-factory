#!/usr/bin/env bash
# Onboard a project onto the model gateway: one virtual key per project, limited to the
# models that project is allowed to use, with a hard budget and a rate limit. Agents get
# this key, never the real provider key, so it can be revoked or capped at any time.
#
# A project declares the class of data it handles; the platform decides which models that
# class may use. Confidential data never leaves the premises: local models only.
#
# Usage: ./create-project-key.sh [project-name] [budget-in-usd] [public|internal|confidential]
#   e.g. an on-premises client: ./create-project-key.sh client-onprem 1 confidential
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

PROJECT="${1:-mini-factory}"
BUDGET="${2:-5}"
DATA_CLASS="${3:-internal}"

case "$DATA_CLASS" in
  public | internal) MODELS_JSON='["claude-sonnet-5-5", "claude-haiku-5-5"]' ;;
  confidential) MODELS_JSON='["local-qwen3-8b"]' ;;
  *) echo "unknown data class: $DATA_CLASS (use public, internal or confidential)" >&2; exit 2 ;;
esac

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
  "metadata": {"project": "${PROJECT}", "plane": "generation", "data_class": "${DATA_CLASS}"}
}
JSON
echo
echo "Copy the \"key\" value above: it is shown only once. Give it to the agent sandbox as AGENT_GATEWAY_KEY."
