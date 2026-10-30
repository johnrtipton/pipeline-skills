#!/usr/bin/env bash
# check-install.sh — both install modes give /pipeline-review a working script and
# template.
#
# Copy mode once copied only SKILL.md and PURPOSE.md, so a copied pipeline-review
# had no scripts/review_state.py, and the path line in its SKILL.md resolved to
# ~/.claude, where no template lives. This runs install.sh into a throwaway HOME in
# copy mode, in symlink mode, and in copy mode over an earlier symlink install;
# evaluates the SKILL_HOME line exactly as SKILL.md writes it; and runs
# `review_state.py init` without --template, which must find review-state.json.
# It also checks the line with PIPELINE_SKILL_DIR pointing at this clone.
#
# Usage: bash scripts/check-install.sh   (or: make check-install)
# Exit:  0 = pass; 1 = an install mode left the skill unable to start a review.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
REPO="$(pwd -P)"

command -v python3 >/dev/null || { echo "✗ python3 not on PATH — cannot check install.sh"; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
LINE="$(grep -m1 '^SKILL_HOME=' skills/pipeline-review/SKILL.md)"
[ -n "$LINE" ] || { echo "✗ no SKILL_HOME= line in skills/pipeline-review/SKILL.md"; exit 1; }
fail=0

# start_review <label> <home> [PIPELINE_SKILL_DIR]: resolve the skill as SKILL.md
# does, then init a review with no --template. Prints the resolved SKILL_HOME;
# on a failure, says why on stderr and returns 1 (it runs in a subshell).
start_review() {
    local label="$1" home="$2" dir="${3:-}" skill_home out
    skill_home="$(env -u PIPELINE_SKILL_DIR HOME="$home" ${dir:+PIPELINE_SKILL_DIR="$dir"} \
        bash -c "$LINE"' && printf %s "$SKILL_HOME"')"
    if [ ! -f "$skill_home/scripts/review_state.py" ]; then
        echo "✗ $label: no review_state.py under SKILL_HOME=$skill_home" >&2; return 1
    fi
    if ! out="$(python3 "$skill_home/scripts/review_state.py" init "$home/ws-$label/state.json" \
            --pr-url https://example.com/o/r/pull/1 --repo o/r --number 1 2>&1)"; then
        echo "✗ $label: init without --template failed: $out" >&2; return 1
    fi
    if ! grep -q '"pipeline_type": "review"' "$home/ws-$label/state.json"; then
        echo "✗ $label: init did not build the state file from review-state.json" >&2; return 1
    fi
    printf %s "$skill_home"
}

run_install() {
    HOME="$1" bash install.sh ${2:+"$2"} >/dev/null 2>&1 || { echo "✗ install.sh ${2:-} failed"; fail=1; }
}

# Copy mode: a real folder with the scripts and the template inside it.
run_install "$TMP/copy"
target="$TMP/copy/.claude/skills/pipeline-review"
if [ -L "$target" ] || [ ! -d "$target" ]; then
    echo "✗ copy: $target is not a real folder"; fail=1
elif ! cmp -s templates/review-state.json "$target/templates/review-state.json"; then
    echo "✗ copy: templates/review-state.json missing from or different in $target"; fail=1
elif home="$(start_review copy "$TMP/copy")"; then
    [ "$home" = "$(cd "$target" && pwd -P)" ] \
        && echo "✓ copy: SKILL_HOME is the copied folder; script and template found" \
        || { echo "✗ copy: SKILL_HOME is $home, not the copied folder"; fail=1; }
else
    fail=1
fi
missing="$(cd skills && for f in $(find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc'); do
    [ -f "$TMP/copy/.claude/skills/$f" ] || echo "$f"; done)"
[ -z "$missing" ] && echo "✓ copy: every file of every skill folder was copied" \
    || { echo "✗ copy: not copied: $missing"; fail=1; }

# Symlink mode: a link to this clone's skill folder; the template comes from the clone.
run_install "$TMP/link" --symlink
target="$TMP/link/.claude/skills/pipeline-review"
if [ ! -L "$target" ]; then
    echo "✗ symlink: $target is not a symlink"; fail=1
elif home="$(start_review symlink "$TMP/link")"; then
    [ "$home" = "$REPO/skills/pipeline-review" ] \
        && echo "✓ symlink: SKILL_HOME is the clone's folder; script and template found" \
        || { echo "✗ symlink: SKILL_HOME is $home, not $REPO/skills/pipeline-review"; fail=1; }
else
    fail=1
fi

# Copy over an earlier symlink install: the link is replaced, and nothing is
# written into the clone through it.
clone_before="$(find skills | sort)"
run_install "$TMP/link"
if [ -L "$target" ] || [ ! -f "$target/templates/review-state.json" ]; then
    echo "✗ copy over symlink: $target is still a link or lacks its template"; fail=1
elif [ "$(find skills | sort)" != "$clone_before" ]; then
    echo "✗ copy over symlink: install.sh wrote into the clone's skills/pipeline-review"; fail=1
else
    echo "✓ copy over symlink: replaced the link; the clone is untouched"
fi

# PIPELINE_SKILL_DIR names a clone: SKILL_HOME is that clone's folder, whatever HOME holds.
mkdir -p "$TMP/empty"
if home="$(start_review env "$TMP/empty" "$REPO")"; then
    [ "$home" = "$REPO/skills/pipeline-review" ] \
        && echo "✓ PIPELINE_SKILL_DIR: SKILL_HOME is that clone's folder; script and template found" \
        || { echo "✗ PIPELINE_SKILL_DIR: SKILL_HOME is $home"; fail=1; }
else
    fail=1
fi

exit "$fail"
