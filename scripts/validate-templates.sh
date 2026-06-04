#!/usr/bin/env bash
# validate-templates.sh (v0.3.0) — validate every state-file template's structure.
#
# The pipeline-init skill describes a "template parse" verify step; this commits
# it as a runnable check (ADR-0001: executable, not prose). Asserts each
# templates/*.json: parses; has pipeline_type + stages; stage keys are "1".."N"
# contiguous and in order; each stage has name/status/verdict/checklist.
#
# Usage: bash scripts/validate-templates.sh [dir]   (default dir: templates)
#        make validate-templates
# Exit:  0 = all valid; 1 = at least one invalid.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

DIR="${1:-templates}"
command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot validate templates"; exit 2; }

python3 - "$DIR" <<'PY'
import json, sys, glob, os

dir_ = sys.argv[1]
files = sorted(glob.glob(os.path.join(dir_, "*.json")))
if not files:
    print(f"✗ no *.json templates found in {dir_}/")
    sys.exit(1)

REQUIRED_STAGE_KEYS = ("name", "status", "verdict", "checklist")
fail = False

for f in files:
    errs = []
    try:
        with open(f) as fh:
            d = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        print(f"✗ {f} — does not parse: {e}")
        fail = True
        continue

    if not isinstance(d, dict):
        print(f"✗ {f} — top-level JSON is {type(d).__name__}, expected an object")
        fail = True
        continue

    if "pipeline_type" not in d:
        errs.append("missing top-level 'pipeline_type'")
    stages = d.get("stages")
    if not isinstance(stages, dict) or not stages:
        errs.append("missing or empty 'stages' object")
        stages = {}

    # Stage keys must be numeric and strictly ascending. Gaps and fractional
    # sub-stages are allowed (e.g. retro uses 3.5 / 4.5 verification gates) — the
    # invariant is that the JSON-object order is a valid execution order.
    keys = list(stages.keys())
    try:
        nums = [float(k) for k in keys]
    except ValueError:
        errs.append(f"stage keys are not all numeric: {keys}")
        nums = []
    if nums:
        if nums[0] != 1:
            errs.append(f"first stage key should be '1', got '{keys[0]}'")
        if any(b <= a for a, b in zip(nums, nums[1:])):
            errs.append(f"stage keys not strictly ascending: {keys}")

    # Each stage has the required fields.
    for k, st in stages.items():
        if not isinstance(st, dict):
            errs.append(f"stage {k} is not an object")
            continue
        missing = [rk for rk in REQUIRED_STAGE_KEYS if rk not in st]
        if missing:
            errs.append(f"stage {k} ({st.get('name','?')}) missing: {', '.join(missing)}")

    if errs:
        fail = True
        print(f"✗ {f}")
        for e in errs:
            print(f"    - {e}")
    else:
        print(f"✓ {f} — {d.get('pipeline_type')} ({len(stages)} stages)")

sys.exit(1 if fail else 0)
PY
