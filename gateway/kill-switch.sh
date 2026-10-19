#!/usr/bin/env bash
# Kill switch: stop every agent from calling models, in seconds, without touching the real
# provider key or any human's access. It blocks the virtual keys tagged as agent keys
# (metadata.plane = "generation", set by create-project-key.sh), for all projects or one.
# Blocking is reversible: unblock restores the same keys, so agents need no new credentials.
#
# Usage:
#   ./kill-switch.sh status  [project]
#   ./kill-switch.sh block   "<reason>" [project]
#   ./kill-switch.sh unblock "<reason>" [project]
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

ACTION="${1:?usage: ./kill-switch.sh status|block|unblock [reason] [project]}"
case "$ACTION" in
  status) REASON=""; PROJECT="${2:-}" ;;
  block | unblock)
    REASON="${2:?a reason is required, for example: \"runaway spend on mini-factory\"}"
    PROJECT="${3:-}"
    ;;
  *) echo "unknown action: $ACTION" >&2; exit 2 ;;
esac

ACTION="$ACTION" REASON="$REASON" PROJECT="$PROJECT" CHANGED_BY="${USER:-unknown}" python3 - <<'PY'
import json
import os
import urllib.parse
import urllib.request

GATEWAY = "http://localhost:4000"
HEADERS = {
    "Authorization": f"Bearer {os.environ['LITELLM_MASTER_KEY']}",
    "Content-Type": "application/json",
}


def call(method: str, path: str, body: dict | None = None, extra: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        GATEWAY + path, data=data, method=method, headers={**HEADERS, **(extra or {})}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def agent_keys(project: str) -> list[dict]:
    keys, page = [], 1
    while True:
        query = urllib.parse.urlencode({"return_full_object": "true", "size": 100, "page": page})
        result = call("GET", f"/key/list?{query}")
        keys += result.get("keys", [])
        if page >= (result.get("total_pages") or 1):
            break
        page += 1
    metadata = [(k, k.get("metadata") or {}) for k in keys]
    return [
        k
        for k, m in metadata
        if m.get("plane") == "generation" and (not project or m.get("project") == project)
    ]


action, reason, project = os.environ["ACTION"], os.environ["REASON"], os.environ["PROJECT"]
keys = agent_keys(project)
scope = f"project '{project}'" if project else "all projects"
print(f"{len(keys)} agent key(s) in {scope}")

for key in keys:
    if action in ("block", "unblock"):
        call(
            "POST",
            f"/key/{action}",
            {"key": key["token"]},
            {"litellm-changed-by": f"{os.environ['CHANGED_BY']} via kill-switch: {reason}"},
        )
        key["blocked"] = action == "block"
    state = "BLOCKED" if key.get("blocked") else "active"
    print(f"  {key.get('key_alias') or '(no alias)':30} {state}")
PY
