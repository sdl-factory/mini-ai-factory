#!/usr/bin/env bash
# Prove tenant isolation instead of assuming it. In each tenant namespace this starts a small
# web server and a client (both compliant with Pod Security "restricted"), then checks:
#   - a tenant can reach its own service;
#   - a tenant cannot reach another tenant's service, in either direction;
#   - a pod outside every tenant cannot reach in;
#   - a tenant cannot reach the internet (only DNS is allowed out);
#   - a pod that runs as root is rejected.
# A policy is only as good as the component enforcing it: run this on every new cluster.
#
# Usage: ./terraform/isolation-test.sh [tenant-a] [tenant-b]
set -euo pipefail

A="${1:-mini-factory}"
B="${2:-client-a}"
IMAGE="busybox:1.36"
FAILURES=0

restricted_pod() { # namespace name command
  kubectl apply -n "$1" -f - >/dev/null <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: $2
  labels: { app: $2 }
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    seccompProfile: { type: RuntimeDefault }
  containers:
    - name: main
      image: $IMAGE
      command: ["sh", "-c", "$3"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: { drop: ["ALL"] }
EOF
}

setup_tenant() { # namespace
  restricted_pod "$1" web "echo ok > /tmp/index.html && httpd -f -p 8080 -h /tmp"
  restricted_pod "$1" client "sleep 3600"
  kubectl expose pod web -n "$1" --port 8080 --name web >/dev/null
}

cleanup() {
  for ns in "$A" "$B"; do
    kubectl delete pod web client -n "$ns" --ignore-not-found --wait=false >/dev/null
    kubectl delete service web -n "$ns" --ignore-not-found >/dev/null
  done
  kubectl delete pod outsider -n default --ignore-not-found --wait=false >/dev/null
}
trap cleanup EXIT

check() { # description expected(allow|deny) namespace pod url
  local got="deny"
  if kubectl exec -n "$3" "$4" -- wget -qO- -T 3 "$5" >/dev/null 2>&1; then got="allow"; fi
  if [ "$got" = "$2" ]; then
    printf "PASS  %-48s expected %-5s got %s\n" "$1" "$2" "$got"
  else
    printf "FAIL  %-48s expected %-5s got %s\n" "$1" "$2" "$got"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "Starting test pods in $A, $B and default..."
setup_tenant "$A"
setup_tenant "$B"
kubectl run outsider -n default --image "$IMAGE" --restart=Never -- sleep 3600 >/dev/null
kubectl wait --for=condition=Ready pod --all -n "$A" --timeout=120s >/dev/null
kubectl wait --for=condition=Ready pod --all -n "$B" --timeout=120s >/dev/null
kubectl wait --for=condition=Ready pod/outsider -n default --timeout=120s >/dev/null
echo

svc() { echo "http://web.$1.svc.cluster.local:8080"; }
check "$A reaches its own service" allow "$A" client "$(svc "$A")"
check "$B reaches its own service" allow "$B" client "$(svc "$B")"
check "$A cannot reach $B" deny "$A" client "$(svc "$B")"
check "$B cannot reach $A" deny "$B" client "$(svc "$A")"
check "default namespace cannot reach $A" deny default outsider "$(svc "$A")"
check "default namespace cannot reach $B" deny default outsider "$(svc "$B")"
check "$A cannot reach the internet" deny "$A" client "http://example.com"
check "$B cannot reach the internet" deny "$B" client "http://example.com"

if kubectl run root-test -n "$B" --image nginx:1.27 --dry-run=server >/dev/null 2>&1; then
  printf "FAIL  %-48s\n" "root pod rejected in $B"
  FAILURES=$((FAILURES + 1))
else
  printf "PASS  %-48s\n" "root pod rejected in $B"
fi

echo
if [ "$FAILURES" -eq 0 ]; then echo "Isolation holds."; else echo "$FAILURES check(s) failed."; fi
exit "$FAILURES"
