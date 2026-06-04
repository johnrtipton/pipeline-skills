---
name: pipeline-dev
description: >
  Fast iteration loop for initial-development work: branch → implement → build →
  push → live-verify → merge. No subagent reviews, no CHANGELOG, no roadmap
  coupling. Optimized for rapid PR cycles where the USER is the reviewer
  (manual verification via browser/CLI) and browser-extension reload/reconnect
  is an explicit handoff step. Use this INSTEAD OF /pipeline-ship when there's
  no CI, no formal review, and the goal is shipping many small PRs per day.
---

# pipeline-dev — Fast iteration PR loop

The dev-mode counterpart to `/pipeline-ship`. `pipeline-ship` runs a full
gauntlet (test → subagent review → security → docs → changelog → code-review
subagent → merge → retro). That's correct for framework-level releases with
CI, but it's overkill for initial development where:

- The user manually verifies each change (clicks in browser, runs the tool)
- There's no CI pipeline to gate on
- Extension changes need an explicit reload + MCP reconnect
- A typical "iteration" is 3–10 minutes of work → PR → verify → merge

This skill strips the ceremony to the minimum that still maintains branch
hygiene and clean merge history.

## Usage

```
/pipeline-dev                          # Iterate on the current uncommitted work
/pipeline-dev --description "..."      # Start from empty, describe the task
/pipeline-dev --target master          # Target branch (default: main, or master if main missing)
/pipeline-dev --no-reload              # Skip the reload/reconnect handoff (pure-server tasks)
/pipeline-dev --resume                 # Continue an existing PR branch after a user-reported bug
```

## What gets skipped vs /pipeline-ship

| Stage | pipeline-ship | pipeline-dev |
|---|---|---|
| Subagent test-runner | ✓ | ✗ (manual only) |
| Subagent self-review | ✓ | ✗ (user is reviewer) |
| Subagent security review | ✓ | ✗ (user is reviewer) |
| Subagent code-reviewer on PR | ✓ | ✗ |
| CHANGELOG update | required | skipped |
| docs/website updates | required | skipped |
| Conventional commit format | ✓ | ✓ (keep) |
| Branch from fresh target | ✓ | ✓ (keep) |
| Build before push | ✓ | ✓ (keep) |
| PR opened, not direct-push | ✓ | ✓ (keep) |
| Squash-merge + delete branch | ✓ | ✓ (keep) |
| Pipeline retro as PR comment | ✓ | ✗ |

## The loop

```
┌─────────────────┐
│ 1. Scope & branch│ ← create clean branch from fresh target
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Implement    │ ← edit files, add tools, fix bug
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Build/test   │ ← npm run build / cargo build / pytest -x (if applicable)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Commit + push│ ← conventional-commit message; push; open PR
│    + open PR    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. Handoff      │ ← "Reload extension + reconnect MCP", wait for user
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. Verify live  │ ← run the new tools, observe behavior, catch bugs
└────────┬────────┘
         ▼
         ├── bugs? → fix on same branch, push again, loop to step 5
         │
         ▼
┌─────────────────┐
│ 7. Merge        │ ← squash-merge + delete branch
└────────┬────────┘
         ▼
┌─────────────────┐
│ 8. Reset        │ ← checkout target, git pull --ff-only
└─────────────────┘
```

## Stage details

### 1. Scope & branch

- Confirm the task in one sentence (e.g., "Add ws_throttle tool").
- Check `git status` — uncommitted changes from the previous iteration?
  Either amend them into this one or stash and resume with `/pipeline-dev --resume`.
- Pull target: `git checkout {target} && git pull --ff-only`.
- Create branch: `git checkout -b {type}/{short-name}` where `type` is
  `feat`, `fix`, `docs`, `refactor`, `chore`, or `perf`.

### 2. Implement

- Make the code changes. For browser-extension work, remember:
  - **content.js** runs in isolated world (no `window.djust`)
  - **injected.js** runs in MAIN world (has `window.djust`, WebSocket, etc.)
  - New MCP tools need BOTH:
    - dispatch case in content.js (or `sendToInjected` passthrough)
    - handler function in content.js or injected.js
    - Zod schema in `src/tools/*.ts`
    - registration in `src/server.ts`
- Keep scope tight. Feature creep → new PR.

### 3. Build

- TypeScript: `npm run build` from the MCP repo root. `tsc` errors fail fast.
- Rust (if applicable): `cargo build --release`.
- Python unit tests, only if clearly relevant to the change: `pytest path/to/test_foo.py`.
- Skip the full test suite for dev iteration. That's what CI is for in
  `/pipeline-ship`; for dev iteration, trust the type-checker + manual verify.

