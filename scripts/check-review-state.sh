#!/usr/bin/env bash
# check-review-state.sh — review_state.py's list, update and round commands, and
# init's default template.
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
# A re-review after the author answers a finished review goes through `round`. The
# check asserts that it refuses while a stage is open, without a reviewed head, with
# an unknown option, without a state file, and over an archive that is not the
# round being closed; that it archives the round to rounds/<n>.json and carries the
# head, review URL, verdict and still-open findings (recheck PENDING) into the next;
# and that `done` refuses Verify Claims while a carried finding is unchecked.
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

# --- round: a re-review after the author answers a finished review -------------
# A first review starts with every re_review item ticked; nothing came before it.
python3 - "$STATE" <<'PY' || fail=1
import json, sys
with open(sys.argv[1]) as f:
    state = json.load(f)
items = [i for s in state["stages"].values() for i in s["checklist"] if i.get("re_review")]
if not items or not all(i["done"] for i in items):
    print(f"✗ init left re_review items open: {[i['action'][:40] for i in items if not i['done']]}")
    sys.exit(1)
if state.get("round") != 1:
    print(f"✗ init did not start round 1: round={state.get('round')!r}")
    sys.exit(1)
print(f"✓ init ticks the {len(items)} re_review items of a first review")
PY

refuse "stages still open in this round: 1 (Intake, pending)" round "$STATE"
for stage in 1 2 3 4 5 6 7 8 9; do python3 "$RS" skip "$STATE" "$stage" "check" >/dev/null || fail=1; done
refuse "no head_sha_reviewed" round "$STATE"
refuse "unknown or incomplete option" round "$STATE" --tempalte x.json
refuse "no state file at" round "$TMP/ws/missing.json"
run "" set "$STATE" head_sha_reviewed=aaa111 posted_review_url=https://example.com/o/r/pull/1#review-1 review_verdict=REQUEST_CHANGES
run "added findings[0]" add "$STATE" findings '{"severity": "Must", "title": "the job lacks the new setting", "evidence": "a.py:1"}'
run "added findings[1]" add "$STATE" findings '{"severity": "Nit", "title": "typo", "recheck_evidence": "stale"}'
run "added findings[2]" add "$STATE" findings '{"severity": "Should", "title": "fixed earlier", "recheck": "RESOLVED"}'
run "added findings[3]" add "$STATE" findings '{"severity": "Should", "title": "was wrong", "recheck": "WITHDRAWN"}'
cp "$STATE" "$TMP/round1.json"
run "with 2 findings to recheck" round "$STATE" --no-post

python3 - "$STATE" "$TMP/round1.json" "$TMP/ws/rounds/1.json" <<'PY' || fail=1
import json, sys
load = lambda p: json.load(open(p))
state, before, archive = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
errs = []
if archive != before:
    errs.append("rounds/1.json is not the finished round as it was")
want = {"round": 2, "previous_head": "aaa111", "previous_verdict": "REQUEST_CHANGES",
        "previous_review_url": "https://example.com/o/r/pull/1#review-1", "head_sha_reviewed": "",
        "repo": "o/r", "pr_number": 1, "post_mode": "none", "claims": [], "completed_at": None}
errs += [f"{k}={state.get(k)!r}, want {v!r}" for k, v in want.items() if state.get(k) != v]
if state.get("rounds") != [{"round": 1, "state": "rounds/1.json", "head": "aaa111",
                            "verdict": "REQUEST_CHANGES",
                            "review_url": "https://example.com/o/r/pull/1#review-1"}]:
    errs.append(f"rounds={state.get('rounds')!r}")
if state.get("findings") != [
    {"severity": "Must", "title": "the job lacks the new setting", "evidence": "a.py:1", "round": 1, "recheck": "PENDING"},
    {"severity": "Nit", "title": "typo", "round": 1, "recheck": "PENDING"},
]:
    errs.append(f"findings={state.get('findings')!r} (want the two still open, recheck PENDING)")
if any(s["status"] != "pending" for s in state["stages"].values()):
    errs.append("the new round does not start with every stage pending")
reopened = [i for s in state["stages"].values() for i in s["checklist"] if i.get("re_review")]
if not reopened or any(i["done"] for i in reopened):
    errs.append("the new round's re_review items are not open")
if errs:
    print("✗ round built the next round wrongly:\n    " + "\n    ".join(errs))
    sys.exit(1)
print("✓ round archived round 1 and carried its head, review and open findings into round 2")
PY
run "findings to recheck against the new commits: [0, 1]" status "$STATE"

# Verify Claims cannot close while a carried finding is unchecked, even with every item ticked.
for stage in 1 2 3; do python3 "$RS" skip "$STATE" "$stage" "check" >/dev/null || fail=1; done
ITEMS="$(python3 -c 'import json,sys; print(*range(len(json.load(open(sys.argv[1]))["stages"]["4"]["checklist"])))' "$STATE")"
# shellcheck disable=SC2086
python3 "$RS" tick "$STATE" 4 $ITEMS || fail=1
refuse "findings [0, 1] from the last round" done "$STATE" 4 CLAIMS_CHECKED
run "updated findings[0]" update "$STATE" findings 0 '{"recheck": "RESOLVED", "recheck_evidence": "a.py:4 at the new head"}'
refuse "findings [1] from the last round" done "$STATE" 4 CLAIMS_CHECKED
run "updated findings[1]" update "$STATE" findings 1 '{"recheck": "OPEN"}'
run "stage 4 CLAIMS_CHECKED" done "$STATE" 4 CLAIMS_CHECKED
refuse "stages still open in this round: 5 (Consequences, pending)" round "$STATE"

# Round 3 carries only what is still open, keeps the round a finding was raised in,
# and refuses to overwrite an archive that is not the round being closed.
for stage in 5 6 7 8 9; do python3 "$RS" skip "$STATE" "$stage" "check" >/dev/null || fail=1; done
run "" set "$STATE" head_sha_reviewed=bbb222
run "added findings[2]" add "$STATE" findings '{"severity": "Should", "title": "new in round 2"}'
cp "$TMP/round1.json" "$TMP/ws/rounds/2.json"
refuse "exists and is not this round" round "$STATE"
# The same round already there is a rerun after a crash between the two writes: carry on.
cp "$STATE" "$TMP/ws/rounds/2.json"
run "with 2 findings to recheck" round "$STATE"
python3 - "$STATE" <<'PY' || fail=1
import json, sys
state = json.load(open(sys.argv[1]))
got = [(f["title"], f["round"], f["recheck"]) for f in state["findings"]]
want = [("typo", 1, "PENDING"), ("new in round 2", 2, "PENDING")]
if state["round"] != 3 or state["previous_head"] != "bbb222" or got != want:
    print(f"✗ round 3 is wrong: round={state['round']} previous_head={state['previous_head']} findings={got}")
    sys.exit(1)
if [r["round"] for r in state["rounds"]] != [1, 2] or state["post_mode"] != "ask":
    print(f"✗ round 3 lost the history or kept --no-post: {state['rounds']} post_mode={state['post_mode']}")
    sys.exit(1)
print("✓ round 3 carries only the open findings, each with the round that raised it")
PY

exit "$fail"
