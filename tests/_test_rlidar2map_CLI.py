#!/usr/bin/env python3
"""Self-contained tests for tools/rlidar2map_CLI.py (no VM or pytest required)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "rlidar2map_CLI.py"
FAKE_TRANSPORT = ROOT / "Tests" / "_fake_rlidar2map_CLI_transport.py"
SPEC = importlib.util.spec_from_file_location("rlidar2map_CLI", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
rlidar2map_cli = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rlidar2map_cli
SPEC.loader.exec_module(rlidar2map_cli)


def options(*extra: str) -> rlidar2map_cli.Options:
    return rlidar2map_cli.parse_options([*extra, "vm.example"])


def remote_state(
    status: str = "running",
    *,
    exit_code=None,
    reason: str = "",
    rsync: bool = False,
) -> rlidar2map_cli.RemoteState:
    return rlidar2map_cli.RemoteState(
        exists=True,
        tmux=status in rlidar2map_cli.ACTIVE_STATES,
        session="lidar",
        run_id="20260729T120000Z-123",
        status=status,
        mode="source",
        exit_code=exit_code,
        reason=reason,
        created_at="2026-07-29T12:00:00Z",
        started_at="2026-07-29T12:00:01Z",
        finished_at=(
            "2026-07-29T12:01:00Z"
            if status in rlidar2map_cli.TERMINAL_STATES
            else ""
        ),
        run_dir="/home/test/.lidar2map-runs/lidar",
        results_dir="/home/test/.lidar2map-runs/lidar/results",
        log_path="/home/test/.lidar2map-runs/lidar/run.log",
        rsync=rsync,
    )


class ParseTests(unittest.TestCase):
    def test_recommended_argument_vector_is_preserved(self):
        hostile = [
            "--lidar",
            "--name",
            "A B",
            "--expr",
            "O'Brien; touch PWN",
            "$HOME",
            "*",
            "éà",
        ]
        parsed = rlidar2map_cli.parse_options(["root@vm", "--", *hostile])
        self.assertEqual(parsed.lidar_args, hostile)

    def test_output_directory_is_reserved(self):
        with self.assertRaises(SystemExit):
            rlidar2map_cli.parse_options(["vm", "--", "--lidar", "--output-dir=x"])

    def test_invalid_session_is_rejected(self):
        with self.assertRaises(SystemExit):
            rlidar2map_cli.parse_options(["--session", "../bad", "vm"])

    def test_ssh_target_cannot_be_an_option(self):
        with self.assertRaises(SystemExit):
            rlidar2map_cli.parse_options(["--", "-oProxyCommand=bad"])

    def test_purge_remote_is_a_dedicated_mode(self):
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "--session", "done", "root@vm"]
        )
        self.assertTrue(parsed.purge_remote)
        self.assertEqual(parsed.lidar_args, [])
        for argv in (
            ["--purge-remote", "--restart", "root@vm"],
            ["--purge-remote", "--detach", "root@vm"],
            ["--purge-remote", "--once", "root@vm"],
            ["--purge-remote", "root@vm", "--", "--lidar"],
            ["root@vm", "--purge-remote"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                rlidar2map_cli.parse_options(argv)


class ProtocolTests(unittest.TestCase):
    def test_parse_complete_state(self):
        payload = "\n".join(
            [
                "protocol=1",
                "exists=1",
                "session=lidar",
                "run_id=20260729T120000Z-42",
                "status=failed",
                "tmux=0",
                "mode=source",
                "exit_code=7",
                "reason=lidar2map exited with code 7",
                "created_at=2026-07-29T12:00:00Z",
                "started_at=2026-07-29T12:00:01Z",
                "finished_at=2026-07-29T12:01:00Z",
                "run_dir=/root/.lidar2map-runs/lidar",
                "results_dir=/root/.lidar2map-runs/lidar/results",
                "log_path=/root/.lidar2map-runs/lidar/run.log",
                "rsync=1",
            ]
        )
        state = rlidar2map_cli.parse_state(payload, "lidar")
        self.assertTrue(state.exists)
        self.assertEqual(state.exit_code, 7)
        self.assertTrue(state.terminal)
        self.assertTrue(state.rsync)

    def test_parse_absent_state_with_legacy_tmux_collision(self):
        state = rlidar2map_cli.parse_state(
            "protocol=1\nexists=0\ntmux=1\n", "lidar"
        )
        self.assertFalse(state.exists)
        self.assertTrue(state.tmux)

    def test_unexpected_result_path_is_rejected(self):
        payload = "\n".join(
            [
                "protocol=1",
                "exists=1",
                "session=lidar",
                "run_id=run-1",
                "status=running",
                "tmux=1",
                "run_dir=/tmp/run",
                "results_dir=/etc",
                "log_path=/tmp/run.log",
            ]
        )
        with self.assertRaises(rlidar2map_cli.RunOnVmError):
            rlidar2map_cli.parse_state(payload, "lidar")

    def test_remote_scripts_keep_exact_exit_and_safe_argv(self):
        launch = rlidar2map_cli.REMOTE_LAUNCH_SCRIPT
        query = rlidar2map_cli.REMOTE_QUERY_SCRIPT
        self.assertIn("set -euo pipefail", launch)
        self.assertIn('pipeline_status=("${PIPESTATUS[@]}")', launch)
        self.assertIn('COMMAND+=("${LIDAR_ARGS[@]}"', launch)
        self.assertNotIn("eval ", launch)
        self.assertNotIn("exec bash\"", launch)
        self.assertNotIn("=== run fini ===", launch)
        self.assertIn('tmux has-session -t "=$SESSION"', launch)
        self.assertIn("flock -w 600 9", launch)
        self.assertIn("flock -w 600 8", launch)
        self.assertIn("8>&- 9>&-", launch)
        self.assertNotIn('mkdir -- "$SESSION_LOCK', launch)
        self.assertLess(
            launch.index("\nacquire_session_lock\n"),
            launch.index("\nTMUX_ALIVE=0\n"),
        )
        self.assertLess(
            launch.index('write_value "$RUN_DIR/status" "starting"'),
            launch.index("tmux new-session"),
        )
        self.assertLess(
            launch.index('write_value "$INIT_DIR/bootstrap_pid" "$$"'),
            launch.index('write_value "$INIT_DIR/status" "provisioning"'),
        )
        self.assertLess(
            launch.index('write_value "$INIT_DIR/status" "provisioning"'),
            launch.index('mv -- "$INIT_DIR" "$RUN_DIR"'),
        )
        self.assertLess(
            query.index("if claim_query_lock; then"),
            query.index('write_value "$RUN_DIR/status" "failed"'),
        )
        purge = rlidar2map_cli.REMOTE_PURGE_SCRIPT
        self.assertIn('flock -w 60 9', purge)
        self.assertIn('actual_run_id" != "$EXPECTED_RUN_ID', purge)
        self.assertIn("exit 78", purge)
        self.assertIn('mv -- "$RUN_DIR" "$PURGING_DIR"', purge)
        self.assertIn(
            'if ! rm -rf --one-file-system -- "$PURGING_DIR"; then',
            purge,
        )
        self.assertIn('[ "$receipt_state" != "purging" ]', purge)
        self.assertNotIn('"$BASE/archive"', purge)

    def test_embedded_remote_bash_is_syntactically_valid(self):
        bash = shutil.which("bash")
        if bash is None:
            git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
            bash = str(git_bash) if git_bash.exists() else None
        if bash is None:
            self.skipTest("bash is unavailable")
        for name, script in (
            ("query", rlidar2map_cli.REMOTE_QUERY_SCRIPT),
            ("launch", rlidar2map_cli.REMOTE_LAUNCH_SCRIPT),
            ("purge", rlidar2map_cli.REMOTE_PURGE_SCRIPT),
        ):
            completed = subprocess.run(
                [bash, "-n"],
                input=script.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(
                completed.returncode,
                0,
                "{} script: {}".format(
                    name,
                    completed.stderr.decode("utf-8", errors="replace"),
                ),
            )
        compile(
            rlidar2map_cli.REMOTE_FILE_SYNC_HELPER,
            "<remote-file-sync-helper>",
            "exec",
        )

    def test_parse_purge_response_checks_identity(self):
        payload = (
            "protocol=1\npurged=1\nalready_purged=0\n"
            "session=done\nrun_id=run-42\n"
        )
        self.assertFalse(
            rlidar2map_cli.parse_purge_response(payload, "done", "run-42")
        )
        with self.assertRaises(rlidar2map_cli.RunOnVmError):
            rlidar2map_cli.parse_purge_response(payload, "other", "run-42")


class TransportTests(unittest.TestCase):
    def test_remote_command_round_trips_hostile_arguments(self):
        parsed = rlidar2map_cli.parse_options(
            [
                "--session",
                "safe",
                "root@vm",
                "--",
                "--name",
                "A B",
                "--expr",
                "O'Brien; touch PWN",
                "$HOME",
                "*",
            ]
        )
        deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: None)
        controller = rlidar2map_cli.VmController(parsed, deps)
        remote_args = [
            "source",
            "safe",
            "0",
            "0",
            *parsed.lidar_args,
        ]
        command = controller._ssh_command(remote_args)
        decoded = shlex.split(command[-1], posix=True)
        self.assertEqual(decoded[:3], ["bash", "-s", "--"])
        self.assertEqual(decoded[3:], remote_args)
        self.assertNotIn("shell=True", repr(command))

    def test_reconnect_command_is_absolute_and_preserves_monitor_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_dir = Path(tmp) / "local results"
            identity = Path(tmp) / "key file"
            parsed = rlidar2map_cli.parse_options(
                [
                    "--session",
                    "var-83",
                    "--local-dir",
                    str(local_dir),
                    "--interval",
                    "7.5",
                    "--sync-method",
                    "scp",
                    "--ssh-timeout",
                    "19",
                    "--max-ssh-errors",
                    "8",
                    "--identity",
                    str(identity),
                    "--ssh-option",
                    "ProxyJump=bastion",
                    "--no-bell",
                    "root@vm",
                ]
            )
            controller = rlidar2map_cli.VmController(parsed)
            expected = [
                sys.executable,
                str(MODULE_PATH.resolve()),
                "--session",
                "var-83",
                "--local-dir",
                str(local_dir.resolve()),
                "--interval",
                "7.5",
                "--sync-method",
                "scp",
                "--ssh-timeout",
                "19",
                "--max-ssh-errors",
                "8",
                "--identity",
                str(identity.resolve()),
                "--ssh-option=ProxyJump=bastion",
                "--no-bell",
                "root@vm",
            ]
            rendered = (
                subprocess.list2cmdline(expected)
                if os.name == "nt"
                else shlex.join(expected)
            )
            self.assertEqual(controller.reconnect_command(), rendered)

    def test_frozen_reconnect_command_does_not_repeat_embedded_script(self):
        parsed = rlidar2map_cli.parse_options(["--session", "frozen", "root@vm"])
        controller = rlidar2map_cli.VmController(parsed)
        with mock.patch.object(rlidar2map_cli.sys, "frozen", True, create=True):
            rendered = controller.reconnect_command()
        expected = [
            sys.executable,
            "--session",
            "frozen",
            "--local-dir",
            str(controller._base_local_dir()),
            "--interval",
            "30.0",
            "--sync-method",
            "auto",
            "--ssh-timeout",
            "10",
            "--max-ssh-errors",
            "3",
            "root@vm",
        ]
        command = (
            subprocess.list2cmdline(expected)
            if os.name == "nt"
            else shlex.join(expected)
        )
        self.assertEqual(rendered, command)
        self.assertNotIn(str(MODULE_PATH.resolve()), rendered)

    def test_remote_purge_uses_expected_run_id_and_marks_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                [
                    "--purge-remote",
                    "--local-dir",
                    tmp,
                    "--session",
                    "lidar",
                    "vm.example",
                ]
            )
            controller = rlidar2map_cli.VmController(parsed)
            state = remote_state("succeeded", exit_code=0)
            response = (
                b"protocol=1\npurged=1\nalready_purged=0\n"
                b"session=lidar\nrun_id=20260729T120000Z-123\n"
            )
            calls = []

            def fake_run(command, **kwargs):
                calls.append((list(command), kwargs))
                return subprocess.CompletedProcess(command, 0, response, b"")

            with mock.patch.object(rlidar2map_cli.subprocess, "run", fake_run):
                already = controller.purge_remote(state)

            self.assertFalse(already)
            remote_tokens = shlex.split(calls[0][0][-1], posix=True)
            self.assertEqual(
                remote_tokens[-2:],
                ["lidar", "20260729T120000Z-123"],
            )
            self.assertEqual(
                calls[0][1]["input"],
                rlidar2map_cli.REMOTE_PURGE_SCRIPT.encode("utf-8"),
            )
            pending_path = controller.mark_remote_purge_pending(state, "scp")
            pending_manifest = json.loads(
                pending_path.read_text(encoding="utf-8")
            )
            self.assertTrue(pending_manifest["remote_purge_pending"])
            recovered = controller.load_remote_purge_pending()
            self.assertIsNotNone(recovered)
            assert recovered is not None
            recovered_state, recovered_method = recovered
            self.assertEqual(recovered_state.run_id, state.run_id)
            self.assertEqual(recovered_state.log_path, state.log_path)
            self.assertEqual(recovered_method, "scp")

            manifest_path = controller.mark_remote_purged(state, "scp")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["remote_purged"])
            self.assertFalse(manifest["remote_purge_pending"])
            self.assertTrue(manifest["remote_purged_at"])
            self.assertIsNone(controller.load_remote_purge_pending())
            completed = controller.load_remote_purged()
            self.assertIsNotNone(completed)
            assert completed is not None
            self.assertEqual(completed[0].run_id, state.run_id)

    def test_scp_fallback_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: None)
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state()
            calls = []

            def fake_run(command, **kwargs):
                calls.append((list(command), kwargs))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            with mock.patch.object(
                rlidar2map_cli.subprocess, "run", fake_run
            ), mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value={},
            ):
                ok, method, local_dir = controller.sync_once(state)

            self.assertTrue(ok)
            self.assertEqual(method, "ssh")
            self.assertEqual(calls, [])
            manifest = json.loads(
                (local_dir / "rlidar2map.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["run_id"], state.run_id)
            self.assertFalse(manifest["sync_pending"])
            self.assertFalse(manifest["remote_purge_pending"])

    def test_scp_failure_never_replaces_a_complete_local_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "scp", "vm.example"]
            )
            controller = rlidar2map_cli.VmController(parsed)
            state = remote_state("succeeded", exit_code=0)
            local_results = Path(tmp) / state.run_id / "results"
            destination = local_results / "nested" / "result.mbtiles"
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"complete-old")
            relative = "nested/result.mbtiles"
            encoded = rlidar2map_cli.base64.b64encode(
                relative.encode("utf-8")
            ).decode("ascii")
            new_content = b"complete-new"
            fingerprint = (1, 2, len(new_content), 3)
            inventory = {relative: (encoded, fingerprint)}

            def frame(payload):
                raw = json.dumps(
                    payload, separators=(",", ":")
                ).encode("ascii")
                return rlidar2map_cli.struct.pack(">Q", len(raw)) + raw

            class FakeProcess:
                def __init__(self, output, returncode):
                    self.stdin = io.BytesIO()
                    self.stdout = io.BytesIO(output)
                    self._final_returncode = returncode
                    self._returncode = None

                def wait(self):
                    if self._returncode is None:
                        self._returncode = self._final_returncode
                    return self._returncode

                def poll(self):
                    return self._returncode

                def kill(self):
                    self._returncode = -9

            interrupted_stream = (
                rlidar2map_cli.FILE_STREAM_MAGIC
                + frame(
                    {
                        "type": "file",
                        "path": encoded,
                        "size": len(new_content),
                    }
                )
                + new_content[:4]
            )
            with mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value=inventory,
            ), mock.patch.object(
                    rlidar2map_cli.subprocess,
                    "Popen",
                    return_value=FakeProcess(interrupted_stream, 1),
            ):
                ok = controller._sync_results_scp(state, local_results)

            self.assertFalse(ok)
            self.assertEqual(destination.read_bytes(), b"complete-old")
            self.assertFalse(
                list(local_results.parent.glob(".rlidar2map-sync-*"))
            )
            digest = rlidar2map_cli.hashlib.sha256(new_content).hexdigest()
            complete_stream = (
                rlidar2map_cli.FILE_STREAM_MAGIC
                + frame(
                    {
                        "type": "file",
                        "path": encoded,
                        "size": len(new_content),
                    }
                )
                + new_content
                + frame(
                    {
                        "type": "trailer",
                        "path": encoded,
                        "stable": True,
                        "sha256": digest,
                    }
                )
                + frame({"type": "end", "count": 1})
            )
            with mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value=inventory,
            ), mock.patch.object(
                    rlidar2map_cli.subprocess,
                    "Popen",
                    return_value=FakeProcess(complete_stream, 0),
            ):
                ok = controller._sync_results_scp(state, local_results)

            self.assertTrue(ok)
            self.assertEqual(destination.read_bytes(), b"complete-new")

    def test_scp_missing_remote_file_is_skipped_not_fatal(self):
        # Le pipeline distant purge ses intermédiaires (VRT voisin, etc.)
        # pendant que le sync tourne : un fichier de l'inventaire peut avoir
        # disparu au moment de la copie. Vécu : FileNotFoundError distante
        # plantait tout le lot. Le fichier manquant doit juste être ignoré,
        # les AUTRES fichiers du même lot doivent quand même passer.
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "scp", "vm.example"]
            )
            controller = rlidar2map_cli.VmController(parsed)
            state = remote_state("succeeded", exit_code=0)
            local_results = Path(tmp) / state.run_id / "results"
            local_results.mkdir(parents=True)

            # PAS .vrt : exclu inconditionnellement en amont (cf.
            # ALWAYS_EXCLUDED_EXTENSIONS) donc jamais demandé au tout, ce qui
            # court-circuiterait le chemin de résilience testé ici. Un autre
            # intermédiaire (warp temporaire) illustre le même risque de
            # purge concurrente pour un fichier non filtré en amont.
            gone_relative = "gar9_002x003/warped_3857_tmp.tif"
            gone_encoded = rlidar2map_cli.base64.b64encode(
                gone_relative.encode("utf-8")
            ).decode("ascii")
            ok_relative = "gar9_002x003/result.mbtiles"
            ok_encoded = rlidar2map_cli.base64.b64encode(
                ok_relative.encode("utf-8")
            ).decode("ascii")
            ok_content = b"complete-mbtiles"

            inventory = {
                gone_relative: (gone_encoded, (1, 2, 999, 3)),
                ok_relative: (ok_encoded, (1, 2, len(ok_content), 3)),
            }

            def frame(payload):
                raw = json.dumps(
                    payload, separators=(",", ":")
                ).encode("ascii")
                return rlidar2map_cli.struct.pack(">Q", len(raw)) + raw

            class FakeProcess:
                def __init__(self, output, returncode):
                    self.stdin = io.BytesIO()
                    self.stdout = io.BytesIO(output)
                    self._final_returncode = returncode
                    self._returncode = None

                def wait(self):
                    if self._returncode is None:
                        self._returncode = self._final_returncode
                    return self._returncode

                def poll(self):
                    return self._returncode

                def kill(self):
                    self._returncode = -9

            digest = rlidar2map_cli.hashlib.sha256(ok_content).hexdigest()
            # Ordre = ordre du dict inventory (Python 3.7+ garantit l'ordre
            # d'insertion) : "missing" pour le .vrt, puis file/trailer normal
            # pour le .mbtiles. Code de sortie 0 (pas 74/unstable) : rien n'a
            # été lu de façon instable, le fichier était juste absent.
            stream = (
                rlidar2map_cli.FILE_STREAM_MAGIC
                + frame({"type": "missing", "path": gone_encoded})
                + frame(
                    {
                        "type": "file",
                        "path": ok_encoded,
                        "size": len(ok_content),
                    }
                )
                + ok_content
                + frame(
                    {
                        "type": "trailer",
                        "path": ok_encoded,
                        "stable": True,
                        "sha256": digest,
                    }
                )
                + frame({"type": "end", "count": 2})
            )
            with mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value=inventory,
            ), mock.patch.object(
                    rlidar2map_cli.subprocess,
                    "Popen",
                    return_value=FakeProcess(stream, 0),
            ):
                ok = controller._sync_results_scp(state, local_results)

            self.assertTrue(ok)
            self.assertEqual(
                (local_results / ok_relative).read_bytes(), ok_content
            )
            self.assertFalse((local_results / gone_relative).exists())
            self.assertFalse(
                list(local_results.parent.glob(".rlidar2map-sync-*"))
            )

    def test_purge_markers_are_monotonic_across_stale_monitors(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "vm.example"]
            )
            old_monitor = rlidar2map_cli.VmController(parsed)
            purge_controller = rlidar2map_cli.VmController(parsed)
            succeeded = remote_state("succeeded", exit_code=0)
            stale_running = remote_state("running")

            old_monitor._write_manifest(
                stale_running, "scp", sync_pending=False
            )
            purge_controller.mark_remote_purge_pending(succeeded, "scp")
            old_monitor._write_manifest(
                stale_running, "scp", sync_pending=True
            )

            local_dir = old_monitor.local_run_dir(succeeded)
            pending_marker = local_dir / rlidar2map_cli.PURGE_PENDING_MARKER
            self.assertTrue(pending_marker.is_file())
            recovered = old_monitor.load_remote_purge_pending()
            self.assertIsNotNone(recovered)
            manifest = json.loads(
                (local_dir / "rlidar2map.json").read_text(encoding="utf-8")
            )
            self.assertTrue(manifest["remote_purge_pending"])
            self.assertFalse(manifest["sync_pending"])
            self.assertEqual(manifest["status"], "succeeded")

            purge_controller.mark_remote_purged(succeeded, "scp")
            purged_marker = local_dir / rlidar2map_cli.PURGED_MARKER
            purged_record = purged_marker.read_bytes()
            old_monitor._write_manifest(
                stale_running, "scp", sync_pending=True
            )
            old_monitor.mark_remote_purge_pending(succeeded, "scp")

            self.assertEqual(purged_marker.read_bytes(), purged_record)
            self.assertIsNone(old_monitor.load_remote_purge_pending())
            manifest = json.loads(
                (local_dir / "rlidar2map.json").read_text(encoding="utf-8")
            )
            self.assertTrue(manifest["remote_purged"])
            self.assertFalse(manifest["remote_purge_pending"])
            self.assertFalse(manifest["sync_pending"])
            self.assertFalse(list(local_dir.glob("*.tmp-*")))

    def test_superseded_marker_prevents_old_pending_from_resurrecting(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "vm.example"]
            )
            controller = rlidar2map_cli.VmController(parsed)
            succeeded = remote_state("succeeded", exit_code=0)
            controller.mark_remote_purge_pending(succeeded, "scp")
            controller.mark_remote_purge_superseded(
                succeeded, "scp", "remote run id changed"
            )
            controller._write_manifest(
                remote_state("running"), "scp", sync_pending=True
            )

            self.assertIsNone(controller.load_remote_purge_pending())
            manifest = json.loads(
                (
                    controller.local_run_dir(succeeded) / "rlidar2map.json"
                ).read_text(encoding="utf-8")
            )
            self.assertTrue(manifest["remote_purge_superseded"])
            self.assertFalse(manifest["remote_purge_pending"])
            self.assertFalse(manifest["remote_purged"])

    def test_rsync_is_preferred_when_available_on_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: "rsync")
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state(rsync=True)
            calls = []

            def fake_run(command, **kwargs):
                calls.append(list(command))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            with mock.patch.object(rlidar2map_cli.subprocess, "run", fake_run):
                ok, method, _local_dir = controller.sync_once(state)

            self.assertTrue(ok)
            self.assertEqual(method, "rsync")
            self.assertEqual(calls[0][0], "rsync")
            self.assertIn(
                "--partial-dir=.rlidar2map-rsync-partial", calls[0]
            )
            self.assertIn("--exclude=*.part", calls[0])
            self.assertIn("--exclude=*.part-wal", calls[0])
            self.assertNotEqual(calls[0][0], "scp")

    def test_sync_only_excludes_mapping(self):
        # .vrt exclu inconditionnellement (intermédiaire jamais utile en
        # local, cf. ALWAYS_EXCLUDED_EXTENSIONS), quel que soit --sync-only.
        for value, expected in (
            ("tout", (".vrt",)),
            ("ombrages", (".vrt", ".mbtiles", ".rmap", ".sqlitedb")),
            ("carte", (".vrt", ".tif")),
        ):
            parsed = rlidar2map_cli.parse_options(
                ["--sync-only", value, "vm.example"]
            )
            controller = rlidar2map_cli.VmController(parsed)
            self.assertEqual(
                set(controller._sync_only_excludes()), set(expected),
                msg="--sync-only {}".format(value),
            )

    def test_sync_only_adds_rsync_excludes(self):
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto",
                 "--sync-only", "carte", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: "rsync")
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state(rsync=True)
            calls = []

            def fake_run(command, **kwargs):
                calls.append(list(command))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            with mock.patch.object(rlidar2map_cli.subprocess, "run", fake_run):
                ok, method, _local_dir = controller.sync_once(state)

            self.assertTrue(ok)
            self.assertEqual(method, "rsync")
            # carte : garde mbtiles/rmap/sqlitedb, exclut les .tif intermédiaires.
            self.assertIn("--exclude=*.tif", calls[0])
            self.assertNotIn("--exclude=*.mbtiles", calls[0])
            self.assertNotIn("--exclude=*.rmap", calls[0])
            self.assertNotIn("--exclude=*.sqlitedb", calls[0])

    def test_sync_only_filters_scp_inventory_before_transfer(self):
        # --sync-only carte sur un inventaire 100% .tif : équivalent à un
        # inventaire vide une fois filtré (cf. test_scp_fallback_writes_manifest,
        # même assertion calls == []) -> prouve que le filtre retire bien TOUT
        # avant que la boucle de copie SCP ne s'exécute.
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto",
                 "--sync-only", "carte", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: None)
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state()
            calls = []

            def fake_run(command, **kwargs):
                calls.append((list(command), kwargs))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            encoded = rlidar2map_cli.base64.b64encode(
                b"gar9_001x001_svf_flux.tif"
            ).decode("ascii")
            tif_only_inventory = {
                "gar9_001x001_svf_flux.tif": (encoded, (1, 2, 3, 4)),
            }
            with mock.patch.object(
                rlidar2map_cli.subprocess, "run", fake_run
            ), mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value=tif_only_inventory,
            ):
                ok, method, _local_dir = controller.sync_once(state)

            self.assertTrue(ok)
            self.assertEqual(method, "ssh")
            self.assertEqual(calls, [])

    def test_scp_transfer_skipped_when_local_disk_is_low(self):
        # Garde-fou disque local avant une copie SSH : espace insuffisant ->
        # annulation propre (retry au prochain cycle), pas de tentative de
        # copie qui échouerait à mi-chemin ou saturerait le disque local.
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: None)
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state("succeeded", exit_code=0)
            calls = []

            def fake_run(command, **kwargs):
                calls.append((list(command), kwargs))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            encoded = rlidar2map_cli.base64.b64encode(
                b"gar9_001x001_svf_flux.tif"
            ).decode("ascii")
            inventory = {
                "gar9_001x001_svf_flux.tif": (encoded, (1, 2, 5_000_000_000, 4)),
            }
            fake_usage = mock.Mock(free=1_000)   # bien en dessous de la marge
            local_results = controller.local_run_dir(state) / "results"
            local_results.mkdir(parents=True, exist_ok=True)
            with mock.patch.object(
                rlidar2map_cli.subprocess, "run", fake_run
            ), mock.patch.object(
                    controller,
                    "_remote_results_inventory",
                    return_value=inventory,
            ), mock.patch.object(
                    rlidar2map_cli.shutil, "disk_usage", return_value=fake_usage,
            ):
                # _sync_results_scp directement (pas sync_once) : isole le
                # garde-fou disque du transfert du log final, sans rapport.
                ok = controller._sync_results_scp(state, local_results)

            self.assertFalse(ok)
            self.assertEqual(calls, [])

    def test_print_remote_log_tail_collapses_cr_progress_across_polls(self):
        # run.log est la capture brute (tmux/tee) : ses répétitions \r ne
        # doivent PAS devenir des lignes [VM] distinctes (splitlines() coupe
        # aussi sur \r) - seul l'état final d'une répétition compte, et
        # l'état doit survivre à la frontière entre deux sondages (tail
        # incrémental), une répétition pouvant être coupée en plein milieu.
        with tempfile.TemporaryDirectory() as tmp:
            parsed = rlidar2map_cli.parse_options(
                ["--local-dir", tmp, "--sync-method", "auto", "vm.example"]
            )
            deps = rlidar2map_cli.RuntimeDeps(which=lambda _name: None)
            controller = rlidar2map_cli.VmController(parsed, deps)
            state = remote_state()

            # Sondage 1 : 3 répétitions \r, la dernière coupée avant tout \r/\n
            # (poll suivant en pleine barre de progression).
            chunk1 = (
                b"SVF chunked:  10% (1/10)\r"
                b"SVF chunked:  20% (2/10)\r"
                b"SVF chunked:  30% (3/10)"
            )
            # Sondage 2 : continuation -> \r finalise le 30%, PUIS la vraie
            # ligne de fin, terminée par \n.
            chunk2 = b"\rSVF chunked: done (10 blocks)\n"

            results = iter([chunk1, chunk2])

            def fake_run(_command, **_kwargs):
                return subprocess.CompletedProcess(
                    _command, 0, next(results), b""
                )

            printed = io.StringIO()
            with mock.patch.object(
                rlidar2map_cli.subprocess, "run", fake_run
            ), mock.patch("sys.stdout", printed):
                controller.print_remote_log_tail(state)
                controller.print_remote_log_tail(state)

            output = printed.getvalue()
            self.assertNotIn("10%", output)
            self.assertNotIn("20%", output)
            self.assertNotIn("30%", output)
            self.assertEqual(
                output.count("SVF chunked: done (10 blocks)"), 1
            )


class ControllerTests(unittest.TestCase):
    def _controller_mock(self, states, sync_results):
        fake = mock.Mock()
        fake.query_state.side_effect = list(states)
        fake.sync_once.side_effect = list(sync_results)
        fake.deps = rlidar2map_cli.RuntimeDeps(sleep=lambda _seconds: None)
        fake.reconnect_command.return_value = "resume"
        fake.local_run_dir.return_value = Path("local")
        fake.load_remote_purge_pending.return_value = None
        fake.load_remote_purged.return_value = None
        return fake

    def test_start_monitor_sync_and_success(self):
        absent = rlidar2map_cli.RemoteState(exists=False)
        running = remote_state("running")
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [absent, running, succeeded],
            [
                (True, "scp", Path("local")),
                (True, "scp", Path("local")),
            ],
        )
        parsed = rlidar2map_cli.parse_options(["vm.example", "--", "--lidar"])

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.launch.assert_called_once_with()
        self.assertEqual(fake.sync_once.call_count, 2)
        fake.notify.assert_called_once()

    def test_terminal_run_is_synced_then_purged(self):
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [succeeded],
            [(True, "scp", Path("local"))],
        )
        fake.purge_remote.return_value = False
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.purge_remote.assert_called_once_with(succeeded)
        fake.mark_remote_purge_pending.assert_called_once_with(
            succeeded, "scp"
        )
        fake.mark_remote_purged.assert_called_once_with(succeeded, "scp")
        names = [call[0] for call in fake.mock_calls]
        self.assertLess(
            names.index("sync_once"),
            names.index("mark_remote_purge_pending"),
        )
        self.assertLess(
            names.index("mark_remote_purge_pending"),
            names.index("purge_remote"),
        )
        self.assertLess(
            names.index("purge_remote"),
            names.index("mark_remote_purged"),
        )

    def test_absent_remote_resumes_pending_purge_from_local_manifest(self):
        absent = rlidar2map_cli.RemoteState(exists=False)
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock([absent], [])
        fake.load_remote_purge_pending.return_value = (succeeded, "scp")
        fake.purge_remote.return_value = True
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.sync_once.assert_not_called()
        fake.purge_remote.assert_called_once_with(succeeded)
        fake.mark_remote_purged.assert_called_once_with(succeeded, "scp")

    def test_gone_pending_is_superseded_and_no_new_run_is_deleted(self):
        absent = rlidar2map_cli.RemoteState(exists=False)
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock([absent], [])
        fake.load_remote_purge_pending.return_value = (succeeded, "scp")
        fake.purge_remote.side_effect = (
            rlidar2map_cli.PurgeTargetChangedError("run absent")
        )
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.mark_remote_purge_superseded.assert_called_once_with(
            succeeded, "scp", "run absent"
        )
        fake.mark_remote_purged.assert_not_called()

    def test_already_purged_local_marker_makes_retry_idempotent(self):
        absent = rlidar2map_cli.RemoteState(exists=False)
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock([absent], [])
        fake.load_remote_purged.return_value = (succeeded, "ssh")
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.sync_once.assert_not_called()
        fake.purge_remote.assert_not_called()

    def test_restart_is_blocked_while_a_purge_is_pending(self):
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock([succeeded], [])
        fake.load_remote_purge_pending.return_value = (succeeded, "scp")
        parsed = rlidar2map_cli.parse_options(
            ["--restart", "vm.example", "--", "--lidar"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            with self.assertRaises(rlidar2map_cli.RunOnVmError):
                rlidar2map_cli.run_controller(parsed)

        fake.launch.assert_not_called()

    def test_target_change_after_final_sync_records_superseded(self):
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [succeeded],
            [(True, "scp", Path("local"))],
        )
        fake.purge_remote.side_effect = (
            rlidar2map_cli.PurgeTargetChangedError("run changed")
        )
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            with self.assertRaises(rlidar2map_cli.RunOnVmError):
                rlidar2map_cli.run_controller(parsed)

        fake.mark_remote_purge_pending.assert_called_once_with(
            succeeded, "scp"
        )
        fake.mark_remote_purge_superseded.assert_called_once_with(
            succeeded, "scp", "run changed"
        )
        fake.mark_remote_purged.assert_not_called()

    def test_failed_run_can_be_purged_and_purge_returns_zero(self):
        failed = remote_state("failed", exit_code=7, reason="failed")
        fake = self._controller_mock(
            [failed],
            [(True, "scp", Path("local"))],
        )
        fake.purge_remote.return_value = False
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.purge_remote.assert_called_once_with(failed)

    def test_incomplete_sync_prevents_remote_purge(self):
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [succeeded],
            [(False, "scp", Path("local"))],
        )
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 4)
        fake.purge_remote.assert_not_called()
        fake.mark_remote_purge_pending.assert_not_called()
        fake.mark_remote_purged.assert_not_called()

    def test_active_run_cannot_be_purged(self):
        running = remote_state("running")
        fake = self._controller_mock([running], [])
        parsed = rlidar2map_cli.parse_options(
            ["--purge-remote", "vm.example"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            with self.assertRaises(rlidar2map_cli.RunOnVmError):
                rlidar2map_cli.run_controller(parsed)
        fake.sync_once.assert_not_called()
        fake.purge_remote.assert_not_called()

    def test_existing_run_is_followed_not_relaunched(self):
        running = remote_state("running")
        failed = remote_state(
            "failed", exit_code=7, reason="lidar2map exited with code 7"
        )
        fake = self._controller_mock(
            [running, failed],
            [
                (True, "scp", Path("local")),
                (True, "scp", Path("local")),
            ],
        )
        parsed = options()

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 7)
        fake.launch.assert_not_called()
        self.assertIn("RUN EN ÉCHEC", fake.notify.call_args.args[0])

    def test_transient_ssh_error_is_not_reported_as_process_crash(self):
        running = remote_state("running")
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [running, rlidar2map_cli.SshError("temporary"), succeeded],
            [
                (True, "scp", Path("local")),
                (True, "scp", Path("local")),
                (True, "scp", Path("local")),
            ],
        )
        parsed = options("--max-ssh-errors", "2")

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        titles = [call.args[0] for call in fake.notify.call_args_list]
        self.assertEqual(titles, ["RUN TERMINÉ"])

    def test_success_with_failed_final_sync_returns_four(self):
        succeeded = remote_state("succeeded", exit_code=0)
        fake = self._controller_mock(
            [succeeded],
            [(False, "scp", Path("local"))],
        )
        parsed = options()

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 4)
        self.assertIn(
            "SYNCHRONISATION INCOMPLÈTE",
            fake.notify.call_args.args[0],
        )

    def test_restart_archives_terminal_run_and_launches_new_one(self):
        succeeded = remote_state("succeeded", exit_code=0)
        running = remote_state("running")
        fake = self._controller_mock(
            [succeeded, running],
            [(True, "scp", Path("local"))],
        )
        parsed = rlidar2map_cli.parse_options(
            ["--restart", "--once", "vm.example", "--", "--lidar"]
        )

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 0)
        fake.launch.assert_called_once_with()

    def test_repeated_ssh_failure_is_connection_alert_not_crash(self):
        running = remote_state("running")
        fake = self._controller_mock(
            [
                running,
                rlidar2map_cli.SshError("offline"),
                rlidar2map_cli.SshError("offline"),
            ],
            [
                (True, "scp", Path("local")),
                (True, "scp", Path("local")),
            ],
        )
        parsed = options("--max-ssh-errors", "2")

        with mock.patch.object(rlidar2map_cli, "VmController", return_value=fake):
            rc = rlidar2map_cli.run_controller(parsed)

        self.assertEqual(rc, 3)
        self.assertEqual(
            fake.notify.call_args.args[0],
            "SURVEILLANCE INTERROMPUE",
        )

    def test_keyboard_interrupt_never_kills_remote_tmux(self):
        with mock.patch.object(
            rlidar2map_cli, "run_controller", side_effect=KeyboardInterrupt
        ):
            rc = rlidar2map_cli.main(["vm.example"])
        self.assertEqual(rc, 130)


class EndToEndFakeTransportTests(unittest.TestCase):
    def test_start_follow_and_final_scp_use_real_subprocess_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "scenario.json"
            call_log = root / "calls.ndjson"
            remote_root = root / "remote"
            local_root = root / "local with spaces"
            (remote_root / "results").mkdir(parents=True)
            (remote_root / "results" / "output file.txt").write_text(
                "complete\n",
                encoding="utf-8",
            )
            (remote_root / "results" / "unfinished.mbtiles.part").write_text(
                "partial\n",
                encoding="utf-8",
            )
            provider_stage = (
                remote_root
                / "results"
                / "tile.tif.123.deadbeef.part"
            )
            provider_stage.mkdir()
            (provider_stage / "tile.tif").write_text(
                "provider partial\n",
                encoding="utf-8",
            )
            state_path.write_text(
                json.dumps(
                    {
                        "states": [
                            "absent",
                            "running",
                            "running",
                            "succeeded",
                        ],
                        "query_index": 0,
                    }
                ),
                encoding="utf-8",
            )
            common = (
                sys.executable,
                str(FAKE_TRANSPORT),
            )
            deps = rlidar2map_cli.RuntimeDeps(
                ssh_prefix=common
                + ("ssh", str(state_path), str(call_log), str(remote_root)),
                scp_prefix=common
                + ("scp", str(state_path), str(call_log), str(remote_root)),
                rsync_prefix=common
                + ("rsync", str(state_path), str(call_log), str(remote_root)),
                sleep=lambda _seconds: None,
                which=lambda _name: None,
            )
            hostile = ["--name", "A B", "--expr", "O'Brien; touch PWN", "$HOME", "*"]
            parsed = rlidar2map_cli.parse_options(
                [
                    "--no-bell",
                    "--local-dir",
                    str(local_root),
                    "vm.example",
                    "--",
                    "--lidar",
                    *hostile,
                ]
            )

            rc = rlidar2map_cli.run_controller(parsed, deps)

            self.assertEqual(rc, 0)
            local_run = local_root / "fake-run-1"
            self.assertEqual(
                (local_run / "results" / "output file.txt").read_text(
                    encoding="utf-8"
                ),
                "complete\n",
            )
            self.assertEqual(
                (local_run / "run.log").read_text(encoding="utf-8"),
                "fake remote log\n",
            )
            self.assertFalse(
                (
                    local_run / "results" / "unfinished.mbtiles.part"
                ).exists()
            )
            self.assertFalse(
                (
                    local_run
                    / "results"
                    / "tile.tif.123.deadbeef.part"
                ).exists()
            )
            calls = [
                json.loads(line)
                for line in call_log.read_text(encoding="utf-8").splitlines()
            ]
            order = [
                "{}:{}".format(call["tool"], call.get("kind", "copy"))
                for call in calls
            ]
            self.assertEqual(
                order,
                [
                    "ssh:query",
                    "ssh:launch",
                    "ssh:query",
                    "ssh:log_tail",
                    "ssh:inventory",
                    "ssh:query",
                    "ssh:log_tail",
                    "ssh:inventory",
                    "ssh:copy",
                    "ssh:query",
                    "ssh:log_tail",
                    "ssh:inventory",
                    "scp:copy",
                ],
            )
            self.assertEqual(order.count("ssh:copy"), 1)
            launch_call = next(call for call in calls if call.get("kind") == "launch")
            self.assertEqual(
                launch_call["remote_tokens"][3:],
                ["source", "lidar", "0", "0", "--lidar", *hostile],
            )
            self.assertFalse((root / "PWN").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