### 4. Commit + push + PR

One commit per PR — squash-merge will collapse multi-commit chains anyway,
but single commits keep the history legible during the iteration.

**Commit message** (conventional commits):
```
<type>: <short imperative description>

<body: what changed, why, what's the impact>

<optional: any specific call-out a future reader will need>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Push and open PR in one command chain**:
```bash
git push -u origin <branch>
gh pr create --title "..." --body "$(cat <<'EOF'
## Summary
- bullet 1
- bullet 2

## Test plan
- [ ] reload extension + reconnect MCP
- [ ] call new tool on /examples/
- [ ] verify output shape

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 5. Handoff

For browser-extension PRs (djust-browser-mcp), the build produces new
`dist/` output but the running MCP server + loaded content scripts are still
the old versions. The agent MUST explicitly prompt:

> "PR #N opened: <url>. Please reload the Chrome extension and reconnect
> `djust-browser` MCP so I can verify."

Then **stop and wait**. Do NOT try to call the new tools before the user
confirms — they won't be in the deferred-tool list yet and the call will
error out, wasting a round trip.

If the PR is pure-server (no extension changes), skip this stage — pass
`--no-reload`.

### 6. Verify live

After the user says "reloaded" / "done" / "reconnected":

1. Load the new tool schemas via `ToolSearch` with `select:<name>`.
2. Call the new tool with realistic arguments.
3. Report the result concisely.

Verification is the PR review. If the tool doesn't work as expected:

- Trace the cause (which world? content.js or injected.js? build artifact stale?)
- Patch on the same branch
- `npm run build`
- `git add {files} && git commit -m "fix: ..." && git push`
- Loop back to stage 5 (re-request reload)

### 7. Merge

Once verification passes:

```bash
gh pr merge <N> --squash --delete-branch
```

Use `--admin` only if blocked by a branch-protection rule that doesn't apply
to the dev context (rare in a single-developer early-stage repo).

### 8. Reset

```bash
git checkout {target} && git pull --ff-only
```

Confirm clean tree: `git status --short`. Then either close out, or
`/pipeline-dev` again for the next item.

## When to escalate to /pipeline-ship

Switch to the heavier `/pipeline-ship` when any of these apply:

- Framework-level change that affects downstream users (djust core)
- Security-sensitive change (auth, CSRF, permission logic)
- Public API change (adds/changes/removes a decorator or mixin)
- Release candidate / version bump
- CI is configured and should gate the PR
- CHANGELOG is required by the repo's convention

For repos without CI where the user iterates live (djust-browser-mcp,
djust.org during early iteration, internal prototypes), `pipeline-dev` is
the right tool.

## Example run (abbreviated)

```
User: "Add a ws_throttle tool"

Claude:
  [stage 1] Creates branch feat/ws-throttle from master
  [stage 2] Edits injected.js + content.js + src/tools/advanced.ts + src/server.ts
  [stage 3] npm run build — clean
  [stage 4] Commits "feat: ws_throttle (delay/drop WS frames)", pushes,
            opens PR #N
  [stage 5] "Reload extension + reconnect MCP"
  User:     "done"
  [stage 6] ToolSearch → load schema → call ws_throttle → verify delay
            takes effect, capture stats, clear, verify cleared.
  [stage 7] gh pr merge --squash --delete-branch
  [stage 8] git checkout <default-branch> && git pull
            (the repo's default branch from pipeline-config; not hard-coded)
  
Claude: "Merged as PR #N. Next?"
```

## Anti-patterns

Things this skill explicitly does NOT do, and you should resist the pull to:

- **Spawning a code-reviewer subagent**. The user's "works" / "doesn't work"
  on verify is the review signal. Subagent review just adds latency.
- **Asking for approval before merge**. In dev mode, once verification
  passes, merge is autonomous. Don't make the user say "merge" twice.
- **Writing CHANGELOG entries**. Dev-mode repos don't track them.
  (If the repo convention says otherwise, you shouldn't be using pipeline-dev.)
- **Running full test suites "just in case"**. Dev iteration trusts the
  type-checker + manual verify. If something breaks that manual verify
  misses, add a regression tool in a follow-up PR.
- **Batching unrelated fixes**. If you notice a pre-existing bug while
  implementing the task, file it as a separate task, don't tack it onto
  this PR. The exception: if the pre-existing bug actively blocks
  verification of the new tool, fix it inline and note it in the commit.
