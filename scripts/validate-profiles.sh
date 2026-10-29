#!/usr/bin/env bash
# validate-profiles.sh — validate every profile against profiles/generic.json.
#
# profiles/README.md rule: every key exists in EVERY profile, with a neutral value
# where a project does not use it. This makes that rule a check (ADR-0001:
# executable, not prose). Asserts each *.json: parses; has every top-level key of
# generic.json; detection is a list of {file, contains?}; detection_priority is an
# int; stage_additions / stage_replacements keys are "<type>.<stage>"; every
# replacement has match + action.
#
# Usage: bash scripts/validate-profiles.sh [dir ...]   (default: profiles)
#        bash scripts/validate-profiles.sh profiles ~/.config/pipeline-skills/profiles
#        make validate-profiles
# Exit:  0 = all valid; 1 = at least one invalid.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot validate profiles"; exit 2; }
[ "$#" -eq 0 ] && set -- profiles

python3 - "$@" <<'PY'
import json, os, re, sys, glob

with open("profiles/generic.json") as f:
    required = set(json.load(f))

KEY = re.compile(r"^[a-z]+\.\d+$")
fail = False
checked = 0

for directory in sys.argv[1:]:
    directory = os.path.expanduser(directory)
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        checked += 1
        problems = []
        try:
            with open(path) as f:
                profile = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"✗ {path}: does not parse: {exc}")
            fail = True
            continue
        missing = sorted(required - set(profile))
        if missing:
            problems.append(f"missing keys {missing}")
        if profile.get("name") != os.path.splitext(os.path.basename(path))[0]:
            problems.append(f"name {profile.get('name')!r} differs from the file name")
        detection = profile.get("detection", [])
        if not isinstance(detection, list) or any(
                not isinstance(rule, dict) or not rule.get("file") for rule in detection):
            problems.append("detection must be a list of {file, contains?}")
        if not isinstance(profile.get("detection_priority", 0), int):
            problems.append("detection_priority must be an int")
        for field in ("stage_additions", "stage_replacements"):
            for key in profile.get(field, {}) or {}:
                if not KEY.match(key):
                    problems.append(f"{field} key {key!r} is not <type>.<stage>")
        for key, items in (profile.get("stage_replacements") or {}).items():
            for item in items:
                if not item.get("match") or not item.get("action"):
                    problems.append(f"stage_replacements {key}: each item needs match and action")
        if problems:
            fail = True
            for problem in problems:
                print(f"✗ {path}: {problem}")
        else:
            print(f"✓ {path}")

if checked == 0:
    print("✗ no profiles found")
    sys.exit(1)
sys.exit(1 if fail else 0)
PY
