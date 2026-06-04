#!/usr/bin/env bash
# check-issue-symbols.sh (#7) — pre-drain staleness check.
#
# Before /pipeline-drain queues a GitHub issue into the ROADMAP, verify the code
# symbols and file paths the issue body cites still exist in the codebase. An
# issue that references removed code is stale — queuing it wastes a pipeline run.
#
# Usage: bash scripts/check-issue-symbols.sh <issue-number> [<issue-number> ...]
# Exit:  0 = all cited symbols found (or none cited); 1 = at least one missing.
#        Advisory: a miss means "review before queuing", not "always drop".
#
# Portable to bash 3.2 (macOS default) and BSD grep/sed — no mapfile, no arrays.
set -uo pipefail
cd "$(dirname "$0")/.."

command -v gh >/dev/null || { echo "NOTE: gh not on PATH — cannot fetch issues, skipping"; exit 0; }

overall=0
for issue in "$@"; do
  body=$(gh issue view "$issue" --json body -q .body 2>/dev/null) || {
    echo "✗ #$issue — could not fetch (closed/missing?)"; overall=1; continue; }

  # Extract backtick-wrapped tokens that look like code: file paths (contain a
  # dot-extension) or function calls (end in "(" or "()"). Conceptual phrases
  # are ignored — only greppable code-ish tokens are checked.
  toks=$(printf '%s\n' "$body" \
    | grep -oE '`[^`]+`' \
    | sed 's/`//g' \
    | grep -oE '[A-Za-z0-9_./-]+\.[A-Za-z0-9_]+|[A-Za-z_][A-Za-z0-9_]*\(\)?' \
    | sed 's/[()]*$//' \
    | grep -vE '^(e\.g|i\.e|etc|vs|origin/(main|master))$' \
    | sort -u || true)

  if [ -z "$toks" ]; then
    echo "• #$issue — no greppable symbols cited (ok)"
    continue
  fi

  missing=""
  count=0
  while IFS= read -r t; do
    [ -z "$t" ] && continue
    count=$((count + 1))
    if printf '%s' "$t" | grep -q '/'; then
      # looks like a file path → test it exists
      [ -e "$t" ] || missing="$missing $t"
    else
      grep -rqF --exclude-dir=.git "$t" . 2>/dev/null || missing="$missing $t"
    fi
  done <<EOF
$toks
EOF

  if [ -z "$missing" ]; then
    echo "✓ #$issue — all $count cited symbols present"
  else
    echo "⚠ #$issue — cited symbols NOT found (possibly stale):$missing"
    overall=1
  fi
done
exit $overall
