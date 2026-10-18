#!/bin/sh
set -e

# Platform volumes (Render disks, Fly volumes) are often mounted root-owned,
# so fix ownership before dropping privileges to the app user.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data
    chown -R appuser:appuser /app/data
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi

exec "$@"
