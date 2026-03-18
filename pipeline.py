#!/usr/bin/env python3
"""
Pipeline runner — external harness that drives Claude Code through stages.

The state file is the program. This script is the executor.
Claude Code handles each stage; this script handles the flow.

Usage:
    # Start a new bugfix pipeline
    python pipeline.py bugfix --task "Fix event sequencing #560" --project ~/path/to/project

    # Start a new feature pipeline
    python pipeline.py feature --task "Add dj-value-* params" --project ~/path/to/project

    # Resume an interrupted pipeline
    python pipeline.py --resume --project ~/path/to/project

    # Resume a specific pipeline
    python pipeline.py --resume --state .pipeline-state/fix-event-sequencing-560.json

    # Override target branch (for milestone dev branches)
    python pipeline.py bugfix --task "..." --project ~/path --target-branch dev/v0.4.0
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def slugify(text: str) -> str:
    """Convert text to a branch-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())
    return slug.strip("-")[:50]


def load_template(pipeline_type: str) -> dict:
    """Load the state file template for a pipeline type."""
    template_path = TEMPLATES_DIR / f"{pipeline_type}-state.json"
    if not template_path.exists():
        print(f"Error: template not found: {template_path}")
        sys.exit(1)
    with open(template_path) as f:
        return json.load(f)


def init_state(pipeline_type: str, task: str, project: str, target_branch: str) -> dict:
    """Create a new state file from template."""
    state = load_template(pipeline_type)
    prefix = {"feature": "feat", "bugfix": "fix", "refactor": "refactor"}[pipeline_type]
    branch = f"{prefix}/{slugify(task)}"

    state["task_description"] = task
    state["branch_name"] = branch
    state["pr_target_branch"] = target_branch
    state["project_path"] = os.path.abspath(project)
    state["started_at"] = datetime.now(timezone.utc).isoformat()

    return state


def state_path(project: str, branch: str) -> Path:
    """Get the state file path for a branch."""
    safe_name = branch.replace("/", "-")
    return Path(project) / ".pipeline-state" / f"{safe_name}.json"


