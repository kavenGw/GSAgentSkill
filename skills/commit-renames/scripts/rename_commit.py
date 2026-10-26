"""Prepare and commit staged path renames without consuming content edits."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(repo, *args, env=None, data=None):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], input=data, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace") +
                           result.stdout.decode("utf-8", errors="replace"))
    return result.stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text(data):
    return data.decode("utf-8", errors="surrogateescape")


def paths(data):
    return [text(item) for item in data.split(b"\0") if item]


def snapshot(repo, baseline):
    names = set(paths(git(repo, "diff", "--no-ext-diff", "--name-only",
                         "--no-renames", "-z", baseline)))
    names.update(paths(git(repo, "ls-files", "--others", "--exclude-standard", "-z")))
    files = {}
    for name in sorted(names):
        file = repo / name
        if file.is_symlink():
            files[name] = ["symlink", os.readlink(file)]
        elif file.is_file():
            files[name] = ["file", digest(file.read_bytes())]
        elif not file.exists():
            files[name] = ["absent"]
        else:
            raise ValueError("Unsupported changed directory/submodule: " + name)
    return {
        "index": digest(git(repo, "ls-files", "--stage", "-z")),
        "unstaged": digest(git(repo, "diff", "--no-ext-diff", "--no-textconv", "--binary")),
        "files": files,
    }


def check_context(repo):
    require(not os.environ.get("GIT_INDEX_FILE"), "Unset inherited GIT_INDEX_FILE first.")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "sequencer"):
        path = Path(text(git(repo, "rev-parse", "--path-format=absolute", "--git-path", marker)).strip())
        require(not path.exists(), "Finish the in-progress Git operation: " + marker)
    require(not git(repo, "ls-files", "--unmerged", "-z"), "Resolve index conflicts first.")
    return {
        "head": text(git(repo, "rev-parse", "HEAD")).strip(),
        "branch": text(git(repo, "rev-parse", "--symbolic-full-name", "HEAD")).strip(),
    }


def tree_entries(repo, revision):
    result = {}
    for row in git(repo, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if row:
            attrs, path = row.split(b"\t", 1)
            mode, kind, oid = attrs.split()
            result[text(path)] = (text(mode), text(oid))
    return result


def validate_path(value):
    require(isinstance(value, str) and value, "Paths must be nonempty strings.")
    path = PurePosixPath(value)
    require(not path.is_absolute() and str(path) == value and
            not any(part in ("..", ".git") for part in path.parts) and
            not any(char in value for char in ("\\", ":", "\0", "\n", "\r", "\t")),
            "Expected a repository-relative POSIX path: " + value)


def index_entries(repo):
    result = {}
    for row in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if row:
            attrs, path = row.split(b"\t", 1)
            mode, oid, stage = attrs.split()
            require(stage == b"0", "Unmerged index entry.")
            result[text(path)] = (text(mode), text(oid))
    return result


def prepare(args):
    repo = Path(args.repo).resolve()
    root = Path(text(git(repo, "rev-parse", "--show-toplevel")).strip()).resolve()
    require(repo == root, "--repo must name the repository root.")
    context = check_context(repo)
    before = snapshot(repo, context["head"])
    head = tree_entries(repo, context["head"])
    index = index_entries(repo)
    raw = json.loads(Path(args.pairs).read_text(encoding="utf-8-sig"))
    require(isinstance(raw, list) and raw, "Expected a nonempty array of [old, new] pairs.")
    pairs = []
    for pair in raw:
        require(isinstance(pair, list) and len(pair) == 2, "Each mapping must be [old, new].")
        for name in pair:
            validate_path(name)
        pairs.append(tuple(pair))
    require(len(set(pairs)) == len(pairs), "Duplicate mapping.")
    for old, new in list(pairs):
        if not old.endswith(".meta") and old + ".meta" in head:
            sidecar = (old + ".meta", new + ".meta")
            if sidecar not in pairs:
                pairs.append(sidecar)
    require(len({p[0] for p in pairs}) == len(pairs) and
            len({p[1] for p in pairs}) == len(pairs), "Mapping must be one-to-one.")
    expected = dict(head)
    records = []
    for old, new in pairs:
        require(old in head and new not in head, "HEAD path missing or destination occupied: " + old + " -> " + new)
        require(old not in index and new in index, "Rename must already be staged: " + old + " -> " + new)
        require(not (repo / old).exists() and not (repo / old).is_symlink(), "Old working path still exists: " + old)
        require((repo / new).is_file() and not (repo / new).is_symlink(), "Expected a regular destination file: " + new)
        mode, oid = head[old]
        require(mode in ("100644", "100755") and index[new][0] in ("100644", "100755"), "Only regular files are supported.")
        if old.endswith(".meta"):
            original = git(repo, "cat-file", "blob", oid)
            staged = git(repo, "cat-file", "blob", index[new][1])
            working = (repo / new).read_bytes()
            guid = lambda content: re.findall(rb"(?m)^guid:\s*([0-9a-fA-F]+)\s*$", content)
            if guid(original):
                require(len(guid(original)) == 1 and guid(original) == guid(staged) == guid(working), "Unity GUID mismatch: " + new)
        records.append(("0 " + "0" * len(oid) + "\t" + old + "\0").encode("utf-8"))
        records.append((mode + " " + oid + "\t" + new + "\0").encode("utf-8"))
        del expected[old]
        expected[new] = (mode, oid)
    scratch = Path(tempfile.mkdtemp(prefix="commit-renames-"))
    env = dict(os.environ, GIT_INDEX_FILE=str(scratch / "index"))
    state_path = scratch / "state.json"
    try:
        git(repo, "read-tree", context["head"], env=env)
        git(repo, "update-index", "-z", "--index-info", env=env, data=b"".join(records))
        candidate = text(git(repo, "write-tree", env=env)).strip()
        require(tree_entries(repo, candidate) == expected, "Candidate tree differs from the requested mapping.")
        stats = git(repo, "diff", "--cached", "--numstat", "--find-renames=100%", env=env).splitlines()
        require(all(row.startswith((b"0\t0\t", b"-\t-\t")) for row in stats), "Candidate contains content changes.")
        git(repo, "diff", "--cached", "--check", env=env)
        require(check_context(repo) == context and snapshot(repo, context["head"]) == before, "Repository changed during preparation.")
        state = {"repo": str(repo), "context": context, "snapshot": before, "tree": candidate, "pairs": pairs}
        state_path.write_text(json.dumps(state, ensure_ascii=True), encoding="utf-8")
        print(text(git(repo, "diff", "--cached", "--no-ext-diff", "--no-textconv", "--find-renames=100%", env=env)))
        print(json.dumps({"state": str(state_path), "renames": len(pairs), "content_changes": 0}))
    except Exception:
        cleanup(state_path)
        raise


def cleanup(state_path):
    scratch = state_path.parent
    require(scratch.name.startswith("commit-renames-") and
            scratch.parent.resolve() == Path(tempfile.gettempdir()).resolve(), "Unexpected temporary directory.")
    require({p.name for p in scratch.iterdir()} <= {"index", "state.json"}, "Unexpected files or index lock; inspect temporary directory.")
    (scratch / "index").unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)
    scratch.rmdir()


def commit(args):
    state_path = Path(args.state).resolve()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    repo = Path(state["repo"])
    require(check_context(repo) == state["context"], "HEAD/branch changed; prepare again.")
    require(snapshot(repo, state["context"]["head"]) == state["snapshot"], "Index/worktree changed; prepare again.")
    env = dict(os.environ, GIT_INDEX_FILE=str(state_path.parent / "index"))
    require(text(git(repo, "write-tree", env=env)).strip() == state["tree"], "Temporary index changed; prepare again.")
    message = Path(args.message_file).resolve()
    require(message.read_text(encoding="utf-8-sig").strip(), "Empty commit message.")
    print(text(git(repo, "commit", "-F", str(message), env=env)))
    require(text(git(repo, "rev-parse", "HEAD^")).strip() == state["context"]["head"], "Unexpected committed parent; inspect HEAD before any retry.")
    require(text(git(repo, "rev-parse", "HEAD^{tree}")).strip() == state["tree"], "Committed tree changed, possibly by a hook; inspect HEAD before any retry.")
    require(snapshot(repo, state["context"]["head"]) == state["snapshot"], "Index/worktree altered; inspect before retry.")
    print("Verified commit:", text(git(repo, "rev-parse", "HEAD")).strip())
    print("Original index entries and working changes preserved.")
    cleanup(state_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--repo", required=True)
    prepare_parser.add_argument("--pairs", required=True)
    commit_parser = commands.add_parser("commit")
    commit_parser.add_argument("--state", required=True)
    commit_parser.add_argument("--message-file", required=True)
    discard_parser = commands.add_parser("discard")
    discard_parser.add_argument("--state", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args)
        elif args.command == "commit":
            commit(args)
        else:
            cleanup(Path(args.state).resolve())
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, str(error) + "\nStopped. Inspect HEAD and repository state before retrying; no rollback was attempted.\n")


if __name__ == "__main__":
    main()
