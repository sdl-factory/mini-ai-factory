#!/usr/bin/env bash
# Cost transparency: how much has this project's key spent, against which budget?
# Usage: ./cost-report.sh <virtual-key>
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
KEY="${1:?usage: ./cost-report.sh <virtual-key>}"

RESPONSE=$(curl -sS -G http://localhost:4000/key/info \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  --data-urlencode "key=${KEY}")

RESPONSE="$RESPONSE" python3 - <<'PY'
import json
import os

data = json.loads(os.environ["RESPONSE"])
info = data.get("info", data)
spend = info.get("spend") or 0
budget = info.get("max_budget")
project = (info.get("metadata") or {}).get("project")
models = ", ".join(info.get("models") or [])

print(f"Key alias : {info.get('key_alias')}")
print(f"Project   : {project}")
print(f"Models    : {models}")
print(f"Spend     : ${spend:.4f}")
if budget:
    print(f"Budget    : ${budget:.2f} ({spend / budget:.1%} used)")
PY
echo "Per-request details (model, tokens, cost) are in the admin UI: http://localhost:4000/ui -> Logs"
