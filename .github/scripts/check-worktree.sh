#!/usr/bin/env bash
# Fails when a file of the checkout was added or changed, outside the folders that Git ignores.
#
# The workflows run this after the tests: a test must never leave a file in the repository,
# and least of all under evals/ (specs/001-corpus-and-audit/research.md, section 4).
#
#   bash .github/scripts/check-worktree.sh
#   bash .github/scripts/check-worktree.sh --allow-new-build-record
#   bash .github/scripts/check-worktree.sh --allow-new-question-sets
#   bash .github/scripts/check-worktree.sh --allow-new-build-record --allow-new-question-sets
#
# With --allow-new-build-record one kind of file may appear: a new evals/indexes/<index>/build.json,
# the build record of an index that this run built from the pinned dataset. A build record that
# existed before and was changed is still reported.
#
# With --allow-new-question-sets new files evals/golden/<version>.json may appear: the records of
# question sets that this run produced from the pinned dataset. The version has the form of an
# index identifier and at most 40 characters. A file under evals/golden/ that existed before and
# was changed is still reported, and so is a new file there with any other name.
#
# The two switches can be given together, in either order.
#
# Exit codes: 0 nothing unexpected, 1 a file was added or changed, 2 wrong arguments.

set -euo pipefail

allow_new_build_record=false
allow_new_question_sets=false
for argument in "$@"; do
  case "${argument}" in
    --allow-new-build-record) allow_new_build_record=true ;;
    --allow-new-question-sets) allow_new_question_sets=true ;;
    *)
      echo "usage: check-worktree.sh [--allow-new-build-record] [--allow-new-question-sets]" >&2
      exit 2
      ;;
  esac
done

# The identifier of an index: lower-case letters, digits and single hyphens.
new_build_record='^\?\? (evals/indexes/[a-z0-9]+(-[a-z0-9]+)*/build\.json)$'
# The version of a question set has the same form, and at most 40 characters.
new_question_set='^\?\? (evals/golden/([a-z0-9]+(-[a-z0-9]+)*)\.json)$'

changes="$(git status --porcelain --untracked-files=all)"

unexpected=""
allowed_build_record=""
allowed_question_sets=""
while IFS= read -r line; do
  [ -n "${line}" ] || continue
  if [ "${allow_new_build_record}" = true ] && [[ "${line}" =~ ${new_build_record} ]]; then
    echo "::notice title=new build record::${BASH_REMATCH[1]} is new: this run built that index."
    allowed_build_record="yes"
    continue
  fi
  if [ "${allow_new_question_sets}" = true ] && [[ "${line}" =~ ${new_question_set} ]] \
    && [ "${#BASH_REMATCH[2]}" -le 40 ]; then
    echo "::notice title=new question set::${BASH_REMATCH[1]} is new: this run produced that question set."
    allowed_question_sets="yes"
    continue
  fi
  unexpected+="${line}"$'\n'
done <<< "${changes}"

if [ -z "${unexpected}" ]; then
  if [ -n "${allowed_build_record}" ] && [ -n "${allowed_question_sets}" ]; then
    echo "Apart from the new build record and the new question sets, no file was added or changed outside the ignored folders."
  elif [ -n "${allowed_build_record}" ]; then
    echo "Apart from the new build record, no file was added or changed outside the ignored folders."
  elif [ -n "${allowed_question_sets}" ]; then
    echo "Apart from the new question sets, no file was added or changed outside the ignored folders."
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
