#!/usr/bin/env python3
"""Read and update a pipeline-review state file.

Every command names the state file, so two reviews never share one by accident.

    review_state.py init   <state.json> --pr-url <url> --repo <owner/repo> --number <n>
                           [--no-post] [--template <review-state.json>]
    review_state.py status <state.json>                  # the next stage and its open items
    review_state.py set    <state.json> key=value ...    # top-level fields; values may be JSON
    review_state.py tick   <state.json> <stage> <index> ...   # mark checklist items done (0-based)
    review_state.py done   <state.json> <stage> <VERDICT>     # close a stage; refused while a
                                                              # mandatory item is open
    review_state.py skip   <state.json> <stage> <reason>      # mark a stage skipped
    review_state.py add    <state.json> claims|findings '<json object>'   # prints its index
    review_state.py list   <state.json> claims|findings               # entries with their indexes
    review_state.py update <state.json> claims|findings <index> '<json object>'
                                                              # merge fields into one entry
    review_state.py round  <state.json> [--no-post] [--template <review-state.json>]
                                                              # re-review: archive the finished
                                                              # round, start the next one

Without --template, init and round use review-state.json from the skill folder's templates/ (a
copy install puts it there) or else the clone's templates/ (a symlink install, or a clone).

init ticks the checklist items marked re_review: a first review has no earlier round. round
refuses while a stage of the current round is open. It moves the finished state to
rounds/<n>.json beside it and starts round n+1 from the template, with its re_review items open
and previous_head, previous_review_url and previous_verdict from the finished round. The
finished round's findings that are not RESOLVED or WITHDRAWN come along with recheck PENDING,
and a stage marked recheck_findings (Verify Claims) cannot close while one is still PENDING.
"""

import datetime
import json
import os
import sys
import tempfile


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: str) -> dict:
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        sys.exit(f"no state file at {path}; init starts a review")


def _save(path: str, state: dict) -> None:
    # Write to a temporary file in the same folder, then rename, so a crash never leaves half a file.
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".state-", suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def _value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _next_stage(state: dict) -> str | None:
    for key, stage in state["stages"].items():
        if stage["status"] not in ("completed", "skipped"):
            return key
    return None


def _stage(state: dict, key: str) -> dict:
    if key not in state["stages"]:
        sys.exit(f"no stage {key!r}; stages are {', '.join(state['stages'])}")
    return state["stages"][key]


