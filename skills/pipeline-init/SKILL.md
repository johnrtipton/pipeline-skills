---
name: pipeline-init
description: >
  Initialize any repository so the entire pipeline-* family (next, run, dev,
  drain, retro, ship, strategy, roadmap-audit) works. Detects the repo's
  default branch, test/lint/build commands, ROADMAP format, and version scheme,
  then creates .pipeline-state/, .pipeline-templates/ (COPIED from the canonical
  pipeline-skill templates with the detected branch + commands substituted),
  gitignore entries, CHANGELOG/RETRO scaffolding, and a repo-root CLAUDE.md
  pipeline-config block — migrating a foreign-format ROADMAP to the canonical
  priority-matrix + milestone format the pipeline.py parser actually reads.
  Catches the failure where pipeline-next/run abort because no state template or
  conforming ROADMAP exists. Run once per repo before any other pipeline-* skill,
  or to repair a partially-set-up repo.
user_invocable: true
argument: >
  Optional: --dry-run (default — print the detection record and plan, change
  nothing). --apply (create files, migrate ROADMAP, back up originals first).
  --branch <name> (override the detected default branch). --pr-target <name> (PR
  target branch if it differs from default). --base-version vX.Y.Z (seed milestone
  version when the repo has no tags; defaults to v0.1.0). --changelog
  keep-a-changelog|none (changelog convention; default detect → keep-a-changelog).
  --with-ship / --with-gates (also scaffold ship-state.json /
  scripts/pipeline-gates.sh). --priority-map <file> (explicit feature→priority
  overrides for ROADMAP migration). --minimal (skip RETRO/adr/strategy-session
  scaffolding and the changelog two-commit gate when no changelog convention).
---

# Pipeline Init — Make any repo pipeline-ready

Initialize ANY repository so the whole `pipeline-*` family runs. This skill
**detects** the host repo's facts (default branch, test/lint/build commands,
ROADMAP format, version scheme) and **adapts** to them — it never hard-codes one
repo's branch, commands, or language.

The family assumes scaffolding that does not exist in a fresh repo. In the
validation case, the stock repo had a ROADMAP in `### N. Title \`[x]\`` checkbox
format under `## Active work / ## Completed / ## Backlog` headings — and **no**
`.pipeline-templates/`. So `/pipeline-next --list` parsed zero tasks (no Priority
Matrix the parser could read, no `### Milestone: vX.Y.Z` headings) and
`/pipeline-run` had no `<type>-state.json` to copy a state file from. The whole
family was dead on arrival. `/pipeline-init` is the one-time setup that fixes
exactly this: it installs the templates wired to the detected branch + commands,
and migrates the foreign ROADMAP into the format `pipeline.py`'s parser
understands.

**Core principle: detect → derive → emit. Nothing repo-specific is a constant.**
Every value (branch, commands, ROADMAP location, version) is produced by
detection at run time and either substituted into a COPIED canonical template or
written into a per-repo config file. This skill body contains only detection
logic and generic fallbacks — never a literal like `make test`, `master`, or
`cargo test`. The stock repo is only the test case; the same skill must do the
right thing on a `main`+`npm` repo or a `development`+`go` repo with no edits.

**Templates are COPIED, not reproduced.** The canonical `<type>-state.json`
templates live in the pipeline-skill's `templates/` directory (resolved via
`PIPELINE_SKILL_DIR` or the directory containing `pipeline.py`). They are NOT all
the same shape: **feature = 14 stages**, **bugfix = 12 stages**
(Diagnosis/Fix/Regression Check, `-diagnosis.md`, no Change Detection, no
standalone Security Check), **refactor = 12 stages** (Analysis/Refactor
Execution/Review), **ship = 10 stages**. Init **copies** each canonical template
verbatim and substitutes ONLY the detected values — it does not hand-write stage
skeletons (a hand-written skeleton would drift from what pipeline-run/shared
reference by stage name and would get the bugfix/refactor shape wrong). The
canonical templates already parameterize their branch references as
`{pr_target_branch}`, so substituting the top-level `pr_target_branch` value is
all that is needed to make every stage branch-agnostic.

## Why this is a distinct skill (not part of pipeline-next)

`pipeline-next` **assumes** the scaffolding exists: it reads ROADMAP.md, parses a
Priority Matrix and `### Milestone:` sections via `pipeline.py`, and copies
`.pipeline-templates/<type>-state.json` (or the skill-default template). If any
of those are missing it silently finds nothing. `pipeline-init` **creates** them.
Disambiguation:

- vs **pipeline-strategy** — strategy *plans* work (brainstorms features into a
  milestone). It needs a conforming ROADMAP to write into; init produces that
  surface.
- vs **pipeline-drain** — drain *consumes* an existing milestone (turns open
  issues into roadmap entries and runs them). It also needs a conforming
  ROADMAP; init produces it.
- vs **pipeline-roadmap-audit** — audit *verifies* a conforming ROADMAP against
  the code. Init can leave a freshly-migrated ROADMAP for audit to check.

Run init **first, once per repo.** Then next/run/strategy/drain/audit/ship work.

## Steps

### 1. Detect — build the detection record (read-only; runs in both modes)

Probe the host repo and build a detection record. Print it at the top of the
plan. Each probe has an ordered fallback chain — first hit wins.

#### 1.1 Default branch (the single most important repo-agnostic value)

Run this resolution chain, in order, stopping at the first that yields a branch.
This is copy-pasteable:

