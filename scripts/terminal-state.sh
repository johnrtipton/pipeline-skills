#!/usr/bin/env bash
# terminal-state.sh (v0.7.0) — report whether the repo is at a CLEAN terminal
# state, the stop condition for /pipeline-cycle.
#
# CLEAN  = 0 open GitHub issues
#        + 0 active ROADMAP tasks (the parser finds none)
#        + no ADR left at "Proposed"
#        + latest CI run on the default branch is green (or no CI configured)
#
# Usage: bash scripts/terminal-state.sh   (or: make terminal-state)
# Exit:  0 = CLEAN; 1 = NOT clean (a condition failed). Advisory; prints each check.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

clean=0  # 0 = clean so far; set to 1 on any failed check

# 1. open issues
if command -v gh >/dev/null; then
  n=$(gh issue list --state open --json number -q 'length' 2>/dev/null || echo "?")
  if [ "$n" = "0" ]; then echo "✓ issues: 0 open"; else echo "✗ issues: $n open"; clean=1; fi
else
  echo "• issues: gh not on PATH — skipped"
fi

# 2. active ROADMAP tasks (run the real parser)
if command -v python3 >/dev/null && [ -f pipeline.py ]; then
  out=$(python3 pipeline.py auto --project . --list 2>/dev/null || true)
  # Clean = no tasks at all OR all tasks done (0 *remaining*). The parser prints
  # "N done, M remaining"; key off M, not the total "Found N tasks" count, so a
  # fully-shipped milestone (done tasks still listed) reads clean.
  rem=$(printf '%s' "$out" | sed -n 's/.*, \([0-9]*\) remaining.*/\1/p' | head -1)
  if printf '%s' "$out" | grep -qE 'No tasks match' || [ "${rem:-x}" = "0" ]; then
    echo "✓ roadmap: 0 active tasks"
  else
    echo "✗ roadmap: ${rem:-some} remaining task(s)"; clean=1
  fi
else
  echo "• roadmap: no python3/pipeline.py — skipped"
fi

# 3. no Proposed ADR
if ls docs/adr/*.md >/dev/null 2>&1; then
  prop=$(grep -lE '^\*\*Status\*\*:[[:space:]]*Proposed' docs/adr/*.md 2>/dev/null || true)
  if [ -z "$prop" ]; then echo "✓ ADRs: none Proposed"; else
    echo "✗ ADRs still Proposed:"; printf '%s\n' "$prop" | sed 's/^/    /'; clean=1
  fi
else
  echo "• ADRs: none — skipped"
fi

# 4. latest CI run green on the default branch
if command -v gh >/dev/null; then
  base=$(sed -n 's/^- *default_branch: *//p' CLAUDE.md 2>/dev/null | awk 'NR==1{print $1}')
  [ -z "$base" ] && base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
  [ -z "$base" ] && base=main
  concl=$(gh run list --branch "$base" --limit 1 --json conclusion -q '.[0].conclusion' 2>/dev/null || echo "")
  case "$concl" in
    success) echo "✓ CI: latest run on $base is green" ;;
    "")      echo "• CI: no runs found on $base — skipped" ;;
    *)       echo "✗ CI: latest run on $base is '$concl'"; clean=1 ;;
  esac
else
  echo "• CI: gh not on PATH — skipped"
fi

echo "---"
if [ "$clean" -eq 0 ]; then echo "TERMINAL_STATE: CLEAN"; else echo "TERMINAL_STATE: NOT_CLEAN"; fi
exit $clean
