#!/usr/bin/env bash
# The snapshot of an index: a dump of its schema that another job can restore
# (specs/001-corpus-and-audit/research.md, section 7).
#
# Every PostgreSQL program used here (pg_dump, pg_restore, psql) is the one inside the service
# container, so that its version is the version of the server. The container is named by the
# environment variable POSTGRES_CONTAINER. Nothing is written into the checkout: every file
# goes to a place that the caller names, outside the repository.
#
#   snapshot.sh dump INDEX FILE [DATABASE]
#       Dump the schema of the index INDEX, in pg_dump's custom format, to FILE.
#   snapshot.sh restore FILE [DATABASE]
#       Restore a dump into DATABASE. The database is created when it does not exist, and
#       pgvector is enabled in it first. The restore is one transaction: all of it or nothing.
#   snapshot.sh restore-recorded FOLDER [DATABASE]
#       For every evals/indexes/<index>/snapshot.json of the checkout: download the dump from
#       the release that the record names into FOLDER, compare its size and its SHA-256 with
#       the record, and restore it. Needs GH_TOKEN, to read the release.
#   snapshot.sh describe INDEX FILE [DATABASE]
#       Print the snapshot record (contracts/records.md, "snapshot.json") of the dump FILE of
#       the index INDEX to standard output. Needs GITHUB_REPOSITORY and GITHUB_RUN_ID.
#
# DATABASE is "wixqa" unless it is given. Exit codes: 0 done, 1 it failed, 2 wrong arguments.

set -euo pipefail

# The identifier of an index: lower-case letters, digits and single hyphens, at most 40
# characters (data-model.md, "Index").
identifier='^[a-z0-9]+(-[a-z0-9]+)*$'

fail() {
  echo "::error title=snapshot::$1"
  exit 1
}

usage() {
  echo "usage: snapshot.sh dump INDEX FILE [DATABASE] | restore FILE [DATABASE] |" \
    "restore-recorded FOLDER [DATABASE] | describe INDEX FILE [DATABASE]" >&2
  exit 2
}

# Run a program inside the service container; standard input and output pass through.
in_store() {
  docker exec --interactive "${POSTGRES_CONTAINER:?POSTGRES_CONTAINER is not set}" "$@"
}

# Run one SQL statement and print its result without decoration.
query() {
  local database="$1" statement="$2"
  in_store psql --username postgres --dbname "${database}" --no-psqlrc --quiet --tuples-only \
    --no-align --set ON_ERROR_STOP=1 --command "${statement}" < /dev/null
}

check_identifier() {
  if [[ ! "$1" =~ ${identifier} ]] || [ "${#1}" -gt 40 ]; then
    fail "\"$1\" is not a valid index identifier."
  fi
}

check_database_name() {
  [[ "$1" =~ ^[a-z][a-z0-9_]*$ ]] || fail "\"$1\" is not a database name this script accepts."
}

schema_of() {
  echo "idx_${1//-/_}"
}

dump() {
  local index="$1" file="$2" database="$3" schema
  check_identifier "${index}"
  check_database_name "${database}"
  schema="$(schema_of "${index}")"
  mkdir -p "$(dirname "${file}")"
  # --strict-names: a schema that does not exist is an error, not an empty dump.
  if ! in_store pg_dump --username postgres --dbname "${database}" --format=custom \
    --schema="${schema}" --strict-names < /dev/null > "${file}.part"; then
    rm -f "${file}.part"
    fail "The schema ${schema} of the index ${index} could not be dumped."
  fi
  mv "${file}.part" "${file}"
  echo "Dumped the schema ${schema} to ${file}: $(stat --format=%s "${file}") bytes."
}

restore() {
  local file="$1" database="$2"
  check_database_name "${database}"
  [ -f "${file}" ] || fail "The dump ${file} does not exist."
  if [ "$(query postgres "SELECT count(*) FROM pg_database WHERE datname = '${database}'")" = "0" ]; then
    query postgres "CREATE DATABASE ${database}"
  fi
  query "${database}" "CREATE EXTENSION IF NOT EXISTS vector"
  if ! in_store pg_restore --username postgres --dbname "${database}" --no-owner \
    --exit-on-error --single-transaction < "${file}"; then
    fail "The dump ${file} could not be restored into the database ${database}."
  fi
  echo "Restored ${file} into the database ${database}."
}

