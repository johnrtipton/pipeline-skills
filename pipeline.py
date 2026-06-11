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
PROFILES_DIR = Path(__file__).parent / "profiles"


def deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base. Lists are concatenated, dicts are merged recursively."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = result[key] + value
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def detect_profile(project: str) -> str:
    """Auto-detect the appropriate profile for a project."""
    project_path = Path(project)

    # Check CLAUDE.md for explicit pipeline_profile setting
    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()
        match = re.search(r"pipeline_profile:\s*(\w+)", content)
        if match:
            return match.group(1)

    # Auto-detect from project files
    if (project_path / "manage.py").exists():
        return "django"
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text().lower()
        if "django" in content:
            return "django"

    return "generic"


def resolve_agent(project: str, agent_arg: str | None = None) -> str:
    """Resolve which agent backend to drive the pipeline with.

    Precedence (first match wins): ``--agent`` CLI flag -> ``PIPELINE_AGENT``
    env var -> CLAUDE.md ``pipeline_agent:`` config -> ``DEFAULT_AGENT``.
    Mirrors the profile-resolution chain so projects can pin a backend in
    CLAUDE.md without passing the flag every run.
    """
    if agent_arg:
        agent = agent_arg
    elif os.environ.get("PIPELINE_AGENT"):
        agent = os.environ["PIPELINE_AGENT"]
    else:
        agent = None
        claude_md = Path(project) / "CLAUDE.md"
        if claude_md.exists():
            m = re.search(r"^\s*-?\s*pipeline_agent:\s*(\S+)", claude_md.read_text(),
                          re.MULTILINE)
            if m:
                agent = m.group(1)
        if not agent:
            agent = DEFAULT_AGENT

    if agent not in AGENT_BACKENDS:
        print(f"Error: unknown agent backend {agent!r} "
              f"(supported: {', '.join(AGENT_BACKENDS)})")
        sys.exit(1)
    return agent


