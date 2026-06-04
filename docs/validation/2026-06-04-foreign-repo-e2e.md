# Foreign-repo validation (end-to-end) — 2026-06-04

Second outward validation (v0.6.0), this time covering the **PR-dependent stages**
the v0.5.0 local-only run could not exercise. Deliverable: this report + any gaps
filed as issues.

## Method

Created a real throwaway private GitHub repo,
`johnrtipton/pipeline-skill-foreign-validation`, deliberately foreign:

| Dimension | pipeline-skill | validation repo |
|-----------|----------------|-----------------|
| default branch | `main` | **`master`** (set as the GitHub default) |
| stack | Python (stdlib) | **Node** (`package.json`, `npm test`) |
| version | none | `3.1.0` |
| ROADMAP | conforming | **checkbox format**, then migrated |

Ran the full family: detection → `pipeline-init` scaffold → `pipeline-next` →
`pipeline-run` (implement → **real PR → review → merge**) on `master`.

## Results

| Stage | Result | Verdict |
|-------|--------|---------|
| `detect_default_branch` | `master` (origin/HEAD=master) | ✅ — the #45 fix holds on a real remote |
| `detect_profile` | `generic` | ✅ |
| ROADMAP migration (checkbox → priority-matrix) | parser then found 1 task (`greeting helper`, P2) | ✅ |
| `pipeline-init` config | `default_branch: master` written + read back | ✅ |
| Implementation + branch off `master` | `feat/greeting-helper` created, `hello()` added | ✅ |
| **`gh pr create --base master`** | **PR #1 created targeting `master`** | ✅ — the stage v0.5.0 couldn't test |
| `npm test` (foreign `test_command`) | passed | ✅ |
| Code Review + **`gh pr merge --squash`** | **PR #1 merged into `master`** | ✅ |

**No blocking family gaps this run.** With the #45 fix in place, branch
resolution was correct throughout, and every PR-dependent stage (create against
`master`, review, squash-merge) worked on a non-`main`/non-python repo. This is
the end-to-end confirmation the outward pivot was aiming for: the prior milestone
*found* the branch bug; this milestone *fixed it and proved the full loop on a
genuinely foreign repo*.

## Non-family note

The only friction was operator-side: the Claude Code Bash-tool shell runs with
zsh `noclobber` ON (harness default, not configurable), so `cat > existing_file`
silently no-ops. Mitigated by using the Write/Edit tools. Not a pipeline-family
issue.

## Scope still open

A foreign repo with a CI workflow + branch-protection (required checks) was not
exercised — the validation repo had no CI gate, so merges weren't blocked on
checks. A future validation could add a required-check gate and confirm the merge
stage waits on it. (Relates to the v0.5.0 observation that this repo's own CI is
advisory, not required.)

## Outcome

End-to-end family run on a foreign `master`/Node repo: all stages green, PR #1
merged. 0 new blocking gaps. Throwaway repo
`johnrtipton/pipeline-skill-foreign-validation` can be deleted now that it has
served its purpose.
