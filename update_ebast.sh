#!/usr/bin/env bash
# Update the deployed app. db.sqlite3 is git-ignored, so git pull leaves it alone.
# First update after migrations became committed: run deployment/reset_migration_history.sh once before migrate.
set -euo pipefail
cd "$(dirname "$0")"

# Online backup (safe while the app is running in WAL mode).
python -c "import sqlite3; sqlite3.connect('db.sqlite3').backup(sqlite3.connect('db.sqlite3.bak'))"
git pull
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart ebast.service
