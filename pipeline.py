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

    # Auto mode — parse ROADMAP.md and process tasks
    python pipeline.py auto --project ~/path --milestone v0.4.0 --priority P0
    python pipeline.py auto --project ~/path --milestone v0.4.0 --all
    python pipeline.py auto --project ~/path --list --milestone v0.4.0
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


def parse_roadmap(project: str, roadmap_path: str | None = None) -> list[dict]:
    """Use Claude to parse ROADMAP.md into structured tasks."""
    if roadmap_path is None:
        # Search common locations
        for candidate in ["ROADMAP.md", "docs/roadmap.md", "docs/ROADMAP.md"]:
            path = Path(project) / candidate
            if path.exists():
                roadmap_path = str(path)
                break
    if not roadmap_path or not Path(roadmap_path).exists():
        print(f"Error: ROADMAP.md not found in {project}")
        sys.exit(1)

    prompt = f"""Read the file {roadmap_path} and extract all actionable tasks from the "Next Up" and "In Progress" sections.

Output ONLY a JSON array, no other text. Each task object must have:
- "milestone": the version string (e.g., "v0.4.0")
- "milestone_title": the milestone title
- "section": the section name within the milestone (e.g., "Critical Bug Fixes", "Quick Wins")
- "name": the feature/task name (the bold text)
- "priority": P0/P1/P2/P3 (check the Priority Matrix table at the top, default P2 if not listed)
- "issue": GitHub issue number if present (integer or null)
- "type": "bugfix" if section contains "Bug Fix" or description mentions fixing/broken/regression, else "feature"
- "spec": the full description text from the ROADMAP (include everything from the bold name to the next bold name or section boundary)

Skip:
- Anything under "Completed" sections
- Items marked with checkmarks or "Already implemented"
- "Future (Post-1.0)", "Contributing", "Investigate & Decide", "Differentiators", "Parity Tracker" sections

Output the JSON array and nothing else."""

    output, exit_code = run_claude(prompt, project, max_turns=5)

    # Extract JSON from output
    try:
        # Find the JSON array in the output
        match = re.search(r"\[[\s\S]*\]", output)
        if not match:
            print("Error: Could not parse ROADMAP tasks from Claude output.")
            print(f"Output: {output[:500]}")
            sys.exit(1)
        tasks = json.loads(match.group(0))
        return tasks
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON from roadmap parser: {e}")
        print(f"Output: {output[:500]}")
        sys.exit(1)


def filter_tasks(tasks: list[dict], milestone: str | None, priority: str | None,
                 feature: str | None) -> list[dict]:
    """Filter and sort tasks by milestone, priority, and feature keyword."""
    filtered = tasks

    if milestone:
        filtered = [t for t in filtered if t.get("milestone") == milestone]

    if priority:
        filtered = [t for t in filtered if t.get("priority") == priority]

    if feature:
        kw = feature.lower()
        filtered = [t for t in filtered
                    if kw in t.get("name", "").lower()
                    or kw in t.get("spec", "").lower()
                    or kw in t.get("section", "").lower()]

    # Sort: P0 first, then by section priority (Bug Fixes first), then document order
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    filtered.sort(key=lambda t: (
        priority_order.get(t.get("priority", "P2"), 2),
        0 if "bug" in t.get("section", "").lower() else 1,
    ))

    return filtered


