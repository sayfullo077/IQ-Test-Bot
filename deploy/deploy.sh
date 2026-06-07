#!/bin/bash
# Deploy / update script — run from /opt/iq-bot after uploading files
# Usage: bash deploy/deploy.sh

set -e

BOT_DIR=/opt/iq-bot
cd $BOT_DIR

echo "=== 1. Virtual environment ==="
python3.12 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo "=== 2. Restart bot (seed avtomatik ishlaydi) ==="
systemctl restart iq-bot
sleep 2
systemctl status iq-bot --no-pager

echo ""
echo "✅ Deploy done! Logs: journalctl -u iq-bot -f"
