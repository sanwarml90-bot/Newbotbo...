#!/bin/bash
# ============================================================
#  Sanjipro SMS Blast Bot — One-time VPS installer
#  Tested on: Ubuntu 22.04.5 LTS
# ============================================================
set -e

BOT_DIR="/root/sanjipro-bot"
PY="python3"
SERVICE_NAME="sanjipro"

echo "============================================"
echo "  Sanjipro Bot Installer"
echo "============================================"
echo ""

# ---- 1. deps ----
echo "==> [1/7] Installing system packages..."
apt update -y
apt install -y python3 python3-pip python3-venv git curl nano

# ---- 2. dir ----
echo "==> [2/7] Preparing directory: $BOT_DIR"
mkdir -p "$BOT_DIR"
cd "$BOT_DIR"

# ---- 3. pip upgrade ----
echo "==> [3/7] Upgrading pip..."
$PY -m pip install --upgrade pip

# ---- 4. python deps ----
echo "==> [4/7] Installing Python dependencies..."
if [ -f requirements.txt ]; then
    $PY -m pip install -r requirements.txt
else
    echo "    !! requirements.txt not found"
    echo "    !! Make sure you're running from project folder"
    exit 1
fi

# ---- 5. data dir ----
echo "==> [5/7] Creating data directory..."
mkdir -p /root/.sanjipro_data
chmod 700 /root/.sanjipro_data

# ---- 6. env check ----
echo "==> [6/7] Checking .env..."
if [ ! -f .env ]; then
    echo "    !! .env not found — copying from .env.example"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "    !! Edit .env and set BOT_TOKEN, GITHUB_TOKEN, etc."
        echo "    !! Then run: systemctl restart sanjipro"
    else
        echo "    !! .env.example also missing — create .env manually"
    fi
else
    echo "    ✅ .env found"
fi

# ---- 7. systemd ----
echo "==> [7/7] Installing systemd service..."
if [ -f sanjipro.service ]; then
    cp sanjipro.service /etc/systemd/system/${SERVICE_NAME}.service
    systemctl daemon-reload
    systemctl enable ${SERVICE_NAME}
    systemctl restart ${SERVICE_NAME} || true
    sleep 2
    echo ""
    echo "    Service status:"
    systemctl status ${SERVICE_NAME} --no-pager || true
else
    echo "    !! sanjipro.service not found — skipping systemd setup"
fi

echo ""
echo "============================================"
echo "  Install complete!"
echo "============================================"
echo ""
echo "Commands:"
echo "  systemctl status sanjipro"
echo "  systemctl restart sanjipro"
echo "  systemctl stop sanjipro"
echo "  journalctl -u sanjipro -f"
echo "  tail -f /root/sanjipro-bot/bot.log"
echo ""
echo "Data files:"
echo "  /root/.sanjipro_data/sanjipro_data.json"
echo "  /root/.sanjipro_data/sanjipro_data.backup.json"
echo ""
echo "If you edited .env, restart with:"
echo "  systemctl restart sanjipro"
echo ""
