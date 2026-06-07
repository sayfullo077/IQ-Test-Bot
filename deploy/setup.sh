#!/bin/bash
# Server setup script (Ubuntu/Debian)
# Run once as root: bash deploy/setup.sh

set -e

BOT_DIR=/opt/iq-bot
BOT_USER=ubuntu
ENV_FILE=$BOT_DIR/.env

echo "=== 1. System packages ==="
apt-get update -q
apt-get install -y python3.12 python3.12-venv python3-pip postgresql redis-server

echo "=== 2. .env faylini tekshirish ==="
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ $ENV_FILE topilmadi. Avval .env faylini yarating:"
    echo "   cp $BOT_DIR/.env.example $BOT_DIR/.env"
    echo "   nano $BOT_DIR/.env"
    exit 1
fi

# DATABASE_URL dan DB nomi, user va parolni ajratib olish
# Format: postgresql+asyncpg://user:password@host:port/dbname
DB_URL=$(grep "^DATABASE_URL=" "$ENV_FILE" | cut -d'=' -f2-)
DB_USER=$(echo "$DB_URL" | sed 's|.*://||' | cut -d':' -f1)
DB_PASS=$(echo "$DB_URL" | sed 's|.*://[^:]*:||' | cut -d'@' -f1)
DB_NAME=$(echo "$DB_URL" | sed 's|.*/||' | cut -d'?' -f1)

echo "   DB user: $DB_USER"
echo "   DB name: $DB_NAME"

echo "=== 3. PostgreSQL setup ==="
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || \
    sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || true

echo "=== 4. Redis ==="
systemctl enable --now redis-server

echo "=== 5. Bot directory ==="
mkdir -p $BOT_DIR
chown $BOT_USER:$BOT_USER $BOT_DIR

echo "=== 6. Systemd service ==="
cp $BOT_DIR/deploy/iq-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable iq-bot

echo ""
echo "✅ Setup done!"
echo "Keyingi qadam: bash $BOT_DIR/deploy/deploy.sh"
