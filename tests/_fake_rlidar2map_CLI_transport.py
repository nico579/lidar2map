#!/usr/bin/env python3
"""Fake ssh/scp/rsync executable used by _test_rlidar2map_CLI.py."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shlex
import shutil
import struct
import sys
from pathlib import Path


TOOL = sys.argv[1]
STATE_PATH = Path(sys.argv[2])
CALL_LOG = Path(sys.argv[3])
REMOTE_ROOT = Path(sys.argv[4])
ARGS = sys.argv[5:]


def append_call(data):
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CALL_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(data, ensure_ascii=False) + "\n")


def load_state():
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(data):
    STATE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def emit_state(status):
    if status == "absent":
        print("protocol=1")
        print("exists=0")
        print("tmux=0")
        return
    terminal = status in ("succeeded", "failed")
    exit_code = "0" if status == "succeeded" else ("7" if terminal else "")
    print("protocol=1")
    print("exists=1")
    print("session=lidar")
    print("run_id=fake-run-1")
    print("status={}".format(status))
    print("tmux={}".format(0 if terminal else 1))
    print("mode=source")
    print("exit_code={}".format(exit_code))
    print("reason={}".format("fake failure" if status == "failed" else ""))
    print("created_at=2026-07-29T12:00:00Z")
    print("started_at=2026-07-29T12:00:01Z")
    print(
        "finished_at={}".format(
            "2026-07-29T12:01:00Z" if terminal else ""
        )
    )
    print("run_dir=/home/test/.lidar2map-runs/lidar")
    print("results_dir=/home/test/.lidar2map-runs/lidar/results")
    print("log_path=/home/test/.lidar2map-runs/lidar/run.log")
    print("rsync=0")


def remote_inventory():
    files = []
    for path in sorted((REMOTE_ROOT / "results").rglob("*")):
        relative_path = path.relative_to(REMOTE_ROOT / "results")
        if (
            not path.is_file()
            or any(
                part.endswith(".part")
                for part in relative_path.parts[:-1]
            )
            or path.name.endswith(
                (".part", ".part-wal", ".part-shm", ".part-journal")
            )
        ):
            continue
        info = path.stat()
        relative = relative_path.as_posix()
        files.append(
            {
                "path": base64.b64encode(
                    relative.encode("utf-8")
                ).decode("ascii"),
                "fingerprint": [
                    info.st_dev,
                    info.st_ino,
                    info.st_size,
                    info.st_mtime_ns,
                ],
            }
        )
    sys.stdout.buffer.write(
        json.dumps(
            {
                "protocol": 1,
                "run_id": "fake-run-1",
                "now_ns": 1,
                "files": files,
            },
            separators=(",", ":"),
        ).encode("ascii")
    )


def write_frame(payload):
    encoded = json.dumps(payload, separators=(",", ":")).encode("ascii")
    sys.stdout.buffer.write(struct.pack(">Q", len(encoded)))
    sys.stdout.buffer.write(encoded)


def remote_copy(payload):
    request = json.loads(payload)
    files = request["files"]
    sys.stdout.buffer.write(b"L2M-FILE-STREAM-1\n")
    for item in files:
        relative = base64.b64decode(item["path"]).decode("utf-8")
        content = (REMOTE_ROOT / "results" / relative).read_bytes()
        write_frame(
            {
                "type": "file",
                "path": item["path"],
                "size": len(content),
            }
        )
        sys.stdout.buffer.write(content)
        write_frame(
            {
                "type": "trailer",
                "path": item["path"],
                "stable": True,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    write_frame({"type": "end", "count": len(files)})


def fake_ssh():
    payload = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    remote_tokens = shlex.split(ARGS[-1], posix=True)
    helper_action = (
        remote_tokens[-3]
        if len(remote_tokens) >= 3
        and remote_tokens[0:2] == ["python3", "-c"]
        else ""
    )
    if helper_action in ("inventory", "copy"):
        kind = helper_action
    elif remote_tokens[:1] == ["tail"]:
        # print_remote_log_tail : pas de payload (aucun input piped), donc
        # sans ce cas explicite elle tombait dans le repli "launch" ci-dessous
        # (n'importe quel payload sans STATUS=) à chaque cycle de sondage.
        kind = "log_tail"
    else:
        kind = (
            "query"
            if "STATUS=" in payload and "REMOTE_LAUNCH" not in payload
            else "launch"
        )
    # REMOTE_LAUNCH is not a literal in the script; the package setup marker
    # reliably distinguishes it from the small query script.
    if "packages=(tmux)" in payload:
        kind = "launch"
    append_call(
        {
            "tool": "ssh",
            "kind": kind,
            "argv": ARGS,
            "remote_tokens": remote_tokens,
        }
    )
    if kind == "inventory":
        remote_inventory()
        return 0
    if kind == "copy":
        remote_copy(payload)
        return 0
    if kind == "log_tail":
        return 0   # pas de nouvelles données -> no-op, cf. print_remote_log_tail
    if kind == "launch":
        return 0
    data = load_state()
    index = data.get("query_index", 0)
    states = data["states"]
    status = states[min(index, len(states) - 1)]
    data["query_index"] = index + 1
    save_state(data)
    emit_state(status)
    return 0


def copy_tree(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def fake_scp():
    append_call({"tool": "scp", "argv": ARGS, "cwd": os.getcwd()})
    source = ARGS[-2]
    destination = ARGS[-1]
    cwd = Path.cwd()
    if "/results" in source:
        copy_tree(REMOTE_ROOT / "results", cwd)
    elif source.endswith("/run.log") or source.endswith(":run.log"):
        (cwd / destination).write_text("fake remote log\n", encoding="utf-8")
    return 0


def fake_rsync():
    append_call({"tool": "rsync", "argv": ARGS, "cwd": os.getcwd()})
    copy_tree(REMOTE_ROOT / "results", Path.cwd())
    return 0


if TOOL == "ssh":
    raise SystemExit(fake_ssh())
if TOOL == "scp":
    raise SystemExit(fake_scp())
if TOOL == "rsync":
    raise SystemExit(fake_rsync())
raise SystemExit("unknown fake tool: {}".format(TOOL))