```bash
detect_default_branch() {
  local b
  # 1. origin/HEAD symbolic ref (fails on many repos — must not stop here)
  b=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')
  [ -n "$b" ] && { echo "$b"; echo "source=symbolic-ref" >&2; return; }
  # 2. ask the remote (needs network; this is what resolved on the stock repo)
  b=$(git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p')
  [ -n "$b" ] && [ "$b" != "(unknown)" ] && { echo "$b"; echo "source=remote-show" >&2; return; }
  # 3. local init.defaultBranch convention
  b=$(git config --get init.defaultBranch 2>/dev/null)
  [ -n "$b" ] && { echo "$b"; echo "source=init.defaultBranch" >&2; return; }
  # 4. probe existence in priority order
  for cand in main master development; do
    if git rev-parse --verify --quiet "origin/$cand" >/dev/null; then
      echo "$cand"; echo "source=probe:origin/$cand" >&2; return
    fi
  done
  # 5. last resort: current branch (warn it's a guess)
  b=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  echo "$b"; echo "source=current-branch-GUESS (verify this!)" >&2
}
DEFAULT_BRANCH=$(detect_default_branch)
```

> WARNING (field-observed): on the stock repo probe 1 FAILS
> (`fatal: ref refs/remotes/origin/HEAD is not a symbolic ref`) and the current
> branch was `experiment/strategy-optimization` — NOT the default. Probe 5 alone
> would have guessed wrong. Probe 2 (`git remote show origin`) resolved `master`.
> Never short-circuit to the current branch; always run the full chain.

Also record whether a GitHub remote exists (gates PR-dependent stages):

```bash
HAS_GITHUB=$(git remote -v | grep -c 'github\.com')   # 0 ⇒ gh stages will PR_SKIPPED
```

**Self-heal (optional, `--apply` only, only with a github remote, only if probe 1
failed but a branch resolved):** offer to set origin/HEAD so future detection
resolves directly via probe 1:

```bash
git remote set-head origin -a   # makes refs/remotes/origin/HEAD point at the default
```

Print this as a SUGGESTED action in the plan; only execute under `--apply` after
the branch is confirmed.

#### 1.2 Test / lint / format / build commands

Probe sources in order; first that yields a command for a slot wins. **Record the
SOURCE for each.** If nothing is found, leave the slot EMPTY with a `_note` —
never guess a concrete command.

```bash
have() { command -v "$1" >/dev/null 2>&1; }
mk_target() { [ -f Makefile ] && grep -Eq "^$1:" Makefile; }    # Makefile target exists?
pkg_script() { [ -f package.json ] && grep -Eq "\"$1\"[[:space:]]*:" package.json; }

# TEST
if   mk_target test;            then TEST="make test";          TEST_SRC="Makefile:test";
elif pkg_script test;           then TEST="npm test";           TEST_SRC="package.json:scripts.test";
elif [ -f Cargo.toml ];         then TEST="cargo test";         TEST_SRC="Cargo.toml";
elif [ -f pyproject.toml ] || [ -f tox.ini ] || [ -f pytest.ini ] || [ -d tests ]; then
                                     TEST="pytest";             TEST_SRC="python";   # or "python -m pytest"
elif [ -f go.mod ];             then TEST="go test ./...";      TEST_SRC="go.mod";
else                                 TEST="";                   TEST_SRC="none"; fi

# LINT
if   mk_target lint;            then LINT="make lint";          LINT_SRC="Makefile:lint";
elif pkg_script lint;           then LINT="npm run lint";       LINT_SRC="package.json:scripts.lint";
elif [ -f Cargo.toml ];         then LINT="cargo clippy";       LINT_SRC="Cargo.toml";
elif have ruff;                 then LINT="ruff check .";       LINT_SRC="ruff";
elif [ -f .flake8 ] || have flake8; then LINT="flake8";        LINT_SRC="flake8";
else                                 LINT="";                   LINT_SRC="none"; fi

# FORMAT
if   mk_target fmt || mk_target format; then
       FMT=$(mk_target fmt && echo "make fmt" || echo "make format"); FMT_SRC="Makefile";
elif pkg_script format;         then FMT="npm run format";      FMT_SRC="package.json:scripts.format";
elif [ -f Cargo.toml ];         then FMT="cargo fmt";           FMT_SRC="Cargo.toml";
elif have ruff;                 then FMT="ruff format .";       FMT_SRC="ruff";
elif [ -f .prettierrc ] || [ -f prettier.config.js ]; then FMT="npx prettier -w ."; FMT_SRC="prettier";
else                                 FMT="";                    FMT_SRC="none"; fi

# BUILD
if   mk_target build;           then BUILD="make build";        BUILD_SRC="Makefile:build";
elif pkg_script build;          then BUILD="npm run build";     BUILD_SRC="package.json:scripts.build";
elif [ -f Cargo.toml ];         then BUILD="cargo build --release"; BUILD_SRC="Cargo.toml";
elif [ -f pyproject.toml ];     then BUILD="python -m build";   BUILD_SRC="pyproject.toml";
elif [ -f go.mod ];             then BUILD="go build ./...";    BUILD_SRC="go.mod";
else                                 BUILD="";                   BUILD_SRC="none"; fi
```

**Multi-language repos** (the stock repo is one — Makefile **and**
`rust/Cargo.toml`): record ALL detected stacks. The **primary** stack is the one
whose root file is closest to repo root / referenced by the Makefile. Use the
primary command for each stage by default. List secondary stacks in the plan and
let the user opt into chaining (e.g. `make test && (cd rust && cargo test)`) —
**do not silently pick a partial command.** On the stock repo this yields
test → `make test` (Makefile `test:` at line 159), with `cargo test` listed as a
secondary stack to optionally chain.

Also detect a venv path for the shared skill's Configuration-Gathering step:

```bash
for v in .venv venv; do [ -d "$v" ] && VENV="$v" && break; done
[ -z "$VENV" ] && [ -f .python-version ] && VENV=".python-version"
```

#### 1.3 ROADMAP — locate and classify format

Use the SAME candidate order `pipeline.py` uses (`ROADMAP.md`, then
`docs/roadmap.md`, then `docs/ROADMAP.md`), so init and the parser agree on which
file is authoritative:

