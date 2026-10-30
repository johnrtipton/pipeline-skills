---
name: pipeline-review
description: >
  Review someone else's GitHub pull request end to end, and post the review only after the user
  approves it. Use this whenever the user shares a PR link or number and wants it reviewed, checked,
  looked over, approved, or judged ready to merge ("review this PR", "can you look at #412", "is
  owner/repo#88 good to merge?", "did we finish reviewing that PR?"), including infrastructure and
  config PRs whose effects reach other repos. It verifies the PR's claims at their source, checks
  who consumes the change, accepted decision records, open neighbour PRs, CI and branch rules, then
  drafts an approve, request-changes or comment review. Not for shipping your own working tree
  (use /pipeline-ship) or for reviewing a local branch that has no PR.
---

# pipeline-review

Review a pull request that someone else wrote, the way a careful senior reviewer would: read it,
check that what it says is true, work out what it breaks elsewhere, and post one clear review that
the author can act on. The user decides whether and how it is posted.

## Usage

```
/pipeline-review <pr>                # review, draft, ask, then post
/pipeline-review <pr> --no-post      # stop at the draft; the user posts it
/pipeline-review <pr> --resume       # continue an interrupted review from its state file
/pipeline-review <pr> --focus "<text>"   # weight one concern, e.g. "the migration"
```

## Arguments

| Argument | Meaning |
|---|---|
| `<pr>` | A PR URL (`https://github.com/<owner>/<repo>/pull/<n>`, any suffix such as `/changes` or `/files`), `<owner>/<repo>#<n>`, or `<n>` for the repo of the current checkout |
| `--no-post` | Stage 8 posts nothing. `draft.md` is the deliverable |
| `--resume` | Read the existing state file and continue at its `current_stage` |
| `--focus` | A concern to weight in stages 4 and 5. It narrows nothing else |

## How it works

The stages live in a state file that you tick off on disk, as in every pipeline skill: a long
review reads dozens of files and the instructions you started with fade. Before each stage, read the
state file again; after each checklist item, mark it done and write the file. If you are unsure what
an item asks, read this skill again instead of guessing.

### Step 0: Workspace and state file

A review is about a remote PR, not your working tree, so it gets its own workspace:

```bash
PIPELINE_DIR="${PIPELINE_SKILL_DIR:-$(dirname "$(dirname "$(readlink -f ~/.claude/skills/pipeline-review)")")}"
WS="${PIPELINE_REVIEW_DIR:-$HOME/.pipeline-reviews}/<owner>__<repo>__<n>"
RS="$PIPELINE_DIR/skills/pipeline-review/scripts/review_state.py"
mkdir -p "$WS/notes"
python3 "$RS" init "$WS/state.json" --template "$PIPELINE_DIR/templates/review-state.json" \
  --pr-url <url> --repo <owner/repo> --number <n> [--no-post]
```

- If `$WS/state.json` exists and `--resume` was not given, `init` refuses. Tell the user that a
  review of this PR exists and ask whether to resume it or start again.
- The workspace holds `state.json`, the clone in `repo/`, evidence in `notes/`, the review body in
  `draft.md`, and any helper file you write. Keep every file of the review inside `$WS`, never in
  a shared scratch folder: two reviews running at once must not write into each other's files.

`pipeline.py` has no `review` type yet, so `review_state.py` builds the state file from the template.

### Step 1: The stage loop

`review_state.py` is the only thing that edits `state.json`. Do not write your own helper for it.

```bash
python3 "$RS" status "$WS/state.json"                    # the next stage and its open items
python3 "$RS" tick   "$WS/state.json" <stage> <index> ...    # mark items done (0-based)
python3 "$RS" set    "$WS/state.json" head_sha_reviewed=<sha> base_branch=<base>
python3 "$RS" add    "$WS/state.json" claims '{"claim": "...", "status": "VERIFIED", "evidence": "path:line"}'
python3 "$RS" add    "$WS/state.json" findings '{"severity": "Must", "title": "...", "evidence": "..."}'
python3 "$RS" done   "$WS/state.json" <stage> <VERDICT>  # refused while a mandatory item is open
```

Repeat until every stage is `completed` or `skipped`. Run `status` before each stage; it re-reads
the file and lists what is open, which keeps the checklist in front of you after a long stage. Tick
each item as you finish it, then close the stage with `done`. Stage verdicts:

| Stage | Done | Stopped |
|---|---|---|
| 1 Intake | `INTAKE_DONE` | `INTAKE_STOPPED` (no access, or the user stops on a merged PR) |
| 2 Checkout | `CHECKOUT_DONE` | `CHECKOUT_FAILED` |
| 3 Understand | `UNDERSTOOD` | |
| 4 Verify Claims | `CLAIMS_CHECKED` | |
| 5 Consequences | `CONSEQUENCES_CHECKED` | |
| 6 Repo Rules and CI | `RULES_CHECKED` | |
| 7 Draft | `DRAFTED` | |
| 8 Post | `REVIEW_POSTED` | `DRAFT_ONLY` (no-post mode, or the user declines) |
| 9 Close Out | `REVIEW_COMPLETE` | |

## The stages

**1. Intake.** Fetch the PR's metadata, record the head SHA you are about to review, and read the
description in full: what it claims, what it says it ran and what it says it did not. Read the
existing reviews and threads too. A point someone already raised needs a "+1" at most, and a reply
to an earlier review may answer a finding before you write it. A merged or closed PR changes the job
from gatekeeping to follow-up, so tell the user before going further.

**2. Checkout.** Work in `$WS/repo`, never in a checkout or worktree the user is using: they may
have uncommitted work there, and a review must not move their branch. Review the three-dot diff
(`origin/<base>...pr-<n>`), never two-dot. A branch behind its base shows the base's new commits as
phantom deletions under two-dot (`stale-base-review`). Predict conflicts with
`git merge-tree --write-tree`, as `/pipeline-ship` Step 2.6 describes. Note the result (behind by
how many commits, clean or conflicting): the review states it, because the author and the person
who merges both need it.

**3. Understand.** Read the whole diff and the changed files in context. Write the plain summary
before judging anything, because a review that cannot say what the PR does in two sentences is not
ready to find faults. Then list the claims. Most wrong merges come from one false premise in the
description ("the job already sets this", "nothing else loads these settings", "the default is
unused"), not from a typo in the code.

**4. Verify Claims.** Check each claim where it lives: the file and line at the PR head, the
upstream source at the exact version the PR pins, the other repo's default branch, or a read-only
API call. Write the evidence down as you go (`unverified-claim`).

Read upstream code narrowly. When a claim rests on a few files of another project, fetch those files
at the pinned version (`gh api repos/<o>/<r>/contents/<path>?ref=<tag>`, or a shallow, sparse clone
of the tag) instead of cloning the whole history. A review spends its time on judgement, not on
downloads.

Before citing anything, make sure it describes the same thing as the claim. A config file for the
SaaS tenant does not describe the self-hosted one. A group list in a doc about one app does not
describe a sibling app. A file at `main` does not describe the version the PR pins
(`adjacent-evidence`). When a claim cannot be checked, because access is missing or a command is
blocked, say so in the review instead of filling the gap from memory.

**5. Consequences.** Find who consumes what changed: every process that loads the same settings
(a new required setting breaks any job that loads the full settings without it), other services and
repos, generated clients, and the order things deploy in. Compare the PR with the accepted decision
records and docs on the base branch, and with itself: its code, tests, docs and description should
tell one story, and a PR that contradicts an accepted decision needs either a code change or a
decision change. Test-merge the other open PRs that touch the same files, so the author learns the
merge order now and not at the merge. Apply the review categories of `pipeline-shared` (Code
Review): correctness, security, testing, quality, docs.

**6. Repo Rules and CI.** Read CI on the reviewed head and the base branch's rules. Two of them
change how you post:

- **Required review thread resolution.** Every inline comment opens a thread that blocks the merge
  until someone resolves it. Put non-blocking comments in the review body
  (`unresolved-thread-block`).
- **Code-owner review and last-push approval.** Tell the user whether their approval counts, and
  whether the author needs someone else as well.

**7. Draft.** Choose the verdict by the worst finding:

- **REQUEST_CHANGES** for a must-fix: wrong behaviour, a security problem, a deploy break, or a
  contradiction with an accepted decision.
- **APPROVE** when only suggestions and nits remain.
- **COMMENT** when the review cannot conclude, for example because a decisive claim is unverifiable.

Rank the findings Must, Should and Nit. Each one says what is wrong, the evidence, the impact and a
concrete fix. Also list what you checked and what held. An author trusts a review that shows its
work, and the next reviewer need not redo it. That list always includes the merge status from
stages 2 and 5: whether the branch is current with its base, whether it merges cleanly, and which
open PRs it conflicts with. A finding that lives only in the state file does not reach the author. Write `draft.md` in the posted voice, addressed to the
author. Then explain it to the user in plain language and ask whether to post it, and as which kind.

**8. Post.** Only on the user's explicit OK for this review. An OK given for another PR earlier in
the conversation does not carry over. Then:

1. Re-fetch the PR. If the head moved, review the new commits and update the draft. If it was merged
   or closed meanwhile, ask again (`stale-pr-state`).
2. Post against the SHA you reviewed:

   ```bash
   gh api --method POST repos/<owner>/<repo>/pulls/<n>/reviews \
     -f commit_id=<head_sha_reviewed> -f event=<APPROVE|REQUEST_CHANGES|COMMENT> \
     -F body=@"$WS/draft.md"
   ```

   With agreed inline comments, send JSON through `--input`, with `comments: [{path, line, side:
   "RIGHT", body}]`. Each line must be in the diff.
3. Verify: read the review back (state and URL), and each inline comment's anchor
   (`gh api .../pulls/<n>/comments`). Record `posted_review_url`.

**9. Close Out.** Tell the user the outcome in a few lines: the verdict, the link, whether their
review unblocks the merge, and what still blocks it. Offer the follow-ups the review promised, such
as updating a PR of theirs after this one merges.

## Rules that hold in every stage

- **Re-read the state before you report it.** Before telling the user that a PR is merged, open,
  approved or blocked, fetch it again. A read from ten minutes ago is history.
- **When you are shown wrong, say so and fix it everywhere.** If the author or the user corrects a
  finding, check the correction at its source. If it holds, say plainly that the finding was wrong,
  and correct the posted review and any other artifact that repeated it.
- **Reading is free. Writing to GitHub is not.** Fetching, cloning and reading other repos needs no
  permission. Posting, resolving threads, approving or commenting each need the user's OK for that
  action.
- **Keep the review's files in its workspace.** Clones, notes, drafts and helper scripts all go in
  `$WS`. A shared scratch folder lets a second review overwrite them.
- **Keep secrets out of the review.** Never paste tokens, keys or credential values into a review,
  even when the PR handles them. Name the secret, never its value.

## Resume

`--resume` reads `$WS/state.json` and continues at `current_stage`. When the PR's head moved since
`head_sha_reviewed`, say so first: the review covers the old head, and stages 2 to 7 must look at
the new commits before anything is posted.

## Cleanup

The workspace stays after the review, for `--resume` and as the record of what was checked. Remove
`$WS` when the PR is merged and nothing is left to follow up.

## Examples

```bash
/pipeline-review https://github.com/acme/api/pull/412
/pipeline-review acme/infra#88 --focus "the database migration"
/pipeline-review 57 --no-post          # in a checkout of the PR's repo; draft only
/pipeline-review acme/api#412 --resume
```

## What this is not

- Not `/pipeline-ship`. That skill takes your own changes to a merged PR, with its own review stage.
- Not a merge tool. It never merges, enqueues or resolves threads unless the user asks for that
  action separately.
- Not a linter. CI already ran the linters. Spend the review on what CI cannot know.