def detect_default_branch(project: str) -> str:
    """Resolve the repo's default branch — mirrors the pipeline-* skills' chain.

    Order: CLAUDE.md pipeline-config ``default_branch`` -> ``origin/HEAD``
    symbolic ref -> ``git remote show origin`` HEAD branch -> ``origin/<cand>``
    existence probe -> current branch -> ``main`` fallback. Never assume
    ``main``/``master``; the literal is only the last resort. The current-branch
    fallback fixes #45 (a ``master`` repo with no ``origin`` wrongly returned
    ``main``).
    """
    project_path = Path(project)

    # 1. CLAUDE.md pipeline-config default_branch
    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        m = re.search(r"^\s*-?\s*default_branch:\s*(\S+)", claude_md.read_text(),
                      re.MULTILINE)
        if m:
            return m.group(1)

    # 2. origin/HEAD symbolic ref (fails on many repos — must fall through)
    try:
        r = subprocess.run(
            ["git", "-C", project, "symbolic-ref", "--short",
             "refs/remotes/origin/HEAD"],
            capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().removeprefix("origin/")
    except (subprocess.TimeoutExpired, OSError):
        pass

    # 3. ask the remote
    try:
        r = subprocess.run(["git", "-C", project, "remote", "show", "origin"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            m = re.search(r"HEAD branch:\s*(\S+)", r.stdout)
            if m and m.group(1) != "(unknown)":
                return m.group(1)
    except (subprocess.TimeoutExpired, OSError):
        pass

    # 4. probe a remote branch in priority order (remote exists but HEAD unset)
    for cand in ("main", "master", "development"):
        try:
            r = subprocess.run(
                ["git", "-C", project, "rev-parse", "--verify", "--quiet",
                 f"refs/remotes/origin/{cand}"],
                capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return cand
        except (subprocess.TimeoutExpired, OSError):
            pass

    # 5. current branch — last resort for a local/remoteless repo (#45).
    #    Without this, a master-default repo with no origin wrongly returned "main".
    try:
        r = subprocess.run(["git", "-C", project, "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        b = r.stdout.strip()
        if r.returncode == 0 and b and b != "HEAD":   # "HEAD" == detached
            return b
    except (subprocess.TimeoutExpired, OSError):
        pass

    # 6. absolute fallback
    return "main"


def load_profile(profile_name: str) -> dict:
    """Load a profile, merging with generic base if not already generic."""
    generic_path = PROFILES_DIR / "generic.json"
    profile_path = PROFILES_DIR / f"{profile_name}.json"

    if not profile_path.exists():
        print(f"Warning: profile '{profile_name}' not found, using generic")
        profile_path = generic_path

    with open(generic_path) as f:
        base = json.load(f)

    if profile_name == "generic":
        return base

    with open(profile_path) as f:
        overlay = json.load(f)

    return deep_merge(base, overlay)


def load_project_overrides(project: str, pipeline_type: str) -> tuple[dict | None, dict | None]:
    """Load per-repo .pipeline/ overrides. Returns (template_override, profile_override)."""
    pipeline_dir = Path(project) / ".pipeline"
    template_override = None
    profile_override = None

    if not pipeline_dir.exists():
        return None, None

    # Check for template override
    template_path = pipeline_dir / f"{pipeline_type}-state.json"
    if template_path.exists():
        with open(template_path) as f:
            template_override = json.load(f)

    # Check for profile override
    profile_path = pipeline_dir / "profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            profile_override = json.load(f)

    return template_override, profile_override


def apply_profile(state: dict, profile: dict) -> dict:
    """Inject profile content into a state file's stages."""
    pipeline_type = state["pipeline_type"]

    # Inject stage_additions into matching stages' checklists
    for key, additions in profile.get("stage_additions", {}).items():
        parts = key.split(".")
        if len(parts) != 2:
            continue
        ptype, stage_num = parts
        if ptype != pipeline_type:
            continue
        if stage_num in state["stages"]:
            stage = state["stages"][stage_num]
            checklist = stage.get("checklist", [])
            # Insert profile additions before the last mandatory item (usually the verdict output)
            insert_idx = len(checklist)
            for i in range(len(checklist) - 1, -1, -1):
                if checklist[i].get("mandatory"):
                    insert_idx = i
                    break
            for j, item in enumerate(additions):
                checklist.insert(insert_idx + j, item)
            stage["checklist"] = checklist

    # Inject security patterns into security check stages
    security_patterns = profile.get("security_patterns", [])
    if security_patterns:
        pattern_text = ", ".join(security_patterns[:10])
        for stage in state["stages"].values():
            for item in stage.get("checklist", []):
                if "scan changed files for security patterns" in item.get("action", ""):
                    item["action"] = f"scan changed files for: {pattern_text}"

    # Inject auto-reject triggers into subagent prompts
    auto_reject = profile.get("auto_reject_triggers", [])
    if auto_reject:
        trigger_text = ", ".join(auto_reject[:10])
        for stage in state["stages"].values():
            prompt = stage.get("subagent_prompt", "")
            if "auto-reject triggers" in prompt.lower() and "{profile_triggers}" in prompt:
                stage["subagent_prompt"] = prompt.replace("{profile_triggers}", trigger_text)

    # Store profile info in state
    state["profile"] = profile.get("name", "generic")
    state["profile_config"] = {
        "security_patterns": profile.get("security_patterns", []),
        "auto_reject_triggers": profile.get("auto_reject_triggers", []),
        "environment": profile.get("environment", {}),
        "docs": profile.get("docs", {}),
    }

    return state


def slugify(text: str) -> str:
    """Convert text to a branch-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().strip())
    return slug.strip("-")[:50]


def load_template(pipeline_type: str, project: str | None = None) -> dict:
    """Load the state file template, checking for project overrides first."""
    # Check for project-level template override
    if project:
        override_path = Path(project) / ".pipeline" / f"{pipeline_type}-state.json"
        if override_path.exists():
            print(f"  Using project template override: {override_path}")
            with open(override_path) as f:
                return json.load(f)

    template_path = TEMPLATES_DIR / f"{pipeline_type}-state.json"
    if not template_path.exists():
        print(f"Error: template not found: {template_path}")
        sys.exit(1)
    with open(template_path) as f:
        return json.load(f)


def init_state(pipeline_type: str, task: str, project: str, target_branch: str,
               profile_name: str | None = None, agent: str | None = None,
               agent_model: str | None = None) -> dict:
    """Create a new state file from template, applying profile and project overrides."""
    project = os.path.abspath(project)
    state = load_template(pipeline_type, project)
    prefix = {"feature": "feat", "bugfix": "fix", "refactor": "refactor"}[pipeline_type]
    branch = f"{prefix}/{slugify(task)}"

    state["task_description"] = task
    state["branch_name"] = branch
    state["pr_target_branch"] = target_branch
    state["project_path"] = project
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    # Persist the agent backend so --resume keeps driving the same one.
    state["agent"] = resolve_agent(project, agent)
    if agent_model:
        state["agent_model"] = agent_model

    # Load and apply profile
    if not profile_name:
        profile_name = detect_profile(project)
    profile = load_profile(profile_name)

    # Check for project-level profile overrides
    _, profile_override = load_project_overrides(project, pipeline_type)
    if profile_override:
        print(f"  Applying project profile override from .pipeline/profile.json")
        profile = deep_merge(profile, profile_override)

    state = apply_profile(state, profile)
    print(f"  Profile: {profile.get('name', profile_name)}")

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
    # Ensure .pipeline-state/ and .pipeline-log.md are gitignored
    gitignore = Path(state["project_path"]) / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        additions = []
        if ".pipeline-state/" not in content:
            additions.append(".pipeline-state/")
        if ".pipeline-log.md" not in content:
            additions.append(".pipeline-log.md")
        if additions:
            with open(gitignore, "a") as f:
                f.write("\n" + "\n".join(additions) + "\n")
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


# Supported agent backends. The harness is CLI-driven and otherwise
# agent-agnostic: each backend just needs to take a single prompt, run
# headlessly to completion, and emit the stage's verdict string to stdout.
AGENT_BACKENDS = ("claude", "opencode")
DEFAULT_AGENT = "claude"


def build_agent_cmd(agent: str, prompt: str, project: str, max_turns: int,
                    model: str | None) -> list[str]:
    """Build the headless CLI invocation for the chosen agent backend.

    Backends differ in flag surface, so each is spelled out explicitly:

    - ``claude``   : ``claude -p PROMPT --output-format text --max-turns N``
                     (Claude Code; ``-p`` takes the prompt, supports max-turns,
                     honors the inherited process cwd)
    - ``opencode`` : ``opencode run PROMPT --format default --dir PROJECT``
                     (OpenCode; prompt is positional, no ``-p`` / max-turns flag,
                     ``--dangerously-skip-permissions`` for unattended runs,
                     ``-m provider/model`` for model selection, and ``--dir`` to
                     set the working directory — OpenCode does NOT honor the
                     inherited process cwd, so file edits land in the wrong place
                     without it)
    """
    if agent == "claude":
        cmd = ["claude", "-p", prompt,
               "--output-format", "text",
               "--max-turns", str(max_turns)]
        if model:
            cmd += ["--model", model]
        return cmd
    if agent == "opencode":
        # OpenCode's `run` takes the prompt positionally and has no max-turns
        # flag. --dangerously-skip-permissions is required for unattended runs
        # so file edits / shell calls aren't blocked waiting for approval.
        # --dir is REQUIRED: OpenCode resolves its working directory from this
        # flag, not from the process cwd that subprocess sets, so without it the
        # agent edits files relative to wherever pipeline.py was launched.
        cmd = ["opencode", "run", prompt,
               "--format", "default",
               "--dangerously-skip-permissions",
               "--dir", os.path.abspath(project)]
        if model:
            cmd += ["-m", model]
        return cmd
    raise ValueError(
        f"Unknown agent backend: {agent!r} (supported: {', '.join(AGENT_BACKENDS)})"
    )


def run_agent(prompt: str, project: str, agent: str = DEFAULT_AGENT,
              max_turns: int = 50, model: str | None = None) -> tuple[str, int]:
    """Run the configured agent backend with a prompt; return output + exit code."""
    cmd = build_agent_cmd(agent, prompt, project, max_turns, model)
    label = {"claude": "Claude Code", "opencode": "OpenCode"}.get(agent, agent)
    print(f"\n{'─' * 60}")
    print(f"Running {label}...")
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
        output, exit_code = run_agent(
            prompt, state["project_path"],
            agent=state.get("agent", DEFAULT_AGENT),
            model=state.get("agent_model"),
        )

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


def parse_priority_matrix(lines: list[str]) -> dict[str, str]:
    """Parse the Priority Matrix table to map feature names to priorities."""
    priorities = {}
    in_table = False
    for line in lines:
        if "Priority" in line and "Feature" in line and "Why" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 4:
                # Extract priority — handle ~~**P0**~~ and **P1** formats
                prio_cell = cols[1]
                prio_match = re.search(r"P[0-3]", prio_cell)
                if not prio_match:
                    continue
                priority = prio_match.group(0)
                # Extract feature name — strip ~~, **, `, links
                feature = cols[2]
                completed = "✅" in feature or "~~" in feature
                feature = feature.replace("~~", "").strip("* ")
                feature = re.sub(r"`([^`]+)`", r"\1", feature)
                feature = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", feature)
                feature = feature.strip()
                if feature:
                    priorities[feature.lower()] = priority
                    if completed:
                        priorities[feature.lower() + ":done"] = True
        elif in_table and not line.strip().startswith("|") and line.strip() != "":
            in_table = False
    return priorities


def parse_roadmap(project: str, roadmap_path: str | None = None) -> list[dict]:
    """Parse ROADMAP.md into structured tasks using markdown parsing."""
    if roadmap_path is None:
        for candidate in ["ROADMAP.md", "docs/roadmap.md", "docs/ROADMAP.md"]:
            path = Path(project) / candidate
            if path.exists():
                roadmap_path = str(path)
                break
    if not roadmap_path or not Path(roadmap_path).exists():
        print(f"Error: ROADMAP.md not found in {project}")
        sys.exit(1)

    with open(roadmap_path) as f:
        content = f.read()
    lines = content.split("\n")

    # Parse priority matrix
    priorities = parse_priority_matrix(lines)

    # Sections to skip
    skip_sections = {
        "completed", "future", "post-1.0", "contributing", "investigate",
        "differentiators", "parity tracker", "priority matrix",
    }

    tasks = []
    current_milestone = None
    current_milestone_title = None
    current_section = None
    in_skip = False
    current_feature = None
    current_spec_lines = []

    def flush_feature():
        nonlocal current_feature, current_spec_lines
        if current_feature and current_milestone:
            spec = "\n".join(current_spec_lines).strip()
            # Detect type
            section_lower = (current_section or "").lower()
            spec_lower = spec.lower()
            is_bugfix = (
                "bug fix" in section_lower
                or "fix" in current_feature.lower()[:20]
                or any(w in spec_lower[:200] for w in ["fix:", "broken", "fails", "regression", "crash"])
            )
            # Extract issue number
            issue = None
            issue_match = re.search(r"\(#(\d+)\)", current_feature)
            if issue_match:
                issue = int(issue_match.group(1))
            # Match priority — fuzzy match against priority matrix
            feature_clean = re.sub(r"\s*\(#\d+\)", "", current_feature).strip()
            prio = "P2"
            # Normalize for matching: strip backticks, lowercase, remove extra whitespace
            feature_norm = re.sub(r"`([^`]+)`", r"\1", feature_clean).lower().strip()
            feature_norm = re.sub(r"\s+", " ", feature_norm)
            # Try exact match first, then substring, then word overlap
            for key, val in priorities.items():
                if ":done" in key:
                    continue
                if key == feature_norm or feature_norm == key:
                    prio = val
                    break
                # First significant words match (e.g., "js commands" matches "JS Commands (dj.push...)")
                key_words = set(re.findall(r"\w{3,}", key))
                feat_words = set(re.findall(r"\w{3,}", feature_norm))
                if key_words and feat_words:
                    overlap = key_words & feat_words
                    if len(overlap) >= min(2, len(key_words)):
                        prio = val
                        break

            tasks.append({
                "milestone": current_milestone,
                "milestone_title": current_milestone_title,
                "section": current_section,
                "name": feature_clean,
                "priority": prio,
                "issue": issue,
                "type": "bugfix" if is_bugfix else "feature",
                "spec": spec,
            })
        current_feature = None
        current_spec_lines = []

    for line in lines:
        stripped = line.strip()

        # Detect h2 sections (## Completed, ## Next Up, etc.)
        if stripped.startswith("## "):
            flush_feature()
            heading = stripped[3:].strip().lower()
            in_skip = any(s in heading for s in skip_sections)
            continue

        if in_skip:
            continue

        # Detect milestones (### Milestone: v0.4.0 — Title)
        milestone_match = re.match(r"###\s+Milestone:\s+(v[\d.]+)\s*[—–-]\s*(.*)", stripped)
        if milestone_match:
            flush_feature()
            current_milestone = milestone_match.group(1)
            current_milestone_title = milestone_match.group(2).strip()
            current_section = None
            continue

        # Also handle "### Stability & Correctness" style (In Progress section)
        if stripped.startswith("### ") and not stripped.startswith("### Milestone"):
            flush_feature()
            current_section = stripped[4:].strip()
            continue

        # Detect sections (#### Quick Wins, #### Critical Bug Fixes)
        if stripped.startswith("#### "):
            flush_feature()
            current_section = stripped[5:].strip()
            continue

        # Detect features (**Feature Name** — description)
        feature_match = re.match(r"\*\*(.+?)\*\*", stripped)
        if feature_match and current_milestone:
            flush_feature()
            current_feature = feature_match.group(1)
            # Skip already-completed items
            if "✅" in stripped or "already implemented" in stripped.lower():
                current_feature = None
                continue
            # Skip non-feature lines (milestone goals, etc.)
            if current_feature.lower() in ("goal", "scope"):
                current_feature = None
                continue
            # Skip if marked done in priority matrix
            feature_check = re.sub(r"`([^`]+)`", r"\1", current_feature).lower().strip()
            feature_check = re.sub(r"\s*\(#\d+\)", "", feature_check)
            if priorities.get(feature_check + ":done"):
                current_feature = None
                continue
            current_spec_lines = [stripped]
            continue

        # Accumulate spec lines
        if current_feature:
            current_spec_lines.append(line)

    flush_feature()
    return tasks


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
        0 if "bug" in (t.get("section") or "").lower() else 1,
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
             list_only: bool, agent: str | None = None,
             agent_model: str | None = None):
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

    # Determine target branch (resolve the default branch — never hard-code "main")
    default_branch = detect_default_branch(project)
    target_branch = f"dev/{milestone}" if milestone else default_branch

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
        state = init_state(pipeline_type, task_desc, project, target_branch,
                           agent=agent, agent_model=agent_model)
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
    # Profile options
    parser.add_argument("--profile", help="Pipeline profile (generic/django/... or auto-detect)")
    # Agent backend options
    parser.add_argument("--agent", "-a", choices=AGENT_BACKENDS,
                        help="Agent backend to drive the pipeline "
                             "(default: PIPELINE_AGENT env / CLAUDE.md pipeline_agent / claude)")
    parser.add_argument("--agent-model",
                        help="Model passed to the agent backend "
                             "(e.g. opencode 'anthropic/claude-sonnet-4-5')")

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
            agent=args.agent,
            agent_model=args.agent_model,
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

    state = init_state(args.type, args.task, args.project, args.target_branch,
                       profile_name=args.profile, agent=args.agent,
                       agent_model=args.agent_model)

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
    print(f"Agent: {state.get('agent', DEFAULT_AGENT)}"
          + (f" ({state['agent_model']})" if state.get('agent_model') else ""))

    run_pipeline(state)


if __name__ == "__main__":
    main()