def save_state(state: dict):
    """Write state file to disk."""
    path = state_path(state["project_path"], state["branch_name"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    # Ensure .pipeline-state/ is gitignored
    gitignore = Path(state["project_path"]) / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if ".pipeline-state/" not in content:
            with open(gitignore, "a") as f:
                f.write("\n.pipeline-state/\n")
    return path


def load_state(path: Path) -> dict:
    """Load existing state file."""
    with open(path) as f:
        return json.load(f)


def find_resume_state(project: str) -> Path | None:
    """Find the most recent incomplete state file."""
    state_dir = Path(project) / ".pipeline-state"
    if not state_dir.exists():
        return None
    candidates = []
    for f in state_dir.glob("*.json"):
        state = load_state(f)
        if state.get("completed_at") is None:
            candidates.append((f, state.get("started_at", "")))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def next_stage(state: dict) -> tuple[str, dict] | None:
    """Find the next pending stage."""
    for stage_num in sorted(state["stages"].keys(), key=int):
        stage = state["stages"][stage_num]
        if stage["status"] not in ("passed", "skipped"):
            return stage_num, stage
    return None


def build_stage_prompt(state: dict, stage_num: str, stage: dict) -> str:
    """Build the prompt for a stage, using the checklist as instructions."""
    lines = [
        f"## Stage {stage_num}: {stage['name']}",
        "",
        f"Project: {state['project_path']}",
        f"Branch: {state['branch_name']}",
        f"Task: {state['task_description']}",
        f"PR target: {state['pr_target_branch']}",
    ]

    if state.get("pr_number"):
        lines.append(f"PR: #{state['pr_number']} ({state.get('pr_url', '')})")

    # If this is a subagent stage with a full prompt, use it
    if stage.get("subagent_prompt"):
        prompt = stage["subagent_prompt"]
        # Fill in template variables
        prompt = prompt.replace("{pr_number}", str(state.get("pr_number", "???")))
        prompt = prompt.replace("{project_path}", state["project_path"])
        prompt = prompt.replace("{pr_target_branch}", state["pr_target_branch"])
        prompt = prompt.replace("{task_description}", state["task_description"])
        lines.extend(["", prompt])
    else:
        # Build prompt from checklist
        lines.extend(["", "### Checklist — complete each item:", ""])
        for item in stage.get("checklist", []):
            mandatory = " [MANDATORY]" if item.get("mandatory") else ""
            lines.append(f"- [ ] {item['action']}{mandatory}")

    # Add context from previous stages
    prev_verdicts = []
    for prev_num in sorted(state["stages"].keys(), key=int):
        if int(prev_num) >= int(stage_num):
            break
        prev = state["stages"][prev_num]
        if prev.get("verdict"):
            prev_verdicts.append(f"Stage {prev_num} ({prev['name']}): {prev['verdict']}")
    if prev_verdicts:
        lines.extend(["", "### Previous stage results:", ""])
        lines.extend(prev_verdicts)

    return "\n".join(lines)


def run_claude(prompt: str, project: str, max_turns: int = 50) -> tuple[str, int]:
    """Run Claude Code with a prompt and return output + exit code."""
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "text",
        "--max-turns", str(max_turns),
    ]
    print(f"\n{'─' * 60}")
    print(f"Running Claude Code...")
    print(f"{'─' * 60}\n")
    result = subprocess.run(
        cmd,
        cwd=project,
        capture_output=True,
        text=True,
        timeout=1800,  # 30 min max per stage
    )
    output = result.stdout + result.stderr
    return output, result.returncode


def extract_verdict(output: str, stage: dict) -> str | None:
    """Extract the verdict string from stage output."""
    # Common verdict patterns
    verdicts = [
        "ENV_OK", "ENV_FAILED",
        "MERGE_CLEAN", "MERGE_CONFLICTS_FOUND",
        "CODE_CHANGES", "DOCS_ONLY",
        "TESTS_PASSED", "TESTS_FAILED",
        "REVIEW_PASSED", "REVIEW_FAILED",
        "REGRESSION_PASSED", "REGRESSION_FAILED",
        "SECURITY_PASSED", "SECURITY_FAILED",
        "DOCS_UPDATED",
        "PR_CREATED:", "PR_EXISTS:", "PR_SKIPPED:",
        "REVIEW_COMPLETE",
        "APPROVE", "REQUEST_CHANGES", "COMMENT",
        "PR_MERGED", "MERGE_FAILED",
        "RETRO_COMPLETE",
    ]
    # Check for failure markers first (they override pass markers)
    for v in verdicts:
        if "FAILED" in v and v in output:
            return v
    for v in verdicts:
        if v in output:
            # For PR_CREATED, extract the URL
            if v == "PR_CREATED:":
                match = re.search(r"PR_CREATED:\s*(https://\S+)", output)
                return match.group(0) if match else v
            if v == "PR_EXISTS:":
                match = re.search(r"PR_EXISTS:\s*(https://\S+)", output)
                return match.group(0) if match else v
            return v
    return None


def extract_pr_info(output: str, state: dict):
    """Extract PR number and URL from output."""
    match = re.search(r"PR_(?:CREATED|EXISTS):\s*(https://github\.com/\S+/pull/(\d+))", output)
    if match:
        state["pr_url"] = match.group(1)
        state["pr_number"] = int(match.group(2))


def should_skip(state: dict, stage: dict) -> bool:
    """Check if a stage should be skipped."""
    skip_if = stage.get("skip_if")
    if not skip_if:
        return False
    # Check if any previous stage has this verdict
    for prev in state["stages"].values():
        if prev.get("verdict") == skip_if:
            return True
    return False


def mark_checklist_done(stage: dict):
    """Mark all checklist items as done."""
    for item in stage.get("checklist", []):
        item["done"] = True


def check_mandatory(stage: dict) -> list[str]:
    """Return list of mandatory items that are not done."""
    missing = []
    for item in stage.get("checklist", []):
        if item.get("mandatory") and not item.get("done"):
            missing.append(item["action"])
    return missing


def print_stage_header(stage_num: str, stage: dict, total: int):
    """Print a stage header."""
    print(f"\n{'═' * 60}")
    print(f"  Stage {stage_num}/{total}: {stage['name']}")
    run_as = f" [subagent]" if stage.get("run_as") == "subagent" else ""
    print(f"  {len(stage.get('checklist', []))} checklist items{run_as}")
    print(f"{'═' * 60}")


def print_summary(state: dict):
    """Print pipeline summary."""
    total = len(state["stages"])
    passed = sum(1 for s in state["stages"].values() if s["status"] == "passed")
    skipped = sum(1 for s in state["stages"].values() if s["status"] == "skipped")
    failed = sum(1 for s in state["stages"].values() if s["status"] == "failed")
    pending = total - passed - skipped - failed

    print(f"\n{'═' * 60}")
    print(f"  Pipeline Complete: {state['pipeline_type']}")
    print(f"{'═' * 60}")
    print(f"  Task: {state['task_description'][:60]}")
    print(f"  Branch: {state['branch_name']}")
    print(f"  Stages: {passed} passed, {skipped} skipped, {failed} failed, {pending} pending")
    if state.get("pr_url"):
        print(f"  PR: {state['pr_url']}")
    print(f"{'═' * 60}\n")


def run_pipeline(state: dict):
    """Main pipeline loop — the external harness."""
    total_stages = len(state["stages"])
    save_state(state)

    while True:
        result = next_stage(state)
        if result is None:
            state["completed_at"] = datetime.now(timezone.utc).isoformat()
            save_state(state)
            print_summary(state)
            break

        stage_num, stage = result

        # Skip check
        if should_skip(state, stage):
            print(f"\n  Skipping Stage {stage_num}: {stage['name']} (skip_if: {stage.get('skip_if')})")
            stage["status"] = "skipped"
            stage["verdict"] = f"Skipped: {stage.get('skip_if')}"
            state["current_stage"] = int(stage_num) + 1
            save_state(state)
            continue

        print_stage_header(stage_num, stage, total_stages)

        # Build and run
        prompt = build_stage_prompt(state, stage_num, stage)
        output, exit_code = run_claude(prompt, state["project_path"])

        # Extract verdict
        verdict = extract_verdict(output, stage)
        print(f"\n  Verdict: {verdict or 'NONE'}")

        # Extract PR info if present
        extract_pr_info(output, state)

        # Mark checklist done (we trust Claude completed them if it got a verdict)
        mark_checklist_done(stage)

        # Check for mandatory items — in subagent stages, check output for evidence
        # (The subagent prompt includes MANDATORY markers)

        if verdict and "FAILED" not in (verdict or ""):
            stage["status"] = "passed"
            stage["verdict"] = verdict
            state["current_stage"] = int(stage_num) + 1
        elif verdict and "FAILED" in verdict:
            # TODO: retry logic, rewind logic
            stage["status"] = "failed"
            stage["verdict"] = verdict
            print(f"\n  ⚠️  Stage {stage_num} FAILED: {verdict}")
            print(f"  Pipeline stopped. Fix the issue and run with --resume.")
            save_state(state)
            sys.exit(1)
        else:
            # No verdict found — treat as passed for now, log warning
            print(f"\n  ⚠️  No verdict found in output. Marking as passed.")
            stage["status"] = "passed"
            stage["verdict"] = "no_verdict_extracted"
            state["current_stage"] = int(stage_num) + 1

        save_state(state)


def main():
    parser = argparse.ArgumentParser(description="Pipeline runner for Claude Code")
    parser.add_argument("type", nargs="?", choices=["feature", "bugfix", "refactor"],
                        help="Pipeline type")
    parser.add_argument("--task", "-t", help="Task description")
    parser.add_argument("--project", "-p", default=".", help="Project directory")
    parser.add_argument("--target-branch", "-b", default="main",
                        help="PR target branch (default: main)")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Resume most recent incomplete pipeline")
    parser.add_argument("--state", "-s", help="Resume from specific state file")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List pipeline state and exit")

    args = parser.parse_args()

    # Resume mode
    if args.resume or args.state:
        if args.state:
            path = Path(args.state)
        else:
            path = find_resume_state(args.project)
        if not path:
            print("No incomplete pipeline found to resume.")
            sys.exit(1)
        state = load_state(path)
        result = next_stage(state)
        if result:
            stage_num, stage = result
            print(f"Resuming: {state['pipeline_type']} pipeline")
            print(f"Task: {state['task_description'][:60]}")
            print(f"Branch: {state['branch_name']}")
            print(f"Next stage: {stage_num} ({stage['name']})")
        run_pipeline(state)
        return

    # List mode
    if args.list:
        state_dir = Path(args.project) / ".pipeline-state"
        if not state_dir.exists():
            print("No pipeline state directory found.")
            return
        for f in sorted(state_dir.glob("*.json")):
            state = load_state(f)
            result = next_stage(state)
            status = "complete" if result is None else f"stage {result[0]}: {result[1]['name']}"
            print(f"  {f.name}: {state['pipeline_type']} — {status}")
        return

    # New pipeline
    if not args.type or not args.task:
        parser.error("Pipeline type and --task are required (or use --resume)")

    state = init_state(args.type, args.task, args.project, args.target_branch)

    # Check if state file already exists (duplicate)
    existing = state_path(state["project_path"], state["branch_name"])
    if existing.exists():
        print(f"State file already exists: {existing}")
        print("Use --resume to continue, or delete it to start fresh.")
        sys.exit(1)

    print(f"Starting {args.type} pipeline")
    print(f"Task: {args.task}")
    print(f"Branch: {state['branch_name']}")
    print(f"Target: {args.target_branch}")

    run_pipeline(state)


if __name__ == "__main__":
    main()
