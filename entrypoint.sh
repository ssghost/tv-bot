#!/bin/bash
set -e

echo "[1/4] Install dependencies."
if [ -f requirements.txt ]; then
    pip install --no-cache-dir -r requirements.txt
fi

echo "[2/4] Login into TV account."
python tools/login.py

mkdir -p /root/tv_bot
touch /root/tv_bot/alerts_history.log

echo "[3/4] Initialize Tmux Sessions."
tmux new-session -d -s tv_browser \
    "python tools/run_browser.py --remote-debugging-port=9222"

tmux new-session -d -s tv_backend \
    "python main.py"

echo "[4/4] Deployment complete."
exec tmux attach-session -t tv_backend