```bash
ROADMAP=""
for f in ROADMAP.md docs/roadmap.md docs/ROADMAP.md; do
  [ -f "$f" ] && ROADMAP="$f" && break
done
```

Classify (drives Step 4). The PIPELINE/FOREIGN test must mirror the REAL parser,
not a looser grep:

- **PIPELINE** (already conforms) — has a Priority-Matrix header line containing
  ALL of `Priority`, `Feature`, AND `Why` (this is exactly what
  `parse_priority_matrix` requires — see Anti-patterns), AND at least one
  `### Milestone: v<digits.dots> — Title` heading.
  ```bash
  grep -Eq 'Priority.*Feature.*Why|Feature.*Priority.*Why|Why.*Priority.*Feature' "$ROADMAP" \
    && grep -Eq '^###[[:space:]]+Milestone:[[:space:]]+v[0-9.]+[[:space:]]*[—–-]' "$ROADMAP"
  ```
- **FOREIGN** (exists but non-conforming) — present but missing either of the
  above. The stock repo is FOREIGN: `## Active work / ## Completed / ## Backlog`,
  numbered `### N. Title \`[x]\`` items, `[ ]/[~]/[x]` checkboxes, no matrix, no
  `vX.Y.Z`.
- **ABSENT** — none of the three paths exist.

#### 1.4 Existing pipeline scaffolding (idempotency inputs)

Detect presence of each so already-correct artifacts are left untouched:
`.pipeline-state/`, `.pipeline-templates/` (and which of feature/bugfix/refactor/
ship templates), `.gitignore` entries for `.pipeline-state/` and
`.pipeline-log.md`, root `CHANGELOG.md`, `RETRO.md` (and whether it has an
`## Action Tracker` table), `pr/feedback/`, `docs/adr/`, `docs/strategy-sessions/`,
`scripts/pipeline-gates.sh`, a PR-checklist file
(`docs/PULL_REQUEST_CHECKLIST.md`), and any `<!-- pipeline-config -->` block in
the **repo-root** `CLAUDE.md`.

#### 1.5 Version / tag scheme

```bash
NTAGS=$(git tag --list | grep -Ec '^v[0-9]+\.[0-9]+\.[0-9]+' )
```

If no `vX.Y.Z` tags AND no version field in `pyproject.toml` / `Cargo.toml` /
`package.json`, record `version_scheme: none` and seed the scaffold/migration
baseline at `--base-version` (default `v0.1.0`). On the stock repo: 0 tags → seed
`v0.1.0`. This is a CHOSEN default, not derivable — say so in the plan (see
Ambiguities). NOTE the parser's milestone regex is `v[\d.]+` (digits and dots
only) — `--base-version` MUST be of the form `vN.N.N`; a suffix like `v0.1.0-rc`
will NOT parse. Reject such input.

#### 1.6 Changelog convention

```bash
if   [ -f CHANGELOG.md ];                     then CHANGELOG_CONV="existing";
elif [ -f release-please-config.json ] || grep -q '"release-please' package.json 2>/dev/null; then
                                                   CHANGELOG_CONV="release-please";
elif [ -f Cargo.toml ] && grep -q cargo-release Cargo.toml 2>/dev/null; then
                                                   CHANGELOG_CONV="cargo-release";
else                                               CHANGELOG_CONV="keep-a-changelog"; fi
# --changelog overrides; --changelog none disables CHANGELOG creation + relaxes the two-commit gate.
```

The two-commit CHANGELOG boundary baked into the canonical templates only makes
sense when the repo HAS a changelog you commit by hand. When `CHANGELOG_CONV` is
`none`, `release-please`, or `cargo-release` (changelog generated by tooling, not
hand-edited per PR), skip CHANGELOG.md creation and note in the plan that the
template's Stage "Documentation" CHANGELOG item may not apply — leave the template
item but flag it for the user. Do not silently force a stock-derived convention.

#### Detection record format (print this)

```
DETECTION RECORD
  default_branch : <branch>        (source: <probe>)        [github remote: yes/no]
  pr_target      : <branch>        (= default unless --pr-target)
  test_command   : <cmd or "(none — fill in)">   source: <src>
  lint_command   : <cmd or "(none)">             source: <src>
  format_command : <cmd or "(none)">             source: <src>
  build_command  : <cmd or "(none)">             source: <src>
  stacks         : <primary> [+ secondary: <...>]
  venv_path      : <path or "(none)">
  ROADMAP        : <path or ABSENT> — format: PIPELINE | FOREIGN | ABSENT
  version_scheme : none → seed <base-version>   (or: <existing>)
  changelog      : <existing | keep-a-changelog | release-please | cargo-release | none>
  pipeline-skill : <PIPELINE_SKILL_DIR or dir-containing-pipeline.py, for template source>
  scaffolding    : .pipeline-state/[Y/N] .pipeline-templates/[which] gitignore[Y/N]
                   CHANGELOG[Y/N] RETRO[Y/N + tracker?] pr/feedback[Y/N]
                   docs/adr[Y/N] docs/strategy-sessions[Y/N] CLAUDE.md-config[Y/N]
```

### 2. Create directories and gitignore (`--apply`)

**Idempotent:** skip-if-present-and-correct; never clobber user content without a
timestamped backup.

```bash
mkdir -p .pipeline-state   # CONTENTS are ephemeral/gitignored; pipeline-next recreates on demand
```

Do NOT add a `.gitkeep` to `.pipeline-state/`: the gitignore rule `.pipeline-state/`
would ignore the gitkeep too, so it would not be committable anyway — and the
canonical setup treats the dir as purely ephemeral. The dir is recreated by
`pipeline-next`/`pipeline-run` when needed.

Append to `.gitignore` ONLY the lines not already present:

```bash
for line in '.pipeline-state/' '.pipeline-log.md'; do
  grep -qxF "$line" .gitignore 2>/dev/null || echo "$line" >> .gitignore
done
```

