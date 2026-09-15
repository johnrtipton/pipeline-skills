# `fix-reproduces-own-bug`

**Rule** (the line the rule sheet carries): Before the first edit, enumerate every caller of
the shared state the fix touches and the invariant each one needs — a fix that reproduces the
class it removes is the family's dominant recurrence.
→ this page

**Status**: `skill` · **gate**: none (proposed: gate-off evidence as a first-class artifact —
upstream #82) · **candidate for mechanical gate**: yes
**Origin**: djust #2147 (v1.1.0-14) — *"the 🔴s were this fix reproducing the bug it exists to
remove"*.

## Instances

| PR | what drifted / what was missed | cure | rule in force? |
|---|---|---|---|
| #2147 | the fix reproduced the bug it exists to remove | reworked before merge | no (origin) |
| #2146 | the fix "repeated the 🔴's own class" | reworked | no |
| #2838 r1 | overloaded a documented attribute (`dj-key`) as a keyboard filter → silenced handlers on keyed list rows; a regression against the base | reverted | no |
| #2838 r2 | first-match-wins dispatch dropped an ancestor handler the base *did* fire, and let a bare binding permanently shadow a dotted sibling | dispatch every matching binding | no |
| #2838 r3 | dispatching every match rebuilt the per-element rate-limit wrapper on every keystroke — defeating `dj-debounce` (3 keystrokes → 3 events) and leaking one `blur` listener per keystroke | cache keyed by (element, matched attribute) | no |
| #2846 | fixed the three render paths the issue named and left a **fourth** on the old resolution (a defect the issue did not enumerate) | follow-up filed (#2847) | no |

## Detection

- **The per-revision gate-off matrix.** One red/green column per revision, not a single
  before/after. On #2838 it produced `main 10 / r1 12 / r2 5 / r3 2 / head 0` — and it is what
  exposed a case that pressed a **non-matching** key, so it could never fail and was green on
  every revision. A single "revert the fix, see it go red" would not have found that.
- **A caller/invariant list** written before the first edit for any change to a cache,
  registry, or dispatch shared by more than one caller. The #2838 cache had four callers
  (click, change, keydown, keyup) and two invariants (a morph must not strand a binding; the
  wrapper owns rate-limit state, so it must not be rebuilt).

## Rejected shapes

- **"Fix the symptom in front of you and re-review."** That is exactly rounds 1–3 of #2838,
  each of which produced the next round's defect.
- **"Make the odd path match the other three."** #2846's brief was to make one path agree with
  its siblings; asking *which resolution was correct* first is what revealed that the siblings
  disagreed about precedence. Parity is not a substitute for a correct target.
