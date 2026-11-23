#!/bin/bash
# Zero-Downtime Soft Reload Script for NJUASCO (njuascogh.org)
# Syncs code updates and gracefully reloads Gunicorn workers (SIGHUP) & Nginx
# without dropping active connections.

set -euo pipefail

PROJECT_NAME="schsite"
USER="bryt"
VPS_IP="62.84.187.51"
SSH_PORT="22"
PROJECT_DIR="/home/$USER/sites/$PROJECT_NAME"
DOMAIN="njuascogh.org"

# ==============================================================================
# PHASE 1: Run from local machine -> sync changes & trigger remote soft reload
# (Automatically skipped if "--remote" is passed or if already inside $PROJECT_DIR)
# ==============================================================================
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" != "--remote" ] && [ "$LOCAL_DIR" != "$PROJECT_DIR" ]; then
    echo "========================================================="
    echo "Soft-reloading $PROJECT_NAME on $USER@$VPS_IP (zero-downtime)"
    echo "========================================================="

    # Sync updated application files (keeps remote venv, db, media, and .env intact)
    echo "=> Syncing updated project files to $USER@$VPS_IP:$PROJECT_DIR/..."
    rsync -avz \
        -e "ssh -p $SSH_PORT" \
        --exclude 'venv/' \
        --exclude '.venv/' \
        --exclude '.git/' \
        --exclude '.idea/' \
        --exclude '.vscode/' \
        --exclude '__pycache__/' \
        --exclude '*.pyc' \
        --exclude 'staticfiles/' \
        --exclude 'media/' \
        --exclude '.env' \
        --exclude 'db.sqlite3' \
        "$LOCAL_DIR/" "$USER@$VPS_IP:$PROJECT_DIR/"

    # Run remote soft-reload steps
    ssh -t -p "$SSH_PORT" "$USER@$VPS_IP" "bash '$PROJECT_DIR/update.sh' --remote"

    echo "========================================================="
    echo "✓ Soft reload complete! No downtime incurred."
    echo "========================================================="
    exit 0
fi

# ==============================================================================
# PHASE 2: Remote VPS -> Migrate, collectstatic, SIGHUP Gunicorn, reload Nginx
# ==============================================================================
cd "$PROJECT_DIR"
source venv/bin/activate

# 1. Install any new dependencies, apply migrations & refresh static files
echo "=> Updating dependencies, running migrations, and collecting static files..."
pip install -r requirements.txt --quiet
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 2. Graceful zero-downtime Gunicorn reload (SIGHUP spawns new workers before retiring old ones)
echo "=> Sending SIGHUP to Gunicorn master process for zero-downtime worker reload..."
GUNICORN_SERVICE="gunicorn_${PROJECT_NAME}"
if [ "$(systemctl show -p LoadState --value "$GUNICORN_SERVICE" 2>/dev/null || echo 'not-found')" = "not-found" ]; then
    GUNICORN_SERVICE="gunicorn"
fi

MAIN_PID=$(systemctl show -p MainPID --value "$GUNICORN_SERVICE" 2>/dev/null || echo "0")
if [ "$MAIN_PID" != "0" ] && [ -n "$MAIN_PID" ]; then
    sudo kill -HUP "$MAIN_PID"
    echo "✓ Gunicorn master ($GUNICORN_SERVICE, PID $MAIN_PID) gracefully reloaded workers."
else
    echo "=> Gunicorn ($GUNICORN_SERVICE) was not running; starting service..."
    sudo systemctl start "$GUNICORN_SERVICE"
fi

# 3. Graceful Nginx config reload (zero-downtime)
if sudo nginx -t >/dev/null 2>&1; then
    sudo systemctl reload nginx
    echo "✓ Nginx gracefully reloaded."
fi