def _default_template() -> str:
    skill = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    candidates = [
        os.path.join(skill, "templates", "review-state.json"),
        os.path.join(os.path.dirname(os.path.dirname(skill)), "templates", "review-state.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    sys.exit(f"no review-state.json in {' or '.join(candidates)}; pass --template <path>")


def _kind(kind: str, command: str) -> str:
    if kind not in ("claims", "findings"):
        sys.exit(f"{command} takes claims or findings, not {kind!r}")
    return kind


def _object(text: str) -> dict:
    item = _value(text)
    if not isinstance(item, dict):
        sys.exit(f"the item must be a JSON object, not {text!r}")
    return item


def _usage(args: list[str], count: int, usage: str) -> None:
    if len(args) != count:
        sys.exit(f"usage: review_state.py {usage}")


def _options(rest: list[str], allowed: tuple[str, ...]) -> dict:
    opts = {}
    while rest:
        flag = rest.pop(0)
        if flag == "--no-post":
            opts["no_post"] = True
        elif flag in allowed and rest:
            opts[flag[2:].replace("-", "_")] = rest.pop(0)
        else:
            sys.exit(f"unknown or incomplete option {flag!r}")
    return opts


def _pending_rechecks(state: dict) -> list[int]:
    return [i for i, item in enumerate(state.get("findings", []))
            if isinstance(item, dict) and item.get("recheck") == "PENDING"]


def cmd_init(args: list[str]) -> None:
    path = args[0]
    opts = _options(args[1:], ("--template", "--pr-url", "--repo", "--number"))
    missing = [k for k in ("pr_url", "repo", "number") if k not in opts]
    if missing:
        sys.exit(f"init needs --{', --'.join(m.replace('_', '-') for m in missing)}")
    if os.path.exists(path):
        sys.exit(f"{path} exists; use status to resume it, or remove it to start again")
    state = _load(opts.get("template") or _default_template())
    state.update(
        pr_url=opts["pr_url"],
        repo=opts["repo"],
        pr_number=int(opts["number"]),
        workspace=os.path.dirname(os.path.abspath(path)),
        post_mode="none" if opts.get("no_post") else "ask",
        task_description=f"Review {opts['repo']}#{opts['number']}",
        started_at=_now(),
    )
    # A first review has no earlier round, so the re-review items have nothing to do.
    for stage in state["stages"].values():
        for item in stage["checklist"]:
            if item.get("re_review"):
                item["done"] = True
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    _save(path, state)
    print(f"created {path}")


def cmd_status(args: list[str]) -> None:
    state = _load(args[0])
    key = _next_stage(state)
    print(f"PR {state.get('repo')}#{state.get('pr_number')}  round {state.get('round', 1)}"
          f"  head reviewed: {state.get('head_sha_reviewed') or '-'}")
    if state.get("previous_head"):
        print(f"previous round: head {state['previous_head']}, {state.get('previous_verdict') or 'no verdict'},"
              f" review {state.get('previous_review_url') or 'not posted'}")
    pending = _pending_rechecks(state)
    if pending:
        print(f"findings to recheck against the new commits: {pending}")
    if key is None:
        print("every stage is done; if the PR's head moved since, round starts a re-review")
        return
    stage = state["stages"][key]
    print(f"next: stage {key}, {stage['name']} ({stage['status']})")
    for i, item in enumerate(stage["checklist"]):
        if not item.get("done"):
            mark = "mandatory" if item.get("mandatory") else "optional"
            print(f"  [{i}] ({mark}) {item['action']}")


def cmd_set(args: list[str]) -> None:
    path, pairs = args[0], args[1:]
    state = _load(path)
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or key == "stages":
            sys.exit(f"bad assignment {pair!r} (use key=value; stages change only through tick/done/skip)")
        state[key] = _value(value)
    _save(path, state)


def cmd_tick(args: list[str]) -> None:
    path, key, indexes = args[0], args[1], args[2:]
    state = _load(path)
    stage = _stage(state, key)
    for text in indexes:
        stage["checklist"][int(text)]["done"] = True
    if stage["status"] == "pending":
        stage["status"] = "in_progress"
    _save(path, state)


def cmd_done(args: list[str]) -> None:
    path, key, verdict = args[0], args[1], args[2]
    state = _load(path)
    stage = _stage(state, key)
    open_items = [i for i, item in enumerate(stage["checklist"]) if item.get("mandatory") and not item.get("done")]
    if open_items:
        sys.exit(f"stage {key} ({stage['name']}) still has mandatory items open: {open_items}")
    pending = _pending_rechecks(state) if stage.get("recheck_findings") else []
    if pending:
        sys.exit(f"stage {key} ({stage['name']}) cannot close while findings {pending} from the last round"
                 f" are still recheck PENDING; record RESOLVED, OPEN or WITHDRAWN with update")
    stage.update(status="completed", verdict=verdict)
    nxt = _next_stage(state)
    state["current_stage"] = nxt
    if nxt is None:
        state["completed_at"] = _now()
    _save(path, state)
    print(f"stage {key} {verdict}; next: {nxt or 'none'}")


def cmd_skip(args: list[str]) -> None:
    path, key, reason = args[0], args[1], " ".join(args[2:])
    state = _load(path)
    stage = _stage(state, key)
    stage.update(status="skipped", verdict=f"SKIPPED: {reason}")
    state["current_stage"] = _next_stage(state)
    _save(path, state)


def cmd_add(args: list[str]) -> None:
    _usage(args, 3, "add <state.json> claims|findings '<json object>'")
    path, kind, text = args[0], _kind(args[1], "add"), args[2]
    item = _object(text)
    state = _load(path)
    entries = state.setdefault(kind, [])
    entries.append(item)
    _save(path, state)
    print(f"added {kind}[{len(entries) - 1}]")


def cmd_list(args: list[str]) -> None:
    _usage(args, 2, "list <state.json> claims|findings")
    path, kind = args[0], _kind(args[1], "list")
    entries = _load(path).get(kind, [])
    print(f"{kind}: {len(entries)}")
    for i, item in enumerate(entries):
        print(f"  [{i}] {json.dumps(item, ensure_ascii=False)}")


def cmd_update(args: list[str]) -> None:
    _usage(args, 4, "update <state.json> claims|findings <index> '<json object>'")
    path, kind, text = args[0], _kind(args[1], "update"), args[3]
    fields = _object(text)
    state = _load(path)
    entries = state.get(kind, [])
    try:
        index = int(args[2])
    except ValueError:
        sys.exit(f"the index must be a whole number, not {args[2]!r}")
    if not 0 <= index < len(entries):
        span = f"0 to {len(entries) - 1}" if entries else "none: the list is empty"
        sys.exit(f"no {kind}[{index}]; indexes are {span} (see: list {path} {kind})")
    if not isinstance(entries[index], dict):
        sys.exit(f"{kind}[{index}] is not a JSON object, so it cannot be merged into")
    entries[index].update(fields)
    _save(path, state)
    print(f"updated {kind}[{index}]: {json.dumps(entries[index], ensure_ascii=False)}")


def cmd_round(args: list[str]) -> None:
    path = args[0]
    opts = _options(args[1:], ("--template",))
    state = _load(path)
    still_open = [f"{k} ({st['name']}, {st['status']})" for k, st in state["stages"].items()
                  if st["status"] not in ("completed", "skipped")]
    if still_open:
        sys.exit(f"stages still open in this round: {', '.join(still_open)}; finish or skip them"
                 f" (status {path}) before starting a round")
    if not state.get("head_sha_reviewed"):
        sys.exit("this round recorded no head_sha_reviewed, so the next one has nothing to diff against;"
                 " set it to the head this round reviewed first")
    number = state.get("round", 1)
    folder = os.path.dirname(os.path.abspath(path))
    archive = os.path.join(folder, "rounds", f"{number}.json")
    # A file there that is not this round means something else wrote it: never overwrite a past round.
    # The same round is a rerun after a crash between the two writes below, so carry on.
    if os.path.exists(archive) and _load(archive) != state:
        sys.exit(f"{archive} exists and is not this round; move it aside before starting a round")

    carried = []
    for item in state.get("findings", []):
        if not isinstance(item, dict) or item.get("recheck") in ("RESOLVED", "WITHDRAWN"):
            continue
        item = {k: v for k, v in item.items() if k != "recheck_evidence"}
        item.setdefault("round", number)
        item["recheck"] = "PENDING"
        carried.append(item)

    fresh = _load(opts.get("template") or _default_template())
    fresh.update({k: state.get(k) for k in ("pr_url", "repo", "pr_number", "base_branch")})
    fresh.update(
        workspace=folder,
        post_mode="none" if opts.get("no_post") else "ask",
        task_description=f"Re-review {state.get('repo')}#{state.get('pr_number')}, round {number + 1}",
        started_at=_now(),
        round=number + 1,
        previous_head=state["head_sha_reviewed"],
        previous_review_url=state.get("posted_review_url"),
        previous_verdict=state.get("review_verdict"),
        rounds=state.get("rounds", []) + [{
            "round": number,
            "state": os.path.relpath(archive, folder),
            "head": state["head_sha_reviewed"],
            "verdict": state.get("review_verdict"),
            "review_url": state.get("posted_review_url"),
        }],
        findings=carried,
    )
    os.makedirs(os.path.dirname(archive), exist_ok=True)
    _save(archive, state)
    _save(path, fresh)
    print(f"round {number} archived to {archive}; round {number + 1} started in {path}"
          f" with {len(carried)} findings to recheck: {list(range(len(carried)))}")


COMMANDS = {
    "init": cmd_init, "status": cmd_status, "set": cmd_set, "tick": cmd_tick,
    "done": cmd_done, "skip": cmd_skip, "add": cmd_add, "list": cmd_list,
    "update": cmd_update, "round": cmd_round,
}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