> Do NOT gitignore `.pipeline-templates/`, `RETRO.md`, `CHANGELOG.md`,
> `docs/adr/`, or `docs/strategy-sessions/` — those are **committed**. Only
> `.pipeline-state/` contents and `.pipeline-log.md` are ephemeral/per-checkout.

Create empty support dirs (unless `--minimal`):

```bash
mkdir -p pr/feedback docs/adr docs/strategy-sessions
for d in pr/feedback docs/adr docs/strategy-sessions; do touch "$d/.gitkeep"; done
```

### 3. Install the state templates by COPYING the canonical ones (`--apply`)

**Do NOT hand-write stage skeletons.** Locate the canonical templates and copy
them, substituting only the detected values. This is the ONLY way to stay in sync
with the real per-type stage shapes (feature 14 / bugfix 12 / refactor 12 /
ship 10) and the conventions pipeline-run/shared reference (`-plan.md` for
feature, `-diagnosis.md` for bugfix, the Re-Review / address-findings loop folded
into Review Verdict, etc.).

```bash
# Resolve the canonical template source.
SKILL_DIR="${PIPELINE_SKILL_DIR:-$(dirname "$(command -v pipeline.py 2>/dev/null || find ~ -maxdepth 6 -name pipeline.py -path '*pipeline-skill*' 2>/dev/null | head -1)")}"
SRC="$SKILL_DIR/templates"
test -f "$SRC/feature-state.json" || { echo "ERROR: canonical templates not found under $SRC — set PIPELINE_SKILL_DIR"; exit 1; }
mkdir -p .pipeline-templates
```

For each of `feature`, `bugfix`, `refactor` (plus `ship` only with `--with-ship`):

1. **Copy** `$SRC/<type>-state.json` → `.pipeline-templates/<type>-state.json`
   (skip if an identical file already exists — idempotent).
2. **Substitute the detected branch.** The canonical templates set top-level
   `"pr_target_branch": "main"` and reference `{pr_target_branch}` inside
   checklist actions / subagent prompts (verified: only `{pr_target_branch}`
   placeholders, no literal `origin/main`). Replace the top-level value with the
   detected branch (and add a `default_branch` key for skills that read it):

   ```bash
   for t in feature bugfix refactor; do
     dst=".pipeline-templates/${t}-state.json"
     python3 - "$dst" "$DEFAULT_BRANCH" "$PR_TARGET" "$TEST" "$LINT_FMT" <<'PY'
import json, sys
dst, default_branch, pr_target, test_cmd, lint_fmt = sys.argv[1:6]
d = json.load(open(dst))
d["pr_target_branch"] = pr_target or default_branch
d["default_branch"]   = default_branch          # additive; harmless to skills that ignore it
# Inject detected commands into stages BY NAME (numbering differs across types).
for sid, st in d["stages"].items():
    nm = st.get("name", "")
    if nm == "Test Execution" and test_cmd:
        st["checklist"].insert(0, {"action": test_cmd, "done": False,
                                   "_note": "detected test command (pipeline-init)"})
    if nm in ("Self-Review", "Regression Check", "Review") and lint_fmt:
        st["checklist"].insert(2, {"action": f"{lint_fmt} on staged files", "done": False,
                                   "_note": "detected lint+format command (pipeline-init)"})
json.dump(d, open(dst, "w"), indent=2)
PY
   done
   ```

   - `$PR_TARGET` defaults to `$DEFAULT_BRANCH` unless `--pr-target` was given.
   - `$LINT_FMT` is the detected lint and/or format command (joined with `&&` if
     both detected); if neither detected, leave it empty and do NOT insert the
     item (a wrong concrete command is worse than a blank — the canonical
     Self-Review already has generic quality checks).
   - If `$TEST` is empty, do NOT insert a test item; the canonical "run full test
     suite" item remains and the user fills the real command via the CLAUDE.md
     config block (Step 6). NEVER substitute a guessed concrete command.

3. **Stage injection is keyed by stage NAME, not number** — bugfix's test stage
   is at a different index than feature's, and bugfix uses `Regression Check`
   instead of `Self-Review`. The script above looks up `Test Execution`,
   `Self-Review`/`Regression Check`/`Review` by name so it works across all three
   types.

> The detected branch and commands are the ONLY repo-specific values written into
> these files. Everything else comes verbatim from the canonical template — so
> the per-type stage shapes, the Re-Review/address-findings loop (folded into
> Review Verdict in the canonical templates), and every gate stay exactly as
> pipeline-run/shared expect.

Also write `.pipeline-templates/README.md` documenting precedence:
project-local templates OVERRIDE the **skill-default** templates in the
pipeline-skill's `templates/` directory (resolved via `PIPELINE_SKILL_DIR` or the
directory containing `pipeline.py` — NOT `~/.claude/skills/...`); `pipeline-next`
checks project-local first. Note that `.pipeline-templates/` is committed (so the
team shares it) while `.pipeline-state/` contents and `.pipeline-log.md` are
gitignored (per-checkout).

> If the canonical templates cannot be located (no `PIPELINE_SKILL_DIR`, no
> `pipeline.py` on disk), STOP and tell the user to set `PIPELINE_SKILL_DIR` —
> do NOT fall back to hand-written skeletons, which would get the bugfix/refactor
> shape wrong.

### 4. Handle the ROADMAP (`--apply`; dry-run prints the full proposed result)

Driven by the Step 1.3 classification. The output MUST parse under the REAL
`pipeline.py` parser. The parser's hard requirements (verified against
`parse_priority_matrix` / `parse_roadmap`):

- The Priority-Matrix table is only read once a line contains ALL of `Priority`,
  `Feature`, AND `Why`. A header without `Why` is invisible → every task silently
  defaults to **P2**. Use a header with those three column names.