restore_recorded() {
  local folder="$1" database="$2" record index file bytes sha256 repository release_tag
  local found=0
  mkdir -p "${folder}"
  for record in evals/indexes/*/snapshot.json; do
    [ -f "${record}" ] || continue
    found=$((found + 1))
    index="$(jq --raw-output '.index' "${record}")"
    file="$(jq --raw-output '.file' "${record}")"
    bytes="$(jq --raw-output '.bytes' "${record}")"
    sha256="$(jq --raw-output '.sha256' "${record}")"
    repository="$(jq --raw-output '.repository' "${record}")"
    release_tag="$(jq --raw-output '.release_tag' "${record}")"

    # The record is read as data: each value has to have the form the contract gives it.
    check_identifier "${index}"
    [ "${record}" = "evals/indexes/${index}/snapshot.json" ] \
      || fail "${record} names the index ${index}, which is not the index of its folder."
    [ "${file}" = "${index}.dump" ] || fail "${record}: the file is not ${index}.dump."
    [ "${release_tag}" = "index-${index}" ] || fail "${record}: the release tag is not index-${index}."
    [[ "${sha256}" =~ ^[0-9a-f]{64}$ ]] || fail "${record}: sha256 is not a SHA-256 fingerprint."
    [[ "${bytes}" =~ ^[0-9]+$ ]] || fail "${record}: bytes is not a number."
    [[ "${repository}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] \
      || fail "${record}: repository is not of the form owner/name."

    mkdir -p "${folder}/${index}"
    if ! gh release download "${release_tag}" --repo "${repository}" --pattern "${file}" \
      --dir "${folder}/${index}" --clobber; then
      fail "The dump ${file} could not be downloaded from the release ${release_tag} of ${repository}."
    fi
    local downloaded="${folder}/${index}/${file}"
    [ "$(stat --format=%s "${downloaded}")" = "${bytes}" ] \
      || fail "The dump of the index ${index} has another size than ${record} records. Nothing was restored from it."
    [ "$(sha256sum "${downloaded}" | cut --delimiter=' ' --fields=1)" = "${sha256}" ] \
      || fail "The dump of the index ${index} has another SHA-256 than ${record} records. Nothing was restored from it."

    restore "${downloaded}" "${database}"
    echo "::notice title=snapshot::The index ${index} was restored from the release ${release_tag}: ${bytes} bytes, SHA-256 as recorded."
  done
  if [ "${found}" -eq 0 ]; then
    echo "::notice title=snapshot::No snapshot is recorded under evals/indexes/, so nothing was restored."
  fi
}

describe() {
  local index="$1" file="$2" database="$3"
  check_identifier "${index}"
  check_database_name "${database}"
  [ -f "${file}" ] || fail "The dump ${file} does not exist."
  jq --null-input \
    --arg index "${index}" \
    --arg file "$(basename "${file}")" \
    --argjson bytes "$(stat --format=%s "${file}")" \
    --arg sha256 "$(sha256sum "${file}" | cut --delimiter=' ' --fields=1)" \
    --arg format "pg_dump custom format, schema $(schema_of "${index}")" \
    --arg postgresql "$(query "${database}" "SHOW server_version")" \
    --arg pgvector "$(query "${database}" "SELECT extversion FROM pg_extension WHERE extname = 'vector'")" \
    --arg repository "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is not set}" \
    --arg release_tag "index-${index}" \
    --arg created_at "$(date --utc --date="@$(stat --format=%Y "${file}")" +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson workflow_run "${GITHUB_RUN_ID:?GITHUB_RUN_ID is not set}" \
    '{
      index: $index,
      file: $file,
      bytes: $bytes,
      sha256: $sha256,
      format: $format,
      postgresql: $postgresql,
      pgvector: $pgvector,
      repository: $repository,
      release_tag: $release_tag,
      created_at: $created_at,
      workflow_run: $workflow_run
    }'
}

case "${1:-}" in
  dump)
    [ "$#" -eq 3 ] || [ "$#" -eq 4 ] || usage
    dump "$2" "$3" "${4:-wixqa}"
    ;;
  restore)
    [ "$#" -eq 2 ] || [ "$#" -eq 3 ] || usage
    restore "$2" "${3:-wixqa}"
    ;;
  restore-recorded)
    [ "$#" -eq 2 ] || [ "$#" -eq 3 ] || usage
    restore_recorded "$2" "${3:-wixqa}"
    ;;
  describe)
    [ "$#" -eq 3 ] || [ "$#" -eq 4 ] || usage
    describe "$2" "$3" "${4:-wixqa}"
    ;;
  *) usage ;;
esac
