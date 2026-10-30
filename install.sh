#!/bin/bash
# Install pipeline skills into Claude Code
# Usage: ./install.sh [--symlink]
#
# --symlink links each skill folder to this clone, so a `git pull` updates them.
# Without it, each skill folder is copied whole (scripts included), plus the repo
# files the skill reads at run time (runtime_files below), and pipeline.py with its
# templates/ and profiles/ goes to ~/.claude/skills/.pipeline-skill, so the copy
# works without the clone.

SKILL_DIR="${HOME}/.claude/skills"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Repo files a skill reads at run time, relative to the clone. A symlinked skill
# reaches them through the clone; a copied one gets them inside its own folder.
runtime_files() {
    case "$1" in
        pipeline-review) echo "templates/review-state.json" ;;
    esac
}

mkdir -p "$SKILL_DIR"
for skill in "${SCRIPT_DIR}/skills/pipeline-"*; do
    name=$(basename "$skill")
    target="${SKILL_DIR}/${name}"

    # Replace whatever is there: copying into an earlier symlink would write into the clone.
    rm -rf "$target"
    if [ "$1" = "--symlink" ]; then
        ln -sf "$skill" "$target"
        echo "Symlinked $name → $target"
    else
        cp -R "$skill" "$target"
        rm -rf "$target/scripts/__pycache__"
        for f in $(runtime_files "$name"); do
            mkdir -p "$target/$(dirname "$f")"
            cp "${SCRIPT_DIR}/$f" "$target/$f"
        done
        echo "Copied $name → $target"
    fi
done

# pipeline.py reads templates/ and profiles/ from its own folder. A symlinked skill
# finds all three in this clone; a copied one falls back to this copy (the
# PIPELINE_DIR lines in the SKILL.md files). Symlink mode removes a stale copy.
RUNTIME_DIR="${SKILL_DIR}/.pipeline-skill"
PIPELINE_HOME="$SCRIPT_DIR"
rm -rf "$RUNTIME_DIR"
if [ "$1" != "--symlink" ]; then
    mkdir -p "$RUNTIME_DIR"
    cp "${SCRIPT_DIR}/pipeline.py" "$RUNTIME_DIR/"
    cp -R "${SCRIPT_DIR}/templates" "${SCRIPT_DIR}/profiles" "$RUNTIME_DIR/"
    PIPELINE_HOME="$RUNTIME_DIR"
    echo "Copied pipeline.py, templates/, profiles/ → $RUNTIME_DIR"
fi

# Profiles are resolved relative to pipeline.py
echo ""
echo "Profiles installed at: ${PIPELINE_HOME}/profiles/"
ls "${PIPELINE_HOME}/profiles/"*.json 2>/dev/null | while read f; do
    echo "  $(basename "$f")"
done

echo ""
echo "Done. Skills available: /pipeline-init, /pipeline-next, /pipeline-run, /pipeline-ship, /pipeline-review, /pipeline-dev, /pipeline-retro, /pipeline-roadmap-audit, /pipeline-strategy, /pipeline-drain, /pipeline-cycle, pipeline-shared (reference)"
echo "Profiles: generic, django (auto-detected or set pipeline_profile in CLAUDE.md)"
