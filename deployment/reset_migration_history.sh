#!/usr/bin/env bash
# One-time step when upgrading an existing database to the committed migrations.
#
# Migrations used to be git-ignored and generated per machine, so django_migrations
# holds names (e.g. qc 0001..0068) that no longer exist on disk. This script backs up
# the database, forgets those rows and marks the committed 0001_initial baselines
# (which match the existing tables) as applied. Afterwards run `python manage.py migrate`.
set -euo pipefail

cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python}"
DB="${EBAST_DB_PATH:-db.sqlite3}"
APPS="core qc qcfm cl_seiscomp bast"

cp "$DB" "$DB.bak-$(date +%Y%m%d%H%M%S)"

"$PYTHON" manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"DELETE FROM django_migrations WHERE app IN ('core', 'qc', 'qcfm', 'cl_seiscomp', 'bast')\")
"

for app in $APPS; do
    "$PYTHON" manage.py migrate "$app" 0001 --fake
done

echo "Migration history reset. Now run: $PYTHON manage.py migrate"
