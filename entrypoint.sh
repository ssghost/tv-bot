#!/bin/bash
set -e

echo "[1/4] Install dependencies."
if [ -f requirements.txt ]; then
    pip install --no-cache-dir -r requirements.txt
fi

echo "[2/4] Initialize Tmux Sessions."
tmux new-session -d -s tv_browser \
    "python tools/run_browser.py --remote-debugging-port=9222"

tmux new-session -d -s tv_backend \
    "python main.py"

echo "[3/4] Initialize Log Process."
(
    while true; do
        sleep 1800
        TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
        mkdir -p /app/logs_archive
        if [ -d /app/logs ]; then
            cp -r /app/logs/* /app/logs_archive/ 2>/dev/null || true
            echo "[$(date)] log saved to /app/logs_archive"
        fi
    done
) &

echo "[4/4] Deployment complete."
exec tmux attach-session -t tv_backend
