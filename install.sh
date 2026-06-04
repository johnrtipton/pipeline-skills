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

# Install profiles alongside pipeline.py (they're resolved relative to pipeline.py)
echo ""
echo "Profiles installed at: ${SCRIPT_DIR}/profiles/"
ls "${SCRIPT_DIR}/profiles/"*.json 2>/dev/null | while read f; do
    echo "  $(basename "$f")"
done

echo ""
echo "Done. Skills available: /pipeline-init, /pipeline-next, /pipeline-run, /pipeline-ship, /pipeline-dev, /pipeline-retro, /pipeline-roadmap-audit, /pipeline-strategy, /pipeline-drain, pipeline-shared (reference)"
echo "Profiles: generic, django (auto-detected or set pipeline_profile in CLAUDE.md)"
