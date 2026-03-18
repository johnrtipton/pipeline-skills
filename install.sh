#!/bin/bash
# Install pipeline skills into Claude Code
# Usage: ./install.sh [--symlink]

SKILL_DIR="${HOME}/.claude/skills"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for skill in "${SCRIPT_DIR}/skills/pipeline-"*; do
    name=$(basename "$skill")
    target="${SKILL_DIR}/${name}"

    if [ "$1" = "--symlink" ]; then
        rm -rf "$target"
        ln -sf "$skill" "$target"
        echo "Symlinked $name → $target"
    else
        mkdir -p "$target"
        cp "$skill/SKILL.md" "$target/SKILL.md"
        echo "Copied $name → $target"
    fi
done

echo "Done. Skills available: /pipeline-feature, /pipeline-bugfix, /pipeline-refactor"
