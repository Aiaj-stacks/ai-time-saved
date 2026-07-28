#!/usr/bin/env bash
# dev.sh - bring up the full ai-time-saved stack in one command
# Usage:  bash dev.sh         (default: port 8768)
#         bash dev.sh 9000    (custom port)
#
# What it does:
#   1. Free up the port (kills any stale instance)
#   2. Open the dashboard in your Windows default browser (WSL)
#   3. Start serve.py in the foreground
#
# Requires: python3 in PATH. Best-effort browser-open on WSL.

set -e
PORT="${1:-8768}"
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Sanity
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not in PATH"; exit 1; }
[ -f serve.py ] || { echo "ERROR: serve.py not found (run from project root)"; exit 1; }

# Free the port (best effort)
if command -v fuser >/dev/null 2>&1; then
  fuser -k "$PORT/tcp" 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:"$PORT" 2>/dev/null | xargs -r kill 2>/dev/null || true
fi
sleep 0.3

# Open dashboard in Windows default browser (WSL only - silent failure on others)
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command "Start-Process 'http://127.0.0.1:$PORT/'" >/dev/null 2>&1 &
fi

# Hand off to serve.py (runs in foreground; Ctrl-C stops)
exec python3 serve.py "$PORT"