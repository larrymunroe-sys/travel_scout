#!/usr/bin/env bash
set -e

# Ensure Render Python virtual environment is in PATH
if [ -d "/opt/render/project/src/.venv/bin" ]; then
    export PATH="/opt/render/project/src/.venv/bin:$PATH"
fi

# Fallback check for user local bin
if [ -d "$HOME/.local/bin" ]; then
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "=== System Information ==="
echo "Working directory: $(pwd)"
echo "PATH: $PATH"
echo "Port: ${PORT:-8000}"

# Launch Uvicorn with available python/uvicorn binary
if command -v uvicorn >/dev/null 2>&1; then
    echo "Starting via uvicorn..."
    exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
elif [ -f "/opt/render/project/src/.venv/bin/uvicorn" ]; then
    echo "Starting via /opt/render/project/src/.venv/bin/uvicorn..."
    exec /opt/render/project/src/.venv/bin/uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
elif command -v python3 >/dev/null 2>&1; then
    echo "Starting via python3 -m uvicorn..."
    exec python3 -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
elif command -v python >/dev/null 2>&1; then
    echo "Starting via python -m uvicorn..."
    exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
else
    echo "Starting via direct fallback..."
    exec /opt/render/project/src/.venv/bin/python main.py web
fi
