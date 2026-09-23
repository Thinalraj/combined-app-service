#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  kill "${SIGNAL_PID:-}" "${WEIGHT_PID:-}" "${IMAGE_PID:-}" "${VIEW_PID:-}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting signal service on :8001"
(cd "$ROOT_DIR/service/signal-service" && python3 rest_service.py --simulate) & SIGNAL_PID=$!
echo "Starting weight service on :8002"
(cd "$ROOT_DIR/service/weight-service" && python3 fast-api-mettler.py) & WEIGHT_PID=$!
echo "Starting image service on :8003"
(cd "$ROOT_DIR/service/image-service" && python3 -m uvicorn api:app --host 0.0.0.0 --port 8003) & IMAGE_PID=$!
echo "Starting view service on :8080"
(cd "$ROOT_DIR/service/view-service" && python3 app.py) & VIEW_PID=$!

echo "Stack running: view http://127.0.0.1:8080"
wait "$SIGNAL_PID" "$WEIGHT_PID" "$IMAGE_PID" "$VIEW_PID"
