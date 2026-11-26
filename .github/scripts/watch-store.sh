#!/usr/bin/env bash
# Prints one line about the store every few seconds, until it is stopped.
#
# The build of an index is one transaction, so its rows cannot be counted from outside before
# it ends. What can be seen is how large the database is and since when a transaction is open.
# The workflow runs this next to the real-data tests, so that the job log shows the build
# moving. It asks through the psql inside the service container, which the environment variable
# POSTGRES_CONTAINER names. A question that fails is reported and does not stop anything.
#
#   bash .github/scripts/watch-store.sh [SECONDS] [DATABASE]      (60 and "wixqa" when not given)

set -u

pause="${1:-60}"
database="${2:-wixqa}"
if [[ ! "${pause}" =~ ^[0-9]+$ ]] || [[ ! "${database}" =~ ^[a-z][a-z0-9_]*$ ]]; then
  echo "usage: watch-store.sh [SECONDS] [DATABASE]" >&2
  exit 2
fi

started="$(date +%s)"
first=""
question="SELECT pg_database_size(current_database()),
  coalesce((SELECT 'a transaction is open since ' || to_char(min(xact_start) AT TIME ZONE 'UTC', 'HH24:MI:SS') || ' UTC'
            FROM pg_stat_activity
            WHERE datname = current_database() AND pid <> pg_backend_pid() AND xact_start IS NOT NULL
            HAVING count(*) > 0), 'no transaction is open')"

# Stopping this script also stops the pause it is in, so that nothing of it stays behind.
pausing=""
trap '[ -z "${pausing}" ] || kill "${pausing}" 2> /dev/null; exit 0' TERM INT

while true; do
  sleep "${pause}" &
  pausing="$!"
  wait "${pausing}" || true
  minutes="$(( ($(date +%s) - started) / 60 ))"
  if answer="$(docker exec --interactive "${POSTGRES_CONTAINER:-}" psql --username postgres --dbname "${database}" \
    --no-psqlrc --quiet --tuples-only --no-align --field-separator '|' --command "${question}" 2>&1 < /dev/null)"; then
    bytes="${answer%%|*}"
    [ -n "${first}" ] || first="${bytes}"
    echo "[store, minute ${minutes}] the database holds $(( bytes / 1048576 )) MB (at the first look: $(( first / 1048576 )) MB); ${answer#*|}"
  else
    echo "[store, minute ${minutes}] the store did not answer: ${answer%%$'\n'*}"
  fi
done
