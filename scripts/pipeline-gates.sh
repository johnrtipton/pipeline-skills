#!/usr/bin/env bash
# pipeline-gates.sh (#28, ADR-0001) — the pipeline-* quality gates as EXECUTABLE
# functions, not SKILL.md prose. One function per gate, parameterized by the
# detected default branch / test command, so the executor (and CI) run them
# context-independently instead of copy-pasting bash.
#
# Use as a library:   source scripts/pipeline-gates.sh; gate_retro_artifact 42
# Use from the CLI:   bash scripts/pipeline-gates.sh retro-artifact 42
#                     bash scripts/pipeline-gates.sh changelog-boundary HEAD
#                     bash scripts/pipeline-gates.sh docs-only HEAD
#                     bash scripts/pipeline-gates.sh premerge 42 .pipeline-state/<branch>.json
#                     bash scripts/pipeline-gates.sh pollution-runs "pytest -q"
#
# Each gate prints a one-line verdict and returns 0 (pass) or 1 (fail).
# Portable to bash 3.2 (macOS default) and BSD grep.
set -uo pipefail

# Gate 1 — an implementation (Stage 5) commit must NOT touch CHANGELOG.md
# (two-commit shape: code in commit 1, CHANGELOG/docs in commit 2).
gate_changelog_boundary() {
  local ref="${1:-HEAD}"
  if git show "$ref" --name-only --format= | grep -q '^CHANGELOG\.md$'; then
    echo "✗ gate:changelog-boundary — $ref touches CHANGELOG.md (move it to the docs commit)"
    return 1
  fi
  echo "✓ gate:changelog-boundary — $ref has no CHANGELOG.md"
}

# Gate 2 — the docs commit must contain ONLY documentation: any Markdown file
# (`*.md` anywhere — incl. skill SKILL.md, RETRO/ROADMAP/CHANGELOG/README), the
# docs/ tree, or .pipeline-templates/. Anything else (code, scripts, CI yaml)
# means implementation drift snuck into the docs commit.
gate_docs_only() {
  local ref="${1:-HEAD}"
  local non_docs
  non_docs=$(git show "$ref" --name-only --format= \
    | grep -vE '\.md$|^docs/|^\.pipeline-templates/' \
    | grep -v '^$' || true)
  if [ -n "$non_docs" ]; then
    echo "✗ gate:docs-only — $ref contains non-docs files:"
    echo "$non_docs" | sed 's/^/    /'
    return 1
  fi
  echo "✓ gate:docs-only — $ref is docs-only"
}

# Gate 3 — pollution-class fix must pass the test command 3 consecutive times.
gate_pollution_runs() {
  local test_cmd="${1:-}"
  if [ -z "$test_cmd" ]; then
    echo "• gate:pollution-runs — no test command (no suite); skipped"
    return 0
  fi
  local i
  for i in 1 2 3; do
    echo "=== pollution-class: run $i of 3: $test_cmd ==="
    if ! eval "$test_cmd"; then
      echo "✗ gate:pollution-runs — run $i failed; needs 3 consecutive clean runs"
      return 1
    fi
  done
  echo "✓ gate:pollution-runs — 3 consecutive clean runs"
}

# Gate 4 — the PR must carry a Retrospective artifact (comment or review).
gate_retro_artifact() {
  local pr="${1:-}"
  [ -z "$pr" ] && { echo "• gate:retro-artifact — no PR number; skipped"; return 0; }
  local n
  n=$(gh pr view "$pr" --json comments,reviews \
        -q '[.comments[].body, .reviews[].body] | join("\n")' 2>/dev/null \
      | grep -ic 'retrospective\|RETRO_COMPLETE\|quality:')
  if [ "${n:-0}" -ge 1 ]; then
    echo "✓ gate:retro-artifact — PR #$pr has a retrospective"
  else
    echo "✗ gate:retro-artifact — PR #$pr has no retrospective; run the Retrospective stage"
    return 1
  fi
}

