#!/bin/bash
# Install pipeline skills for OpenCode
# Usage: ./install-opencode.sh [--with-usai]
#
# This creates slash commands in ~/.config/opencode/commands/ that mirror
# the Claude Code /pipeline-* skills. Each command tells OpenCode to read
# the corresponding SKILL.md file and follow its instructions.
#
# Prerequisites:
#   - OpenCode installed (curl -fsSL https://opencode.ai/install | bash)
#   - git and gh CLI authenticated (gh auth status)
#
# Options:
#   --with-usai    Also configure the USAi (GSA) API provider in opencode.jsonc
#                  (you'll still need to set USAI_API_KEY in your shell profile)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="${HOME}/.claude/skills"
CMD_DIR="${HOME}/.config/opencode/commands"
CONFIG="${HOME}/.config/opencode/opencode.jsonc"

# --- Step 1: Install skill files (shared with Claude Code) ---
echo "Step 1: Installing skill files to ${SKILL_DIR}/"
mkdir -p "$SKILL_DIR"
for skill in "${SCRIPT_DIR}/skills/pipeline-"*; do
    name=$(basename "$skill")
    target="${SKILL_DIR}/${name}"
    rm -rf "$target"
    ln -sf "$skill" "$target"
    echo "  ✓ ${name}"
done

# --- Step 2: Create OpenCode commands ---
echo ""
echo "Step 2: Creating OpenCode commands in ${CMD_DIR}/"
mkdir -p "$CMD_DIR"

SKILLS=(
    "init:Initialize a repo for the pipeline system"
    "next:Pick the next task from ROADMAP.md"
    "run:Execute pipeline stages from the state file"
    "ship:Ship working-tree changes through quality gates"
    "dev:Fast iteration loop — branch, implement, push, merge"
    "strategy:Plan the next milestone via structured session"
    "retro:Run milestone retrospectives"
    "drain:Drain GitHub issues into milestone and process"
    "cycle:Outer loop — strategy, run --all, retro to terminal state"
)

for entry in "${SKILLS[@]}"; do
    name="${entry%%:*}"
    desc="${entry#*:}"
    file="${CMD_DIR}/pipeline-${name}.md"

    # pipeline-run and pipeline-ship also need pipeline-shared
    shared_line=""
    if [ "$name" = "run" ] || [ "$name" = "ship" ]; then
        shared_line="
Also read ${SKILL_DIR}/pipeline-shared/SKILL.md for the shared stage procedures referenced by the main skill."
    fi

    cat > "$file" <<EOF
---
description: ${desc}
agent: build
---

Read the file ${SKILL_DIR}/pipeline-${name}/SKILL.md in full — it contains the complete instructions for this command. Follow those instructions exactly.${shared_line}

Arguments from the user: \$ARGUMENTS
EOF
    echo "  ✓ /pipeline-${name} — ${desc}"
done

# --- Step 3: Set up permissions for skill file access ---
echo ""
echo "Step 3: Verifying OpenCode can read skill files..."
# OpenCode's build agent needs external_directory permission for the skill path.
# Check if it's already configured (it gets auto-added when opencode reads from the path).
echo "  ℹ  OpenCode will prompt to allow reading ${SKILL_DIR}/ on first use."
echo "     After approving once, it's remembered."

# --- Step 4 (optional): Configure USAi provider ---
if [ "$1" = "--with-usai" ]; then
    echo ""
    echo "Step 4: Configuring USAi provider in ${CONFIG}"

    # Only write if not already configured
    if grep -q '"usai"' "$CONFIG" 2>/dev/null; then
        echo "  ℹ  USAi provider already configured, skipping."
    else
        cat > "$CONFIG" <<'JSONC'
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "usai": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "GSA USAi",
      "options": {
        "baseURL": "https://api.gsa.usai.gov/api/v1",
        "apiKey": "{env:USAI_API_KEY}"
      },
      "models": {
        "claude_4_6_sonnet": {
          "name": "Claude 4.6 Sonnet (USAi)",
          "limit": { "context": 200000, "output": 65536 }
        },
        "claude_4_5_sonnet": {
          "name": "Claude 4.5 Sonnet (USAi)",
          "limit": { "context": 200000, "output": 65536 }
        },
        "claude_4_8_opus": {
          "name": "Claude 4.8 Opus (USAi)",
          "limit": { "context": 200000, "output": 65536 }
        },
        "claude_4_5_haiku": {
          "name": "Claude 4.5 Haiku (USAi)",
          "limit": { "context": 200000, "output": 65536 }
        },
        "gemini-2.5-flash": {
          "name": "Gemini 2.5 Flash (USAi)",
          "limit": { "context": 1000000, "output": 65536 }
        }
      }
    }
  }
}
JSONC
        echo "  ✓ USAi provider configured"
        echo ""
        echo "  ⚠  Add to your shell profile (~/.zshrc or ~/.bashrc):"
        echo "     export USAI_API_KEY='<client-id>:<client-secret>'"
    fi
fi

# --- Done ---
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Done! Pipeline skills installed for OpenCode."
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Usage (interactive TUI):"
echo "  cd ~/my-project"
echo "  opencode -m usai/claude_4_6_sonnet   # or any configured model"
echo "  /pipeline-init                        # one-time repo setup"
echo "  /pipeline-run --milestone v1.0        # execute from roadmap"
echo "  /pipeline-ship                        # ship working-tree changes"
echo ""
echo "Usage (headless via harness):"
echo "  python3 ${SCRIPT_DIR}/pipeline.py feature \\"
echo "    --task 'Add feature X' --project ~/my-project \\"
echo "    --agent opencode --agent-model usai/claude_4_6_sonnet"
echo ""
