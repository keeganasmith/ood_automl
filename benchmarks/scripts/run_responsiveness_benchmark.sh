#!/usr/bin/env bash
set -euo pipefail

if [[ ${1:-} == "" ]]; then
  echo "Usage: $0 <backend_log_file>" >&2
  exit 1
fi

LOG_FILE="$1"
START_TS="${START_TS:-$(python - <<'PY'
import time
print(time.time())
PY
)}"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "Log file not found: $LOG_FILE" >&2
  exit 1
fi

echo "Waiting for OOD_AUTOML_READY marker in $LOG_FILE..." >&2

READY_TS=""
while IFS= read -r line; do
  if [[ "$line" =~ OOD_AUTOML_READY[[:space:]]+([0-9]+(\.[0-9]+)?) ]]; then
    READY_TS="${BASH_REMATCH[1]}"
    break
  fi
done < <(tail -n 0 -F "$LOG_FILE")

if [[ -z "$READY_TS" ]]; then
  echo "Failed to locate readiness marker." >&2
  exit 1
fi

READY_LATENCY_MS=$(python - <<'PY'
import os
start = float(os.environ["START_TS"])
ready = float(os.environ["READY_TS"])
if start > 1e12:
    start /= 1000.0
if ready > 1e12:
    ready /= 1000.0
print(int((ready - start) * 1000))
PY
)

echo "session_ready_timestamp=$READY_TS"
echo "session_ready_latency_ms=$READY_LATENCY_MS"