# Pre-merge gate (pipeline-ship) — Code Review stage passed in the state file
# AND a code-review artifact exists on the PR.
gate_premerge() {
  local pr="${1:-}" state="${2:-}"
  [ -z "$pr" ] || [ -z "$state" ] && { echo "✗ gate:premerge — usage: gate_premerge <pr> <state-file>"; return 1; }
  [ -f "$state" ] || { echo "✗ gate:premerge — state file not found: $state"; return 1; }
  # Match the Code Review stage by NAME (numbering varies across templates).
  local cr_status
  cr_status=$(jq -r '.stages | to_entries[] | select(.value.name=="Code Review") | .value.status' "$state" 2>/dev/null | head -1)
  if [ "$cr_status" != "passed" ]; then
    echo "✗ gate:premerge — Code Review stage status='$cr_status' (not passed)"
    return 1
  fi
  local n
  n=$(gh pr view "$pr" --json comments,reviews \
        -q '[.comments[].body, .reviews[].body] | join("\n")' 2>/dev/null \
      | grep -ic 'code review\|REQUEST_CHANGES\|APPROVE')
  if [ "${n:-0}" -lt 1 ]; then
    echo "✗ gate:premerge — PR #$pr has no Code Review artifact"
    return 1
  fi
  echo "✓ gate:premerge — Code Review passed + artifact present on PR #$pr"
}

# Gate 6 — every COMPLETED drain bucket has a milestone retro entry in RETRO.md.
#
# Closes the hole `gate_retro_artifact` leaves open: that gate checks a PR, and a
# bucket is a milestone. A bucket can have every matrix row struck through (its
# issues all closed) and still never be retro'd — djust v1.2.0-6 found 14 such
# buckets, and #2140 was a *previous* backfill of the same kind, so the gap
# recurs rather than being a one-off.
#
# "Completed" is read from the ROADMAP's own matrix rows: a bucket counts as
# complete when it has at least one row and EVERY row carries a completion
# marker (strikethrough or the check emoji). Heading-level markers are NOT used —
# the drifted buckets never had one.
#
# KNOWN LIMITATION, measured against the case that motivated the gate: it found
# 6 of the 13 buckets its heuristic could see, but the drain actually had 14
# drifted buckets. The other 8 were completed WITHOUT striking their rows, so no
# static signal records them as done. That is a second-order finding, not a bug
# in the gate: a bucket whose completion nobody recorded is invisible to every
# reader, human or script. Striking the rows is part of marking a bucket done.
#
# Usage: bash scripts/pipeline-gates.sh retro-coverage [ROADMAP.md RETRO.md]
gate_retro_coverage() {
  local roadmap="${1:-ROADMAP.md}" retro="${2:-RETRO.md}"
  [ -f "$roadmap" ] || { echo "✗ gate:retro-coverage — $roadmap not found"; return 1; }
  [ -f "$retro" ]   || { echo "✗ gate:retro-coverage — $retro not found"; return 1; }
  local buckets=0 missing=0 name
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    buckets=$((buckets + 1))
    if ! grep -qE "^## ${name}([^0-9]|$)" "$retro"; then
      echo "  ✗ ${name}: complete in $roadmap, no entry in $retro"
      missing=$((missing + 1))
    fi
  done <<EOF
$(awk '
  /^#{2,3} v[0-9]/ { if (name != "" && rows > 0 && rows == done) print name; name=$2; rows=0; done=0; next }
  /^\|/ && /#[0-9][0-9][0-9]/ { rows++; if ($0 ~ /~~/ || $0 ~ /✅/) done++ }
  END { if (name != "" && rows > 0 && rows == done) print name }
' "$roadmap")
EOF
  if [ "$missing" -gt 0 ]; then
    echo "✗ gate:retro-coverage — ${missing} of ${buckets} completed bucket(s) have no retro entry; run /pipeline-retro"
    return 1
  fi
  echo "✓ gate:retro-coverage — all ${buckets} completed bucket(s) have a retro entry"
}

# CLI dispatch (only when executed, not when sourced).
if [ "${BASH_SOURCE[0]:-$0}" = "$0" ]; then
  cmd="${1:-}"; shift || true
  case "$cmd" in
    changelog-boundary) gate_changelog_boundary "$@" ;;
    docs-only)          gate_docs_only "$@" ;;
    pollution-runs)     gate_pollution_runs "$@" ;;
    retro-artifact)     gate_retro_artifact "$@" ;;
    premerge)           gate_premerge "$@" ;;
    retro-coverage)     gate_retro_coverage "$@" ;;
    *) echo "usage: $0 {changelog-boundary|docs-only|pollution-runs|retro-artifact|premerge|retro-coverage} [args]"; exit 2 ;;
  esac
fi
