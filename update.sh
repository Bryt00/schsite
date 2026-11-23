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

# 0. Work out which Gunicorn unit serves this site (gunicorn_schsite or the legacy "gunicorn")
GUNICORN_SERVICE="gunicorn_${PROJECT_NAME}"
if [ "$(systemctl show -p LoadState --value "$GUNICORN_SERVICE" 2>/dev/null)" != "loaded" ]; then
    GUNICORN_SERVICE="gunicorn"
fi
echo "=> Using Gunicorn service: $GUNICORN_SERVICE"

# 1. Locate the virtualenv the live Gunicorn actually runs from, so we NEVER touch system Python
#    (Ubuntu 23.04+/24.04 blocks system-wide pip installs: "externally-managed-environment").
VENV_DIR=""
GUNICORN_BIN=$(systemctl show -p ExecStart --value "$GUNICORN_SERVICE" 2>/dev/null \
    | grep -oE 'path=[^ ;]+' | head -n1 | cut -d= -f2 || true)
if [ -n "$GUNICORN_BIN" ] && [ -x "$(dirname "$GUNICORN_BIN")/python" ]; then
    VENV_DIR="$(dirname "$(dirname "$GUNICORN_BIN")")"
fi

if [ -z "$VENV_DIR" ]; then
    for candidate in "$PROJECT_DIR/venv" "$PROJECT_DIR/.venv" "$PROJECT_DIR/env" "/home/$USER/sites/venv"; do
        if [ -x "$candidate/bin/python" ]; then
            VENV_DIR="$candidate"
            break
        fi
    done
fi

NEW_VENV=false
if [ -z "$VENV_DIR" ]; then
    VENV_DIR="$PROJECT_DIR/venv"
    echo "=> No virtualenv found; creating one at $VENV_DIR ..."
    if ! python3 -m venv "$VENV_DIR"; then
        PYVER=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
        echo "✗ Could not create a virtualenv. Install the venv module first, then re-run:"
        echo "    sudo apt install -y python3-venv python${PYVER}-venv"
        exit 1
    fi
    NEW_VENV=true
fi

PY="$VENV_DIR/bin/python"
echo "=> Using virtualenv: $VENV_DIR ($("$PY" --version 2>&1))"

# Make sure pip exists inside the venv (venvs created without python3-venv can lack it)
if ! "$PY" -m pip --version >/dev/null 2>&1; then
    echo "=> pip missing inside venv; bootstrapping with ensurepip..."
    "$PY" -m ensurepip --upgrade
fi

# 2. Install any new dependencies, apply migrations & refresh static files (all via the venv's Python)
echo "=> Updating dependencies, running migrations, and collecting static files..."
"$PY" -m pip install --upgrade pip --quiet
"$PY" -m pip install -r requirements.txt --quiet
if [ "$NEW_VENV" = true ]; then
    "$PY" -m pip install gunicorn --quiet
fi
"$PY" manage.py migrate --noinput
"$PY" manage.py collectstatic --noinput

# 3. Graceful zero-downtime Gunicorn reload (SIGHUP spawns new workers before retiring old ones)
echo "=> Sending SIGHUP to Gunicorn master process for zero-downtime worker reload..."
MAIN_PID=$(systemctl show -p MainPID --value "$GUNICORN_SERVICE" 2>/dev/null || echo "0")
if [ "$MAIN_PID" != "0" ] && [ -n "$MAIN_PID" ]; then
    sudo kill -HUP "$MAIN_PID"
    echo "✓ Gunicorn master ($GUNICORN_SERVICE, PID $MAIN_PID) gracefully reloaded workers."
else
    echo "=> Gunicorn ($GUNICORN_SERVICE) was not running; starting service..."
    sudo systemctl start "$GUNICORN_SERVICE"
fi

# 4. Graceful Nginx config reload (zero-downtime)
if sudo nginx -t >/dev/null 2>&1; then
    sudo systemctl reload nginx
    echo "✓ Nginx gracefully reloaded."
fi
