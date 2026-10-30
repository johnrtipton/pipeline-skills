# PURPOSE — pipeline-review

Why each mandatory gate or rule in `SKILL.md` exists: the pattern it serves (a row in
[`docs/patterns/README.md`](../../docs/patterns/README.md)) and where it came from. A row whose
pattern is `—` is a gate with no living pattern behind it, a candidate for the Stage 3.7 gate once a
page exists (ADR-0004).

| gate / rule | pattern | origin | in SKILL.md |
|---|---|---|---|
| Stage 2: review the three-dot diff; predict conflicts with `merge-tree --write-tree` | `stale-base-review` | inherited from `pipeline-ship` Step 2.6 | “three-dot”, “--write-tree” |
| Stage 2: review in its own workspace, never the user's checkout or worktree | `worktree-dirty-tree` | a checkout with uncommitted work sat on the default branch | “never in a checkout or worktree the user is using” |
| Stage 4: check each claim at its source and record the evidence | `unverified-claim` | a description said a job already set a value that it did not | “Verify Claims” |
| Stage 4: evidence must describe the same app, environment, instance and version as the claim | `adjacent-evidence` | a cross-repo review cited a retired tenant's config, and a sibling app's group list, as evidence; both findings were wrong | “same thing as the claim” |
| Stage 5: compare the PR with accepted decision records and with itself | — | a PR allowed what its own accepted decision record refused | “accepted decision records” |
| Stage 6: under required thread resolution, put non-blocking comments in the review body | `unresolved-thread-block` | two inline nits blocked a merge-ready PR | “Required review thread resolution” |
| Stage 8: post only on an explicit OK for this review | — | — | “explicit OK for this review” |
| `review_state.py` is the only writer of `state.json`; `done` refuses a stage with an open mandatory item | `state-file-bypass` | every test review wrote its own state helper, and two parallel reviews wrote into each other's state file | “the only thing that edits `state.json`” |
| Every file of a review stays in its workspace | `parallel-agent-contention` | the same collision: a helper in a shared scratch folder was overwritten by another review | “Keep the review's files in its workspace” |
| `review_state.py round`: a re-review archives the finished round to `rounds/<n>.json` and starts the next in the same state file; one state file per workspace | `state-file-bypass` | the first follow-up review, after an author answered a REQUEST_CHANGES, started a second state file at a path picked on the spot and copied the previous head, review URL and findings over by hand | “start a re-review round”, “One state file per workspace” |
| Stage 4 in a round: check each earlier finding against the new commits; `done` refuses Verify Claims while one is `PENDING` | `unverified-claim` | the same follow-up review: every earlier finding had to be checked again against the new commits | “is a claim like any other” |
| Stage 5: re-fetch the base before checking consequences | `stale-base-review` | a neighbour PR can merge after the author's last push and move the lines the PR cites; between rounds that window is days | “Re-fetch the base first” |
| Stage 7: the review states the merge status | — | a review found the clean merge but kept it in its state file, out of the author's sight | “the merge status” |
| Stage 8 and the rule “re-read the state before you report it” | `stale-pr-state` | a review told the user a PR was open after it had merged | “Re-read the state before you report it” |
