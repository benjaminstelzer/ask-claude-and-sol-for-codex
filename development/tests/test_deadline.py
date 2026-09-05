from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "deadline_adapter", ROOT / ROOT.name / "scripts" / "ask_claude.py"
)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class DeadlineTests(unittest.TestCase):
    def args(self, argv=()):
        with mock.patch.object(adapter, "resolve_config", return_value=(None, adapter.FALLBACK_CONFIG)):
            return adapter.parse_args(list(argv))

    def invoke(self, args, command):
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(adapter, "parse_args", return_value=args),
            mock.patch.object(adapter, "read_prompt", return_value="synthetic public fixture"),
            mock.patch.object(adapter, "resolve_claude_command", return_value=["unused"]),
            mock.patch.object(adapter, "build_command", return_value=command),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = adapter.run()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_deadline_is_opt_in_and_not_forwarded_to_provider(self):
        args = self.args()
        self.assertIsNone(args.timeout_seconds)
        selected = self.args(["--timeout-seconds", "1.5"])
        self.assertEqual(1.5, selected.timeout_seconds)
        command = adapter.build_command(selected, ["claude"])
        self.assertNotIn("--timeout-seconds", command)
        with mock.patch.object(adapter.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, '{"result":"ok"}', "")) as run:
            code, _, _ = self.invoke(args, ["unused"])
        self.assertEqual(0, code)
        run.assert_called_once()
        self.assertIsNone(run.call_args.kwargs["timeout"])

    def test_invalid_deadlines_fail_argument_parsing(self):
        for value in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.args(["--timeout-seconds", value])
                self.assertEqual(2, error.exception.code)

    def test_real_waiting_direct_child_is_killed_and_reaped(self):
        processes = []
        real_popen = subprocess.Popen

        def launch(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        started = time.monotonic()
        with mock.patch.object(adapter.subprocess, "Popen", side_effect=launch):
            code, stdout, stderr = self.invoke(
                self.args(["--timeout-seconds", "0.4"]),
                [sys.executable, "-c", "import time; time.sleep(60)"],
            )
        self.assertEqual((124, ""), (code, stdout))
        self.assertIn("deadline exceeded", stderr)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(1, len(processes))
        self.assertIsNotNone(processes[0].returncode)
        self.assertNotEqual(0, processes[0].poll())

    def test_success_provider_error_and_resume_survive_selected_deadline(self):
        for payload, expected in (
            ({"result": "exact answer", "session_id": "known-session"}, 0),
            ({"is_error": True, "errors": ["synthetic provider error"]}, 1),
        ):
            with self.subTest(payload=payload):
                command = [sys.executable, "-c", "print(" + repr(json.dumps(payload)) + ")"]
                code, stdout, stderr = self.invoke(
                    self.args(["--resume", "known-session", "--timeout-seconds", "5"]),
                    command,
                )
                self.assertEqual(expected, code, stderr)
                if code == 0:
                    output = json.loads(stdout)
                    self.assertEqual("known-session", output["session_id"])
                    self.assertEqual("resume", output["session_mode"])
                    self.assertEqual("exact answer", output["answer"])
                else:
                    self.assertEqual("", stdout)
                    self.assertIn("synthetic provider error", stderr)

    def test_timeout_preserves_known_resume_handle_without_retry(self):
        with mock.patch.object(adapter.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired(["unused"], 1)) as run:
            code, stdout, stderr = self.invoke(
                self.args(["--resume", "known-session", "--timeout-seconds", "1"]),
                ["unused"],
            )
        run.assert_called_once()
        self.assertEqual((124, ""), (code, stdout))
        self.assertIn("known-session", stderr)
        self.assertIn("No automatic retry", stderr)


if __name__ == "__main__":
    unittest.main()
