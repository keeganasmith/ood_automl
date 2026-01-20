# Benchmarks

## Responsiveness benchmark

The responsiveness benchmark now measures **websocket/session readiness** instead of backend process start time. The backend emits a dedicated log marker when a websocket session is accepted:

```
OOD_AUTOML_READY <unix_timestamp_seconds>
```

The script `benchmarks/scripts/run_responsiveness_benchmark.sh` watches the backend log and computes `session_ready_latency_ms` as the delta between the benchmark start timestamp and the first `OOD_AUTOML_READY` marker. This avoids using the timestamp of the first log line, which may be unrelated to websocket readiness.

### Usage

```
START_TS=$(python - <<'PY'
import time
print(time.time())
PY
)

./benchmarks/scripts/run_responsiveness_benchmark.sh /path/to/backend.log
```

Outputs:

```
session_ready_timestamp=<unix_timestamp_seconds>
session_ready_latency_ms=<milliseconds>
```
