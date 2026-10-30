#!/usr/bin/env bash
# check-review-state.sh — review_state.py's list and update commands, and init's
# default template.
#
# A reviewer who finds a recorded claim was wrong must correct it through the
# script, since nothing else may edit a review's state file. This builds a state
# file in a throwaway folder, adds claims, corrects one with `update`, and asserts
# that only the named fields of that one entry changed. Then it asserts that
# `update` and `list` refuse an unknown list name, an index out of range, an index
# that is not a number, JSON that is not an object and a wrong argument count, each
# with a message and a non-zero exit, and that a refused command leaves the file
# untouched.
#
# Usage: bash scripts/check-review-state.sh   (or: make check-review-state)
# Exit:  0 = pass; 1 = a command misbehaved.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot check review_state.py"; exit 2; }

RS="skills/pipeline-review/scripts/review_state.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STATE="$TMP/ws/state.json"
fail=0

# run <expected output substring> <command args...>: the command must succeed.
run() {
    local want="$1"; shift
    local out
    if ! out="$(python3 "$RS" "$@" 2>&1)"; then
        echo "✗ $* failed: $out"; fail=1; return
    fi
    if [[ "$out" != *"$want"* ]]; then
        echo "✗ $*: output lacks '$want': $out"; fail=1; return
    fi
    echo "✓ $1 ${*:3} → $want"
}

# refuse <expected message substring> <command args...>: non-zero exit, a message,
# and the state file byte for byte as it was.
refuse() {
    local want="$1"; shift
    local before out rc
    before="$(cat "$STATE")"
    out="$(python3 "$RS" "$@" 2>&1)"; rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "✗ $* was accepted; it should be refused"; fail=1
    elif [[ "$out" != *"$want"* ]]; then
        echo "✗ $*: message lacks '$want': $out"; fail=1
    elif [ "$(cat "$STATE")" != "$before" ]; then
        echo "✗ $*: refused but changed the state file"; fail=1
    else
        echo "✓ refused: $1 ${*:3} → $want"
    fi
}

# init without --template finds the clone's templates/review-state.json.
run "created" init "$STATE" --pr-url https://example.com/o/r/pull/1 --repo o/r --number 1
run "added claims[0]" add "$STATE" claims '{"claim": "nothing else reads X", "status": "VERIFIED", "evidence": "a.py:1"}'
run "added claims[1]" add "$STATE" claims '{"claim": "Y defaults to 5", "status": "VERIFIED", "evidence": "b.py:2"}'
run "[1] {\"claim\": \"Y defaults to 5\"" list "$STATE" claims
run "findings: 0" list "$STATE" findings
run "updated claims[1]" update "$STATE" claims 1 '{"status": "REFUTED", "evidence": "b.py:9 sets 3"}'

python3 - "$STATE" <<'PY' || fail=1
import json, sys
with open(sys.argv[1]) as f:
    state = json.load(f)
want = [
    {"claim": "nothing else reads X", "status": "VERIFIED", "evidence": "a.py:1"},
    {"claim": "Y defaults to 5", "status": "REFUTED", "evidence": "b.py:9 sets 3"},
]
if state.get("pipeline_type") != "review":
    print(f"✗ init did not build from review-state.json: pipeline_type={state.get('pipeline_type')!r}")
    sys.exit(1)
if state["claims"] != want:
    print(f"✗ update merged wrongly: claims are {state['claims']!r}")
    sys.exit(1)
print("✓ update changed only the named fields of claims[1]")
PY

refuse "claims or findings" update "$STATE" notes 0 '{"status": "REFUTED"}'
refuse "no claims[2]" update "$STATE" claims 2 '{"status": "REFUTED"}'
refuse "no claims[-1]" update "$STATE" claims -1 '{"status": "REFUTED"}'
refuse "whole number" update "$STATE" claims one '{"status": "REFUTED"}'
refuse "the list is empty" update "$STATE" findings 0 '{"severity": "Nit"}'
refuse "JSON object" update "$STATE" claims 0 '["REFUTED"]'
refuse "JSON object" update "$STATE" claims 0 'status=REFUTED'
refuse "usage:" update "$STATE" claims 0
refuse "claims or findings" list "$STATE" notes
refuse "usage:" list "$STATE"
refuse "JSON object" add "$STATE" findings '"just text"'

exit "$fail"
