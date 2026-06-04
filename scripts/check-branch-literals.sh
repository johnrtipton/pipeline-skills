#!/usr/bin/env bash
# check-branch-literals.sh (#18) — guard against reintroduced hard-coded
# default-branch literals in skill execution paths or pipeline.py.
#
# The whole pipeline-* family resolves the default branch dynamically
# (pipeline-config default_branch -> origin/HEAD -> git remote show -> fallback).
# This check fails if a literal `main`/`master` sneaks back into an actual git
# COMMAND or a pipeline.py branch-naming literal. It deliberately ignores
# backtick-wrapped prose (docs may discuss `origin/main` as an anti-pattern) and
# the documented `BASE=...main` fallback assignment.
#
# Usage: bash scripts/check-branch-literals.sh   (or: make check)
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0

# --- skills: literal git commands that should use "$BASE" ---
# Match real commands (push/pull/checkout/diff/rev-parse) against a literal
# main|master; exclude any line referencing $BASE (the parameterized form and
# the BASE=...main fallback both legitimately contain "main").
#
# #29: a prose mention wrapped in inline code — e.g. `git diff origin/main` —
# must NOT trip the guard, but a real command in a fenced bash block must. So we
# STRIP inline-code spans (backtick-delimited) from each candidate line before
# the final decision: fenced-block commands aren't single-backtick-wrapped and
# survive the strip; inline-code prose disappears.
PATTERN='git (push|pull) origin (main|master)\b|git checkout (main|master)\b|checkout -B [^ ]+ origin/(main|master)\b|git (diff|rev-parse)[^`]*origin/(main|master)\b'
raw=$(grep -rnE "$PATTERN" skills/*/SKILL.md 2>/dev/null | grep -v 'BASE' || true)
skill_hits=""
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  content="${hit#*:*:}"                                   # strip "file:lineno:" prefix
  stripped=$(printf '%s' "$content" | sed 's/`[^`]*`//g') # drop inline-code spans
  if printf '%s' "$stripped" | grep -qE "$PATTERN"; then
    skill_hits="${skill_hits}${hit}"$'\n'
  fi
done <<EOF
$raw
EOF
if [ -n "$(printf '%s' "$skill_hits" | tr -d '[:space:]')" ]; then
  echo "✗ Hard-coded default branch in skill command (use \"\$BASE\"):"
  printf '%s' "$skill_hits" | sed '/^$/d; s/^/    /'
  fail=1
fi

# --- pipeline.py: branch-naming literals (ternary fallback / origin string) ---
# Allows the last-resort `return "main"` in detect_default_branch and the
# user-overridable argparse `default="main"`; flags `else "main"` naming and
# any `"origin/main"` string literal.
py_hits=$(grep -nE 'else[[:space:]]+"(main|master)"|"origin/(main|master)"' pipeline.py 2>/dev/null || true)
if [ -n "$py_hits" ]; then
  echo "✗ Hard-coded branch literal in pipeline.py (resolve via detect_default_branch):"
  echo "$py_hits" | sed 's/^/    /'
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "✓ no reintroduced default-branch literals"
fi
exit $fail
