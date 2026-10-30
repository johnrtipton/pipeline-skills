#!/usr/bin/env bash
# check-no-merge.sh — `--no-merge` skips the merge and nothing else.
#
# --no-merge once skipped the Retrospective too, so a draft PR finished its run
# with no retro on the PR or in .pipeline-log.md. This builds a ship state end to
# end (`pipeline.py ship --init-only`) in a throwaway project, with and without
# --no-merge, and asserts on the written state file: with it, Merge PR is skipped
# (skip_reason "--no-merge") and every other stage, the Retrospective included,
# is pending; without it, no stage is skipped.
#
# Usage: bash scripts/check-no-merge.sh   (or: make check-no-merge)
# Exit:  0 = pass; 1 = --no-merge skipped the wrong stages.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot check --no-merge"; exit 2; }
command -v git >/dev/null || { echo "✗ git not on PATH — cannot check --no-merge"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

for mode in no-merge merge; do
    project="$TMP/$mode"
    mkdir -p "$project" "$TMP/no-profiles"
    git -C "$project" init -q
    flag=""
    [ "$mode" = "no-merge" ] && flag="--no-merge"
    # An empty private-profile dir: the check reads only this repo's profiles/.
    # $flag stays unquoted so an empty one adds no argument (bash 3.2 has no
    # safe empty "${arr[@]}" under set -u).
    # shellcheck disable=SC2086
    if ! out="$(PIPELINE_PROFILES_DIR="$TMP/no-profiles" python3 pipeline.py ship \
            --task "no-merge probe" --project "$project" \
            --profile generic --branch "probe/$mode" --target-branch main \
            --init-only $flag 2>&1)"; then
        echo "✗ pipeline.py ship --init-only $flag failed:"
        echo "$out"
        exit 1
    fi
    python3 - "$project/.pipeline-state/probe-$mode.json" "$mode" <<'PY' || fail=1
import json, sys
path, mode = sys.argv[1], sys.argv[2]
with open(path) as f:
    state = json.load(f)
want_skipped = {"Merge PR"} if mode == "no-merge" else set()
problems = []
for num, stage in state["stages"].items():
    name, status = stage["name"], stage["status"]
    if name in want_skipped:
        if status != "skipped" or stage.get("skip_reason") != "--no-merge":
            problems.append(f"stage {num} {name}: {status}, want skipped by --no-merge")
    elif status != "pending":
        problems.append(f"stage {num} {name}: {status}, want pending")
if state.get("no_merge", False) != (mode == "no-merge"):
    problems.append(f"no_merge is {state.get('no_merge')!r}")
retro = [s for s in state["stages"].values() if s["name"] == "Retrospective"]
if len(retro) != 1:
    problems.append(f"{len(retro)} Retrospective stages")
elif "gh pr comment" not in retro[0].get("subagent_prompt", ""):
    problems.append("the Retrospective prompt does not post a PR comment")
for p in problems:
    print(f"✗ {mode}: {p}")
if not problems:
    skipped = ", ".join(sorted(want_skipped)) or "nothing"
    print(f"✓ {mode}: skips {skipped}; the Retrospective is pending and posts a PR comment")
sys.exit(1 if problems else 0)
PY
done

exit "$fail"
