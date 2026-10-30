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
    review_state.py add    <state.json> claims|findings '<json object>'

Without --template, init uses review-state.json from the skill folder's templates/ (a copy
install puts it there) or else the clone's templates/ (a symlink install, or a clone).
"""

import datetime
import json
import os
import sys
import tempfile


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


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


def cmd_init(args: list[str]) -> None:
    path, opts = args[0], {}
    rest = args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "--no-post":
            opts["no_post"] = True
        elif flag in ("--template", "--pr-url", "--repo", "--number") and rest:
            opts[flag[2:].replace("-", "_")] = rest.pop(0)
        else:
            sys.exit(f"unknown or incomplete option {flag!r}")
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
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    _save(path, state)
    print(f"created {path}")


def cmd_status(args: list[str]) -> None:
    state = _load(args[0])
    key = _next_stage(state)
    print(f"PR {state.get('repo')}#{state.get('pr_number')}  head reviewed: {state.get('head_sha_reviewed') or '-'}")
    if key is None:
        print("every stage is done")
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
    path, kind, text = args[0], args[1], args[2]
    if kind not in ("claims", "findings"):
        sys.exit("add takes claims or findings")
    item = _value(text)
    if not isinstance(item, dict):
        sys.exit("the item must be a JSON object")
    state = _load(path)
    state.setdefault(kind, []).append(item)
    _save(path, state)


COMMANDS = {
    "init": cmd_init, "status": cmd_status, "set": cmd_set, "tick": cmd_tick,
    "done": cmd_done, "skip": cmd_skip, "add": cmd_add,
}

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](sys.argv[2:])