def is_task_done(project: str, task: dict) -> tuple[bool, str]:
    """Check if a task is already done (has merged PR or completed state)."""
    prefix = "fix" if task.get("type") == "bugfix" else "feat"
    branch = f"{prefix}/{slugify(task['name'])}"

    # Check for completed state file
    sp = state_path(project, branch)
    if sp.exists():
        state = load_state(sp)
        if state.get("completed_at"):
            return True, f"completed (state file)"
        # Incomplete state — needs resume, not skip
        return False, f"incomplete (stage {state.get('current_stage', '?')})"

    # Check for merged PR
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--state", "merged", "--head", branch, "--json", "number,title", "--limit", "1"],
            cwd=project, capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            if prs:
                return True, f"merged PR #{prs[0]['number']}"
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    # Check for existing branch with commits
    try:
        result = subprocess.run(
            ["git", "branch", "--list", branch],
            cwd=project, capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            # Branch exists — check if it has a merged PR
            return False, "branch exists (no merged PR)"
    except subprocess.TimeoutExpired:
        pass

    return False, "not started"


def run_auto(project: str, roadmap: str | None, milestone: str | None,
             priority: str | None, feature: str | None, process_all: bool,
             list_only: bool):
    """Parse ROADMAP and process tasks through pipelines."""
    project = os.path.abspath(project)

    print(f"{'═' * 60}")
    print(f"  Pipeline Auto — Parsing ROADMAP")
    print(f"{'═' * 60}\n")

    tasks = parse_roadmap(project, roadmap)
    print(f"  Found {len(tasks)} tasks in ROADMAP\n")

    filtered = filter_tasks(tasks, milestone, priority, feature)
    if not filtered:
        print("  No tasks match the filters.")
        return

    # Determine target branch
    target_branch = f"dev/{milestone}" if milestone else "main"

    # Check status of each task
    print(f"{'═' * 60}")
    title = f"  {milestone or 'All'} Tasks"
    if priority:
        title += f" (Priority: {priority})"
    print(title)
    print(f"{'═' * 60}\n")

    actionable = []
    for task in filtered:
        done, status = is_task_done(project, task)
        marker = "✅" if done else "⬜"
        issue_str = f" (#{task['issue']})" if task.get("issue") else ""
        print(f"  {marker} [{task.get('priority', '??')}] {task['name']}{issue_str} — {status}")
        if not done:
            actionable.append(task)

    print(f"\n  {len(filtered) - len(actionable)} done, {len(actionable)} remaining\n")

    if list_only:
        return

    if not actionable:
        print("  All tasks are complete!")
        return

    # Process tasks
    to_process = actionable if process_all else actionable[:1]

    if process_all and len(to_process) > 3:
        print(f"  ⚠️  About to process {len(to_process)} tasks. Ctrl+C to cancel.\n")

    results = {"succeeded": [], "failed": [], "skipped": []}

    for i, task in enumerate(to_process, 1):
        print(f"\n{'═' * 60}")
        print(f"  Processing {i}/{len(to_process)}: {task['name']}")
        print(f"  Milestone: {task.get('milestone', '?')} | Priority: {task.get('priority', '?')}")
        print(f"  Type: {task.get('type', 'feature')} | Issue: #{task.get('issue', 'none')}")
        print(f"{'═' * 60}")

        pipeline_type = task.get("type", "feature")
        task_desc = task.get("spec") or task.get("name")

        # Check for incomplete state (resume)
        prefix = "fix" if pipeline_type == "bugfix" else "feat"
        branch = f"{prefix}/{slugify(task['name'])}"
        sp = state_path(project, branch)

        if sp.exists():
            state = load_state(sp)
            if state.get("completed_at") is None:
                print(f"  Resuming from stage {state.get('current_stage', 1)}")
                try:
                    run_pipeline(state)
                    results["succeeded"].append(task)
                except SystemExit:
                    results["failed"].append(task)
                continue

        # New pipeline
        state = init_state(pipeline_type, task_desc, project, target_branch)
        # Override branch name to include issue number if present
        if task.get("issue"):
            state["branch_name"] = f"{prefix}/{slugify(task['name'])}-{task['issue']}"

        try:
            run_pipeline(state)
            results["succeeded"].append(task)
        except SystemExit:
            results["failed"].append(task)

    # Summary
    print(f"\n{'═' * 60}")
    print(f"  Pipeline Auto Complete")
    print(f"{'═' * 60}")
    print(f"  Milestone: {milestone or 'all'}")
    print(f"  Tasks processed: {len(to_process)}")
    print(f"  Succeeded: {len(results['succeeded'])}")
    print(f"  Failed: {len(results['failed'])}")
    if results["failed"]:
        for t in results["failed"]:
            print(f"    ❌ {t['name']}")
    print(f"  Dev branch: {target_branch}")
    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline runner for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single pipeline
  python pipeline.py bugfix --task "Fix event sequencing #560" --project ~/djust
  python pipeline.py feature --task "Add dj-value-*" --project ~/djust -b dev/v0.4.0

  # Auto mode (ROADMAP-driven)
  python pipeline.py auto --project ~/djust --milestone v0.4.0 --priority P0
  python pipeline.py auto --project ~/djust --milestone v0.4.0 --all
  python pipeline.py auto --project ~/djust --list --milestone v0.4.0

  # Resume
  python pipeline.py --resume --project ~/djust
        """,
    )
    parser.add_argument("type", nargs="?", choices=["feature", "bugfix", "refactor", "auto"],
                        help="Pipeline type or 'auto' for ROADMAP-driven mode")
    parser.add_argument("--task", "-t", help="Task description (for single pipeline)")
    parser.add_argument("--project", "-p", default=".", help="Project directory")
    parser.add_argument("--target-branch", "-b", default="main",
                        help="PR target branch (default: main)")
    parser.add_argument("--resume", "-r", action="store_true",
                        help="Resume most recent incomplete pipeline")
    parser.add_argument("--state", "-s", help="Resume from specific state file")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List pipeline state / roadmap tasks and exit")
    # Auto mode options
    parser.add_argument("--milestone", "-m", help="Filter by milestone (e.g., v0.4.0)")
    parser.add_argument("--priority", help="Filter by priority (P0/P1/P2/P3)")
    parser.add_argument("--feature", "-f", help="Filter by feature name/keyword")
    parser.add_argument("--all", dest="process_all", action="store_true",
                        help="Process all matching tasks (default: just the first)")
    parser.add_argument("--roadmap", help="Path to ROADMAP.md (auto-detected if not specified)")

    args = parser.parse_args()

    # Auto mode
    if args.type == "auto":
        run_auto(
            project=args.project,
            roadmap=args.roadmap,
            milestone=args.milestone,
            priority=args.priority,
            feature=args.feature,
            process_all=args.process_all,
            list_only=args.list,
        )
        return

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

    # List mode (non-auto)
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

    # New single pipeline
    if not args.type or not args.task:
        parser.error("Pipeline type and --task are required (or use 'auto' or --resume)")

    if args.type not in ("feature", "bugfix", "refactor"):
        parser.error(f"Unknown pipeline type: {args.type}")

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