- The matrix must be the FIRST content section (the spec's "table at the top of
  the file"); emit it before any `### Milestone:` heading.
- Milestone headings match `###\s+Milestone:\s+(v[\d.]+)\s*[—–-]\s*Title` — the
  version is digits/dots only (no `-rc` suffix), and the separator may be em-dash,
  en-dash, or hyphen.
- A feature is ANY line that, inside a milestone, starts with `**...**`. This
  means stray bold lead-ins in preserved prose (`**Plan:**`, `**Files:**`,
  `**Done …:**`) become PHANTOM features. De-bold them when preserving spec text.
- Reserved `## ` sections are skipped: `completed`, `future`, `post-1.0`,
  `contributing`, `investigate`, `differentiators`, `parity tracker`,
  `priority matrix` (matched as substrings of the lowercased h2 heading).
- Priority is joined from the matrix to the milestone feature by name: exact
  (normalized: backticks stripped, lowercased, whitespace collapsed) FIRST, then
  ≥2-significant-word overlap. To guarantee the join, use a BYTE-IDENTICAL
  feature-name string in the matrix `Feature` cell and the `**Bold**` milestone
  entry.
- Type is `bugfix` when the spec's first 200 chars contain `broken`, `fails`,
  `regression`, `crash`, or `fix:`, OR the feature name's first 20 chars contain
  `fix`; else `feature`.

#### 4.1 PIPELINE → leave it

Already conforms. Optionally run a structural lint (warn if the matrix and
milestone sections disagree). No migration.

#### 4.2 ABSENT → scaffold a minimal conforming ROADMAP at `ROADMAP.md`

Matrix FIRST, with the parser-required `Why` column; use `<base-version>` (default
`v0.1.0`). The matrix `Feature` cell and the `**Bold**` milestone entry use the
IDENTICAL string `First task`:

```markdown
# Project ROADMAP

## Priority Matrix

| Priority | Feature | Why | Milestone |
|----------|---------|-----|-----------|
| **P1** | First task | Replace with a real reason. `some_function()` (#1) | <BASE_VERSION> |

### Milestone: <BASE_VERSION> — Initial milestone

**First task**
Describe the first task. Embed greppable hooks like `ClassName`,
`function_name()`, file paths, and `(#NNN)` so /pipeline-roadmap-audit can verify
it. Do NOT start any line in this spec with `**bold**` — that would register as a
separate phantom feature.

### Completed

### Future
```

#### 4.3 FOREIGN → migrate in place (the stock-repo case), backing up first

**Always back up first** (even in `--apply`): copy the original to
`ROADMAP.md.bak-<UTC-timestamp>` before writing. In `--dry-run`, print the full
proposed migrated file for review and write nothing.

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
cp "$ROADMAP" "${ROADMAP}.bak-${TS}"   # --apply only
```

**Emit the Priority Matrix as the FIRST content section** (before any
`### Milestone:`), with the parser-required header
`| Priority | Feature | Why | Milestone |`.

Apply these deterministic mapping rules:

| Source element | Migrated to |
|---|---|
| `\`[x]\`` item (done) | a `### Completed` narrative line; if it had a matrix row, write it struck-through shipped: `\| ~~**Px**~~ \| ~~<name>~~ ✅ Shipped in PR #NNN (\`<path>\`) \| ~~<why>~~ \| ~~<ver>~~ \|` when a PR/path ref is recoverable, else `✅ Shipped (migrated from ROADMAP item N; no PR ref)` carrying the existing `Done <date>` note verbatim. NOT selectable by next (correct). |
| `\`[~]\`` item (in progress) | active selectable feature: plain matrix row + `**Feature**` entry under the active milestone, using the SAME byte-identical name in both |
| `\`[ ]\`` item (pending) | active selectable feature, same as in-progress (no "resume" marker — resume is tracked in `.pipeline-state/`, not the ROADMAP) |
| `## Active work` | split by status: `[x]` → `### Completed`; `[~]`/`[ ]` → active milestone detail |
| `## Completed` | `### Completed` (reserved; skipped by next — correct) |
| `## Backlog (not scheduled)` | `### Future` (reserved; skipped — correct) |
| `## How to update this file` | preserved verbatim under `### Contributing` (reserved; skipped) so the prose isn't lost |

**Name-join invariant (REQUIRED).** The string written into the matrix `Feature`
cell for an active item MUST be byte-identical to the `**Bold Name**` used for its
milestone detail entry — `pipeline.py` joins them by exact name (then fuzzy
overlap) to resolve priority. Pick ONE canonical name per active item (the
de-prefixed numbered-item title, e.g. `restore rust ↔ python parity`) and use
that identical string in both places. If they differ, the join falls back to
word-overlap and may attach the wrong priority or default to P2.

**Strikethrough refs are NOT audit-verified.** Migrated `✅ Shipped` rows are a
format conversion of pre-existing `[x]` markers, not an audit-confirmed shipped
status. When a `[x]` item carries no `#NNN`/path (the stock items 1–7 only have
`Done <date>` notes), write `✅ Shipped (migrated from ROADMAP item N; no PR ref)`
and keep the `Done <date>` text — do NOT fabricate a PR number. Optionally run a
best-effort `git log --all --grep=<keyword>` to recover a PR and mark it
`UNVERIFIED`. State this in the plan: migrated strikethrough = format conversion,
not audit-verified.

**Numbered `### N. Title` → one active milestone + features.** The numbered items
are work items, NOT versions. Collapse them into ONE active milestone whose
version comes from Step 1.5 (no tags → `v0.1.0`): heading `### Milestone:
<base-version> — Active work`. Each numbered item becomes a `**Title**` feature
inside it (or a `### Completed` line if `[x]`). Drop the numeric prefix from the
bold name (carries no priority) but preserve it in the spec text as "(was roadmap
item N)" for traceability.

**De-bold preserved prose to avoid phantom features.** When copying an item's body
into the feature's spec text, REFLOW every leading `**Label:**` marker so no spec
line starts with `**...**`. The stock body has `**Context …:**`, `**Bugs to fix
…:**`, `**Plan:**`, `**Acceptance:**`, `**Files:**` — each of these, left bold
under an active milestone, would register as a SEPARATE phantom feature
(`/pipeline-next --list` would show bogus tasks "Plan", "Acceptance", "Files").
Demote them to plain `Label:` (or indent as sub-bullets):

```bash
# turn a leading "**Label:**" into "Label:" (only at line start)
sed -E 's/^[[:space:]]*\*\*([^*]+):\*\*/\1:/'
```

**Derive priority (source has none — apply to active `[~]`/`[ ]` items only).**
Deterministic heuristic; print the assigned priority + the trigger word for each
item so the user can override (or supply `--priority-map`):

- **P0** if the title/body contains `security`, `CVE`, `crash`, `data loss`,
  `broken`, `regression`.
- **P1** if status `[~]`, OR title/body mentions `fix`, `bug`, `accuracy`,
  `parity`, `restore`, `incorrect`.
- **P2** = default for ordinary pending features (`[ ]`, no other signal).
- **P3** = "nice to have", "someday", "backlog", "investigate".

**Derive type honestly (match the parser's `is_bugfix` rule).** The parser will
classify a feature as `bugfix` when its spec's first 200 chars contain `broken`,
`fails`, `regression`, `crash`, or `fix:`, OR its name's first 20 chars contain
`fix`. Predict this in the plan. For the stock repo, item 8's body contains
`broken` and `Bugs to fix`, so **the parser classifies it as `bugfix`** —
`/pipeline-next` will copy `bugfix-state.json` (the 12-stage Diagnosis/Fix/
Regression-Check template). Do not claim it is a "feature"; the migration's
type-derivation must agree with the parser.

**Preserve prose as spec text:** copy the entire body under each numbered item
(the file paths, `docs/...` refs, sub-bullets) into the feature's spec text after
de-bolding lead-in labels — these become the audit's greppable verification hooks
for free.

**Expected migrated shape for the stock repo:** a Priority-Matrix table
(`| Priority | Feature | Why | Milestone |`) as the first section, with items 1–7
as struck-through `✅ Shipped (migrated …; no PR ref)` rows and item 8 a plain
`| **P1** | restore rust ↔ python parity | … | v0.1.0 |`; one `### Milestone:
v0.1.0 — Active work` with item 8 as the sole active `**restore rust ↔ python
parity**` feature (its `[~]` prose preserved, all `**Label:**` lead-ins
de-bolded); `### Completed` holding items 1–7 plus the existing Completed
entries; `### Future` from the backlog; and `### Contributing` from "How to
update this file". This parses under `pipeline.py`, so `/pipeline-next --list`
returns item 8 as the selectable task — classified **bugfix**, priority **P1**.

### 5. Scaffold CHANGELOG / RETRO (`--apply`)

**`CHANGELOG.md`** (root) — only if absent AND the changelog convention (Step 1.6
/ `--changelog`) is `keep-a-changelog` or `existing`. If the convention is `none`,
`release-please`, or `cargo-release`, skip creation and note that the template's
CHANGELOG item may not apply. Stage Documentation and the two-commit CHANGELOG
boundary assume a hand-edited changelog exists; default to Keep-a-Changelog (a
convention choice, not mandated — a repo with a different convention keeps it):

```markdown
# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]
```

**`RETRO.md`** (root) — needed by pipeline-retro / pipeline-strategy (skip with
`--minimal`). If absent, seed with the exact Action Tracker block:

```markdown
## Action Tracker

Items from retrospectives that need resolution. Every item must have a GitHub
issue or be explicitly closed with a reason.

| # | Action | Source | GitHub | Status | Notes |
|---|--------|--------|--------|--------|-------|

<!-- Milestone retro entry template:
## <milestone> — <date>
**Quality**: N/5 · **What went well**: … · **Lessons**: … · **Actions**: → tracker
-->
```

If a `RETRO.md` exists but lacks the Action Tracker table, back it up
(`RETRO.md.bak-<TS>`) and INSERT the table at the top.

### 6. Write the repo-root CLAUDE.md pipeline-config block (`--apply`) — the WIRED bridge

Append a fenced, marker-delimited block to the **repo-root** `CLAUDE.md`
(`<repo>/CLAUDE.md` — the file pipeline-shared's Configuration Gathering reads:
"Read CLAUDE.md in the project root"). Create it there if absent. NEVER touch the
user-global `~/.claude/CLAUDE.md`. Idempotent — replace the content between the
markers if the block already exists:

```markdown
<!-- pipeline-config: managed by /pipeline-init -->
## Pipeline configuration

- default_branch: <DETECTED>          # e.g. master
- pr_target_branch: <DETECTED>        # usually same as default_branch
- test_command: <DETECTED or "">      # e.g. make test
- lint_command: <DETECTED or "">
- build_command: <DETECTED or "">
- venv_path: <DETECTED or "">
- changelog: <keep-a-changelog | release-please | cargo-release | none>
<!-- /pipeline-config -->
```

This is what makes the family branch-agnostic on the WIRED path: pipeline-shared's
Configuration-Gathering and Environment-Check read `default_branch` /
`pr_target_branch` here (and from the template's `pr_target_branch`) and resolve
`origin/<default_branch>`.

### 6b. Default-branch wiring — honest WIRED vs REQUIRES-SKILL-CHANGE

Be explicit in the plan about how far the config reaches:

- **WIRED (no skill edit needed):** pipeline-shared's Environment-Check resolves
  the target via `pr_target_branch → default_branch → try main/master/development`.
  Writing the detected branch into `.pipeline-templates/*` (`pr_target_branch` /
  `default_branch`) and the CLAUDE.md block routes these skills to
  `origin/<detected>` with no skill change. Covers pipeline-shared and (via it)
  most of pipeline-run. **pipeline-ship** resolves the PR target via config
  (`pr_target_branch`/`default_branch`), so `master`/`main` work — BUT its
  on-branch detection (Step 0.4) only special-cases `main`/`master`; on a
  `development`-default repo confirm the working branch is not literally
  `development`.
- **REQUIRES-SKILL-CHANGE (init CANNOT fix from inside the host repo):** several
  skills contain a **literal `origin/main` / `main`** that does NOT consult config
  — on a non-`main` repo these target a nonexistent branch. Init must EMIT this
  warning verbatim so the user knows the residual gap:

  ```
  ⚠ REQUIRES-SKILL-CHANGE — these skills have literal `origin/main`/`main`
    that ignores the detected branch (<DEFAULT_BRANCH>). Edit them once in
    the pipeline-skill skills/ dir to read {default_branch} from CLAUDE.md/template:
      • pipeline-run     (git checkout -B {branch} origin/main; git log origin/main..main)
      • pipeline-retro   (git push origin main, Stage 6)
      • pipeline-drain   (git push origin main; --all to main)
      • pipeline-strategy (assumes `main`)
    The fix is "use the detected branch," whatever it is — do NOT special-case master.
  ```

  Init WIRES everything it can via config and emits this one-line warning. It does
  not edit the pipeline-skill source.

### 6c. Optional: gates stub (`--with-gates`) and ship template (`--with-ship`)

- `--with-gates` → write `scripts/pipeline-gates.sh`: one shell function per hard
  gate (changelog-boundary, etc.), commands parameterized by the detected branch +
  test command. If not created, the run skill inlines the bash one-liners (its
  documented fallback), so this is optional.
- `--with-ship` → also COPY `$SRC/ship-state.json` (10 stages: Inventory Changes,
  Test Execution, Self-Review, Security Check, Documentation, Commit & PR, Code
  Review, Review Verdict, Merge PR, Retrospective) into `.pipeline-templates/`,
  substituting `pr_target_branch` exactly as in Step 3. Do NOT hand-write it.

### 7. Verify (final step, both modes — see "How to verify")

## --dry-run vs --apply behavior

- **`--dry-run` (DEFAULT)** — print the detection record + the ordered plan of
  every file/dir it WOULD create/modify, including the complete proposed migrated
  ROADMAP and each template's injected commands. Change NOTHING on disk. Write no
  backups (nothing is touched). Print the projected verification report.
- **`--apply`** — execute the plan. Always back up any file it rewrites (ROADMAP,
  an existing RETRO lacking a tracker) to `<file>.bak-<UTC-timestamp>` BEFORE
  writing. Run the real verification report at the end.
- **`--branch <name>`** — override the detected default branch. Written as both
  `default_branch` and `pr_target_branch` unless `--pr-target` is also given.
- **`--pr-target <name>`** — set `pr_target_branch` independently of
  `default_branch`.
- **`--base-version vX.Y.Z`** — seed milestone/scaffold version (default `v0.1.0`;
  must be `vN.N.N`, no suffix, to satisfy the parser's `v[\d.]+` regex).
- **`--changelog keep-a-changelog|none`** — changelog convention override.
- **`--priority-map <file>`** — explicit `feature→priority` overrides for
  migration (lines like `restore rust ↔ python parity: P0`).
- **`--with-ship` / `--with-gates` / `--minimal`** — as above.
- **Idempotent + re-runnable** — every action is skip-if-already-correct.
  Re-running on a fully-initialized repo prints "already initialized — nothing to
  do" and exits 0. Re-running after partial init completes only the missing pieces.

## Anti-patterns to avoid

- **Hand-writing the state templates** — COPY the canonical ones and substitute
  detected values. feature=14 / bugfix=12 / refactor=12 / ship=10 stages with
  DIFFERENT structure (bugfix is Diagnosis/Fix/Regression Check with
  `-diagnosis.md`; refactor is Analysis/Refactor Execution/Review). A hand-written
  14-stage skeleton for bugfix/refactor diverges from what pipeline-run/shared
  reference.
- **Hard-coding `origin/main` / `master` / `make test`** — always detect. The
  stock repo's default was `master` (no `origin/HEAD` symbolic ref); the next
  repo's may be `main` or `development`. The skill must contain only detection
  logic and generic fallbacks.
- **Short-circuiting branch detection to the current branch** — on the stock repo
  the current branch was `experiment/strategy-optimization`, not the default. Run
  the full resolution chain.
- **Emitting a Priority Matrix without a `Why` column** — `parse_priority_matrix`
  only enters the table when the header has `Priority` AND `Feature` AND `Why`. A
  `Description` column instead of `Why` makes the whole matrix invisible and every
  task silently defaults to P2.
- **Leaving bold `**Label:**` lead-ins in preserved spec prose** — any `**...**`
  line under a milestone registers as a feature, so `**Plan:**`/`**Files:**`
  become phantom tasks. De-bold them.
- **Different names in the matrix cell vs the `**Bold**` entry** — the parser
  joins priority by exact name first; mismatched strings attach the wrong
  priority or default to P2. Use one byte-identical string.
- **A milestone version with a suffix** — `v0.1.0-rc` fails the parser's
  `v[\d.]+` regex. Use `vN.N.N`.
- **Overwriting a ROADMAP without backing it up** — always `cp` to
  `ROADMAP.md.bak-<TS>` before migrating; in `--dry-run`, print, don't write.
- **Fabricating a PR ref for migrated `✅ Shipped` rows** — when no `#NNN`/path
  exists, write `(migrated from ROADMAP item N; no PR ref)`. A fabricated ref is
  worse than none (roadmap-audit distrusts unverified SHIPPED claims).
- **Guessing a test/lint command when detection found none** — leave it out (the
  canonical template keeps a generic "run full test suite" item). A wrong concrete
  command is worse than a blank.
- **Gitignoring `.pipeline-templates/`** (it's committed) or **committing
  `.pipeline-state/` contents** (ephemeral) or `.pipeline-log.md`. Do not add a
  `.gitkeep` to `.pipeline-state/` — the gitignore rule would ignore it anyway.
- **Treating migrated priorities as authoritative** — they're a keyword
  heuristic; surface them for review (`--priority-map`).
- **Silently chaining multi-stack commands** — use the primary stack's command;
  list secondaries and let the user opt into chaining.
- **Forcing the two-commit CHANGELOG gate on a no-changelog repo** — gate it on
  the detected changelog convention.
- **Writing the config block to `~/.claude/CLAUDE.md`** — always write the
  repo-root `<repo>/CLAUDE.md`.
- **Special-casing `master`** in the REQUIRES-SKILL-CHANGE fix — the fix is "use
  the detected branch," whatever it is.

## When to run

- First-time setup of a repo that has never used the pipeline family.
- After cloning a repo that lacks `.pipeline-templates/` / a conforming ROADMAP.
- To repair a partially-set-up repo (re-run; it completes only the missing pieces).

## Observed cost in the field

On the stock repo, the failure was total: the ROADMAP was in `### N. Title \`[x]\``
checkbox format under `## Active work / ## Completed / ## Backlog` with no Priority
Matrix the parser could read and no `vX.Y.Z` milestones, and there was no
`.pipeline-templates/`. So `/pipeline-next --list` found zero tasks and
`/pipeline-run` had no state file to copy — the entire family was blocked. The
default branch was `master` with **no** `origin/HEAD` symbolic ref, so naive
`git symbolic-ref` detection alone would have failed (and the checked-out branch
was an unrelated experiment branch, so guessing the current branch would have been
wrong too). Only the full resolution chain — falling through to
`git remote show origin` — recovered `master`. There were 0 tags, so migration had
to invent a version baseline (`v0.1.0`) and say so. Subtle traps the parser would
have sprung if migration were naive: a `Description` column instead of `Why` (the
whole matrix would be invisible → all tasks P2); the active item's body bold
lead-ins (`**Plan:**`, `**Files:**`) becoming phantom tasks; and the active item
("restore rust ↔ python parity") classifying as **bugfix** (its body says
"broken" / "Bugs to fix"), so the bugfix 12-stage template must be installed, not
a 14-stage feature one.

## How to verify

After `--apply` (or as the projected outcome under `--dry-run`), self-check and
print a PASS/FAIL report. The authoritative ROADMAP check is to RUN THE REAL
PARSER, not greps — greps give false-greens (they match surface text the parser
rejects). Greps are a cheap pre-check only.

1. **Template parse** — each `.pipeline-templates/*-state.json` parses, has
   `pipeline_type`, `stages` keyed `"1".."N"` in order, each stage has
   `name`/`status`/`verdict`/`checklist`, and `pr_target_branch == <detected>`.
   Use whatever JSON parser the detected stack provides (don't assume python3 on a
   JS/Rust repo); skip gracefully with a NOTE if none is on PATH:
   ```bash
   parse_json() {
     if command -v python3 >/dev/null; then python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$1";
     elif command -v node >/dev/null; then node -e "JSON.parse(require('fs').readFileSync(process.argv[1]))" "$1";
     elif command -v jq >/dev/null;   then jq -e . "$1" >/dev/null;
     else echo "NOTE: no JSON parser on PATH — template validity not checked"; return 0; fi
   }
   for f in .pipeline-templates/*-state.json; do parse_json "$f" && echo "OK $f" || echo "FAIL $f"; done
   ```
2. **gitignore** — `.pipeline-state/` and `.pipeline-log.md` present:
   ```bash
   grep -qxF '.pipeline-state/' .gitignore && grep -qxF '.pipeline-log.md' .gitignore && echo IGNORE_OK
   ```
3. **ROADMAP conformance — run the actual parser (the real end-to-end gate):**
   ```bash
   python "$SKILL_DIR/pipeline.py" auto --project . --list   # or: import parse_roadmap
   ```
   Assert it returns ≥1 task with the expected name/priority/type. On the stock
   repo this must surface migrated item 8 — name "restore rust ↔ python parity",
   priority **P1**, type **bugfix** — and NOT surface phantom tasks ("Plan",
   "Files", "Acceptance"). Keep these greps ONLY as a cheap pre-check:
   ```bash
   grep -Eq 'Priority.*Feature.*Why' ROADMAP.md          # parser-readable matrix header
   grep -Eq '^###[[:space:]]+Milestone:[[:space:]]+v[0-9.]+[[:space:]]*[—–-]' ROADMAP.md
   ```
4. **Branch sanity** — `git rev-parse --verify origin/<detected>` succeeds (warn,
   don't fail, if there's no github remote — PR stages will `PR_SKIPPED`).
5. **Print the next command:**
   `Run /pipeline-next --list to confirm tasks are discoverable, then /pipeline-run to execute.`

### Unresolved ambiguities (surface these in the report)

1. **Literal `origin/main` in four skills** — WIRED via config for shared/ship
   (ship's PR target only; its on-branch detection still special-cases
   main/master); REQUIRES-SKILL-CHANGE for pipeline-run/retro/drain/strategy (see
   §6b). Init wires what it can and warns about the rest.
2. **Version scheme** — no tags ⇒ init invents `v0.1.0` (chosen, not derivable).
   Use `--base-version` (must be `vN.N.N`, no suffix).
3. **CHANGELOG format/applicability** — unspecified by the skills; init defaults
   to Keep-a-Changelog and gates both the file AND the two-commit boundary on the
   detected convention. A repo using release-please/cargo-release/none keeps its
   own.
4. **Migration priorities** — heuristic; review via `--priority-map`.
5. **Multi-language command synthesis** — default to the primary stack; list
   secondaries; opt into chaining.
6. **RETRO/adr/strategy-session dirs** — required by retro/strategy, degrade
   gracefully; created by default, skipped with `--minimal`.
