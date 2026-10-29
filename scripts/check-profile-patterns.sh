#!/usr/bin/env bash
# check-profile-patterns.sh — a profile's own security patterns and auto-reject
# triggers all reach the state file, ahead of the generic ones.
#
# load_profile once concatenated generic first and apply_profile kept the first 10,
# so a project profile with 10 patterns lost half of them from the Security Check
# item. This builds a ship state end to end (`pipeline.py ship --init-only`) in a
# throwaway project with a probe profile of 10 patterns and 10 triggers, plus a
# .pipeline/profile.json override, and asserts on the written state file: every
# pattern/trigger present exactly once, the most specific source first
# (override → profile → generic), in the stage-4 item and the auto-reject items.
#
# Usage: bash scripts/check-profile-patterns.sh   (or: make check-profile-patterns)
# Exit:  0 = pass; 1 = a pattern or trigger was lost, duplicated or out of order.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot check profile patterns"; exit 2; }
command -v git >/dev/null || { echo "✗ git not on PATH — cannot check profile patterns"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/profiles" "$TMP/project/.pipeline"
git -C "$TMP/project" init -q

python3 - "$TMP" <<'PY'
import json, sys
tmp = sys.argv[1]
with open("profiles/generic.json") as f:
    probe = json.load(f)
probe["name"] = "pattern-probe"
probe["description"] = "check-profile-patterns.sh probe"
probe["security_patterns"] = [f"probe security pattern {i}" for i in range(1, 11)]
probe["auto_reject_triggers"] = [f"probe auto-reject trigger {i}" for i in range(1, 11)]
with open(f"{tmp}/profiles/pattern-probe.json", "w") as f:
    json.dump(probe, f)
# A repo override: one new entry (must lead) and one repeat (must not duplicate).
with open(f"{tmp}/project/.pipeline/profile.json", "w") as f:
    json.dump({"security_patterns": ["override security pattern", "probe security pattern 3"],
               "auto_reject_triggers": ["override auto-reject trigger",
                                        "probe auto-reject trigger 3"]}, f)
PY

if ! out="$(PIPELINE_PROFILES_DIR="$TMP/profiles" python3 pipeline.py ship \
        --task "profile pattern probe" --project "$TMP/project" --profile pattern-probe \
        --branch probe/patterns --target-branch main --init-only --no-merge 2>&1)"; then
    echo "✗ pipeline.py ship --init-only failed:"
    echo "$out"
    exit 1
fi

python3 - "$TMP" <<'PY'
import json, sys
tmp = sys.argv[1]
with open("profiles/generic.json") as f:
    generic = json.load(f)
with open(f"{tmp}/project/.pipeline-state/probe-patterns.json") as f:
    state = json.load(f)

def expected(kind, label):
    # The override lists a new entry and profile entry 3: both lead, 3 only once.
    override = [f"override {label}", f"probe {label} 3"]
    own = [f"probe {label} {i}" for i in range(1, 11) if i != 3]
    return override + own + generic[kind]

def check(kind, label, prefix, stages):
    want = expected(kind, label)
    problems = []
    if state["profile_config"][kind] != want:
        problems.append(f"profile_config.{kind} is {state['profile_config'][kind]!r}")
    for num in stages:
        items = [i["action"] for i in state["stages"][num]["checklist"]
                 if i["action"].startswith(prefix)]
        if len(items) != 1:
            problems.append(f"stage {num}: {len(items)} items start with {prefix!r}")
            continue
        # Compare the whole line: a generic pattern itself contains ", ".
        if items[0] != prefix + ", ".join(want):
            lost = [p for p in want if p not in items[0]]
            problems.append(f"stage {num}: lost {lost}" if lost else
                            f"stage {num}: order/duplicates wrong: {items[0]!r}")
    for p in problems:
        print(f"✗ {kind}: {p}")
    if not problems:
        print(f"✓ {kind}: all {len(want)} in stage(s) {', '.join(stages)}, "
              f"override → profile → generic, no duplicates")
    return not problems

security_stage = [n for n, s in state["stages"].items() if s["name"] == "Security Check"]
reject_stages = [n for n, s in state["stages"].items()
                 if any(i["action"].startswith("check auto-reject triggers")
                        for i in s.get("checklist", []))]
ok = check("security_patterns", "security pattern", "scan changed files for: ", security_stage)
ok = check("auto_reject_triggers", "auto-reject trigger", "check auto-reject triggers: ",
           reject_stages) and ok
sys.exit(0 if ok else 1)
PY
