#!/usr/bin/env bash
# substitute-pr-number.sh (#6) — replace `#TBD` PR placeholders with the real number.
#
# When a docs commit (ROADMAP/RETRO/CHANGELOG entry, PR body) must reference the
# PR it belongs to, the PR number isn't known until after `gh pr create`. Write
# the placeholder `#TBD` (or `PR #TBD`) up front, then run this once the PR
# exists to substitute the real number, and amend the commit.
#
# Usage:
#   bash scripts/substitute-pr-number.sh <PR-number> <file> [file ...]
#   (no files → lists candidate files containing `#TBD`, writes nothing)
# Then: git add -u && git commit --amend --no-edit && git push --force-with-lease
#
# Files are explicit by design: `#TBD` also appears as prose (roadmap/changelog
# entries describing the marker), which must NOT be rewritten.
#
# Portable to bash 3.2 / BSD sed (in-place via temp file, not `sed -i`).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

N="${1:-}"
case "$N" in
  ''|*[!0-9]*) echo "usage: $0 <PR-number> [file ...]   (PR-number must be digits)"; exit 2 ;;
esac
shift

# Target files must be given EXPLICITLY. Auto-writing every file containing
# `#TBD` is unsafe: the marker legitimately appears as prose (a ROADMAP entry
# describing this feature, a CHANGELOG note, this script's own docs) — those are
# not placeholders to fill. With no files, DISCOVER candidates (dry, no write)
# and exit non-zero so the caller picks the ones to substitute.
if [ "$#" -eq 0 ]; then
  echo "No files given — candidate tracked files containing \`#TBD\` (pass the real ones explicitly):"
  git grep -lF '#TBD' 2>/dev/null | sed 's/^/  /' || true
  echo "Re-run: $0 $N <file> [file ...]"
  exit 2
fi
files="$*"

if [ -z "$files" ]; then
  echo "• no \`#TBD\` placeholders found — nothing to substitute"
  exit 0
fi

changed=0
for f in $files; do
  [ -f "$f" ] || { echo "✗ not a file: $f"; continue; }
  if grep -qF '#TBD' "$f"; then
    tmp=$(mktemp)
    # One substitution covers both `PR #TBD` and bare `#TBD`.
    sed "s/#TBD/#$N/g" "$f" > "$tmp" && mv "$tmp" "$f"
    echo "✓ $f — #TBD → #$N"
    changed=$((changed + 1))
  fi
done

echo "substituted in $changed file(s). Now: git add -u && git commit --amend --no-edit && git push --force-with-lease"
