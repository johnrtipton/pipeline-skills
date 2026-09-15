# `unverified-claim`

**Rule** (the line the rule sheet carries): Before writing a claim about what the code or
docs contain, open the file and cite the path (and line); a claim that cannot be checked
must not be written.
→ this page

**Status**: `skill` · **gate**: none (proposed: check paths/symbols/counts in `changelog.d/*.md`
and PR bodies — upstream #83) · **candidate for mechanical gate**: yes
**Origin**: djust #2838 (v1.2.0-6) — the claim that *caused* a regression.

## Instances

| PR | what drifted / what was missed | cure | rule in force? |
|---|---|---|---|
| #2838 | changelog asserted `dj-key="Enter"` is "the documented way to restrict an undotted handler". It is the VNode **list-identity** attribute. The false claim was the *premise* for a code change, which silenced handlers on keyed list rows (`<li dj-key="42" dj-keydown="select">`) — a regression against the base | change reverted; `dj-key` deliberately not read as a key; rule written into the consumer's CLAUDE.md | no (origin — the rule did not exist) |
| #2546 | shipped "a false categorical claim of exactly the class this row exists to kill" | corrected in review | no |
| #2534 | PR body: a test class has "14 shapes"; the case list has 19 | corrected | no |
| #2554 | CHANGELOG cites "two new cases in `TestCustomFilters` of the #1121 file" — no such class exists | corrected | no |
| #2573 | CHANGELOG + `__init__.py` docstring assert an import-ordering fact; the assertion does not hold | corrected | no |
| #2607 | `docs/TEMPLATE_BACKEND.md:260` still reports `47.09% (493 of 1047)` after a behaviour change moved it | corrected | no |
| #2843 | PR body claimed a test "needs the compiled Rust extension, unavailable in this worktree env" — it runs (24 tests pass) and `import djust._rust` works | body corrected by the drain lead before merge | no |

## Detection

Reviewers read the artifact against the code; that is what caught all seven, and it is not a
mechanism. The checkable shapes are narrow and cheap:

- **a path** — `<path>.py`, `tests/...` — should resolve in the tree;
- **a symbol** — `ClassName`, `ClassName.method` — should exist (the consumer's #2652 walker
  already does this for `docs/`);
- **a count** — "N cases in `<file>`" — should match the file (the consumer has
  `check-changelog-test-counts` for exactly this; its own regex has a known prose
  false-positive, see the consumer's #2839).

## Rejected shapes

- **"Add a line to the PR template telling authors to verify claims."** Prose. Five of the
  seven above shipped past review *with* reviewers reading them; a template line does not add
  a reader.
- **"Rely on the reviewer catching it."** True for six of seven — but the seventh became a
  behaviour regression, which is a very expensive way to have a claim checked.
- **Marking the claim with an explicit `unverified:` marker instead of deleting it.** Leaves
  the false claim in the reader's path; the rule is delete-or-verify.
