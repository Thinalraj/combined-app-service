#!/usr/bin/env bash
# FINISH-01: launcher manages children and reads system_assets/runtime.json.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$ROOT_DIR/launch_stack.py" "$@"
