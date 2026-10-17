#!/usr/bin/env bash
# Start a disposable agent sandbox for one task. Everything inside is deleted on exit;
# only what the agent pushed to its branch survives.
#
# Usage:
#   export REPO=your-org/mini-ai-factory
#   export AGENT_GH_TOKEN=github_pat_...     # the agent account's fine-grained token
#   export AGENT_GATEWAY_KEY=sk-...          # from gateway/create-project-key.sh
#   ./sandbox/run.sh spec-001            # start the agent
#   ./sandbox/run.sh spec-001 --shell    # or a shell in the sandbox, for debugging
set -euo pipefail
cd "$(dirname "$0")"

: "${REPO:?set REPO to your-org/mini-ai-factory}"
: "${AGENT_GH_TOKEN:?set AGENT_GH_TOKEN to the agent account token}"
: "${AGENT_GATEWAY_KEY:?set AGENT_GATEWAY_KEY to the project gateway key}"
TASK="${1:?usage: ./sandbox/run.sh <task-name> [extra claude arguments]}"
shift

docker build --quiet -t mini-factory-sandbox . >/dev/null

# --cap-drop ALL, no-new-privileges and resource limits harden the container. The
# factory-net network lets it reach the gateway by name. Exercise (phase 7): restrict its
# internet egress to GitHub and PyPI only, and watch what breaks.
docker run --rm -it \
  --name "agent-${TASK}" \
  --network factory-net \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 512 \
  -e REPO="$REPO" \
  -e TASK="$TASK" \
  -e GH_TOKEN="$AGENT_GH_TOKEN" \
  -e ANTHROPIC_BASE_URL=http://litellm:4000 \
  -e ANTHROPIC_AUTH_TOKEN="$AGENT_GATEWAY_KEY" \
  -e ANTHROPIC_MODEL=claude-sonnet-5-5 \
  -e ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5 \
  -e ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5 \
  -e ANTHROPIC_DEFAULT_OPUS_MODEL=claude-sonnet-5-5 \
  mini-factory-sandbox "$@"
