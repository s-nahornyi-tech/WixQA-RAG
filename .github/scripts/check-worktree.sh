#!/usr/bin/env bash
# Fails when a file of the checkout was added or changed, outside the folders that Git ignores.
#
# The workflows run this after the tests: a test must never leave a file in the repository,
# and least of all under evals/ (specs/001-corpus-and-audit/research.md, section 4).
#
#   bash .github/scripts/check-worktree.sh
#   bash .github/scripts/check-worktree.sh --allow-new-build-record
#
# With --allow-new-build-record one kind of file may appear: a new evals/indexes/<index>/build.json,
# the build record of an index that this run built from the pinned dataset. A build record that
# existed before and was changed is still reported.
#
# Exit codes: 0 nothing unexpected, 1 a file was added or changed, 2 wrong arguments.

set -euo pipefail

allow_new_build_record=false
case "${1:-}" in
  "") ;;
  --allow-new-build-record) allow_new_build_record=true ;;
  *)
    echo "usage: check-worktree.sh [--allow-new-build-record]" >&2
    exit 2
    ;;
esac

# The identifier of an index: lower-case letters, digits and single hyphens.
new_build_record='^\?\? (evals/indexes/[a-z0-9]+(-[a-z0-9]+)*/build\.json)$'

changes="$(git status --porcelain --untracked-files=all)"

unexpected=""
allowed=""
while IFS= read -r line; do
  [ -n "${line}" ] || continue
  if [ "${allow_new_build_record}" = true ] && [[ "${line}" =~ ${new_build_record} ]]; then
    echo "::notice title=new build record::${BASH_REMATCH[1]} is new: this run built that index."
    allowed="yes"
    continue
  fi
  unexpected+="${line}"$'\n'
done <<< "${changes}"

if [ -z "${unexpected}" ]; then
  if [ -n "${allowed}" ]; then
    echo "Apart from the new build record, no file was added or changed outside the ignored folders."
  else
    echo "No file was added or changed outside the ignored folders."
  fi
  exit 0
fi

echo "Added or changed, as git status reports it:"
printf '%s' "${unexpected}"

# One annotation with the whole list; a line break inside a workflow command is written as %0A.
message="${unexpected%$'\n'}"
message="${message//'%'/%25}"
message="${message//$'\r'/%0D}"
message="${message//$'\n'/%0A}"
echo "::error title=files added or changed by the tests::${message}"
exit 1
