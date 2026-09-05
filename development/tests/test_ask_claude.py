from __future__ import annotations

from argparse import Namespace
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = REPOSITORY_ROOT / "ask-claude-and-sol-for-codex"
SCRIPT_PATH = SKILL_ROOT / "scripts" / "ask_claude.py"
SPEC = importlib.util.spec_from_file_location("ask_claude", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
ask_claude = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ask_claude)


def base_args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "command": "claude",
        "model": "claude-fable-5-1",
        "effort": "high",
        "max_budget_usd": 10,
        "timeout_seconds": None,
        "fresh": False,
        "persistent": False,
        "resume": None,
        "continue_session": False,
        "session_name": None,
        "session_persistence_default": True,
        "customizations_enabled": False,
        "config_path": None,
    }
    values.update(overrides)
    return Namespace(**values)


class RecordingStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


class AskClaudeTests(unittest.TestCase):
    def test_standard_streams_are_configured_for_utf8(self) -> None:
        streams = [RecordingStream(), RecordingStream(), RecordingStream()]
        with (
            mock.patch.object(ask_claude.sys, "stdin", streams[0]),
            mock.patch.object(ask_claude.sys, "stdout", streams[1]),
            mock.patch.object(ask_claude.sys, "stderr", streams[2]),
        ):
            ask_claude.configure_standard_streams()

        self.assertEqual(
            streams[0].calls,
            [{"encoding": "utf-8-sig", "errors": "replace"}],
        )
        for stream in streams[1:]:
            self.assertEqual(
                stream.calls,
                [{"encoding": "utf-8", "errors": "replace"}],
            )

    def test_claude_json_result_must_be_an_object(self) -> None:
        for raw_output in ('["answer"]', '"answer"', "null"):
            with self.subTest(raw_output=raw_output):
                with self.assertRaisesRegex(ValueError, "not an object"):
                    ask_claude.parse_claude_result(raw_output)

    def test_claude_error_payload_uses_cli_error_messages(self) -> None:
        payload = {
            "is_error": True,
            "subtype": "error_max_budget_usd",
            "errors": ["Reached maximum budget"],
        }
        self.assertEqual(
            ask_claude.claude_error_details(payload), "Reached maximum budget"
        )

    def test_claude_command_keeps_exact_read_only_tool_surface(self) -> None:
        command = ask_claude.build_command(base_args(fresh=True), ["claude"])
        tools = "Read,Grep,Glob,WebSearch,WebFetch"
        self.assertEqual(command[command.index("--model") + 1], "claude-fable-5-1")
        self.assertEqual(command[command.index("--effort") + 1], "high")
        self.assertEqual(command[command.index("--tools") + 1], tools)
        self.assertEqual(command[command.index("--allowed-tools") + 1], tools)
        self.assertIn("--safe-mode", command)
        self.assertIn("--no-session-persistence", command)
        for mutating_tool in ("Bash", "Edit", "Write"):
            self.assertNotIn(mutating_tool, tools)

    def test_resume_uses_exact_claude_session_id(self) -> None:
        command = ask_claude.build_command(
            base_args(resume="claude-id"), ["claude"]
        )
        self.assertEqual(command[command.index("--resume") + 1], "claude-id")

    def test_configuration_keeps_only_host_owned_sol_settings(self) -> None:
        config = ask_claude.load_config(ask_claude.DEFAULT_CONFIG_PATH)
        self.assertEqual(config, ask_claude.FALLBACK_CONFIG)
        self.assertEqual(set(config["sol"]), {"model", "effort"})
        self.assertEqual(config["sol"]["model"], "gpt-5.6-sol")
        self.assertEqual(config["sol"]["effort"], "xhigh")
        self.assertEqual(config["claude"]["command"], "claude")
        self.assertEqual(config["claude"]["model"], "claude-fable-5-1")
        self.assertEqual(config["claude"]["effort"], "high")

    def test_config_rejects_removed_sol_cli_fields(self) -> None:
        config = json.loads(json.dumps(ask_claude.FALLBACK_CONFIG))
        config["sol"]["command"] = "codex"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown keys: command"):
                ask_claude.load_config(path)

    def test_help_survives_a_configuration_error(self) -> None:
        with (
            mock.patch.object(
                ask_claude,
                "resolve_config",
                side_effect=ValueError("invalid config"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as raised:
                ask_claude.parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_explicit_claude_command_path_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "claude.exe"
            executable.touch()
            self.assertEqual(
                ask_claude.resolve_claude_command(str(executable)),
                [str(executable.resolve())],
            )

    def test_success_reports_claude_answer_and_session(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=0,
            stdout=(
                '{"is_error":false,"result":"Claude answer",'
                '"session_id":"claude-id","model":"claude-fable-5-1"}'
            ),
            stderr="",
        )
        stdout = io.StringIO()
        with (
            mock.patch.object(ask_claude, "parse_args", return_value=base_args()),
            mock.patch.object(ask_claude, "read_prompt", return_value="prompt"),
            mock.patch.object(
                ask_claude, "resolve_claude_command", return_value=["claude"]
            ),
            mock.patch.object(
                ask_claude, "build_command", return_value=["claude"]
            ),
            mock.patch.object(ask_claude.subprocess, "run", return_value=completed),
            contextlib.redirect_stdout(stdout),
        ):
            exit_code = ask_claude.run()
        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["answer"], "Claude answer")
        self.assertEqual(result["session_id"], "claude-id")

    def test_partial_owner_receives_a_real_claude_error(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["claude"],
            returncode=1,
            stdout="",
            stderr="authentication failed",
        )
        stderr = io.StringIO()
        with (
            mock.patch.object(ask_claude, "parse_args", return_value=base_args()),
            mock.patch.object(ask_claude, "read_prompt", return_value="prompt"),
            mock.patch.object(
                ask_claude, "resolve_claude_command", return_value=["claude"]
            ),
            mock.patch.object(
                ask_claude, "build_command", return_value=["claude"]
            ),
            mock.patch.object(ask_claude.subprocess, "run", return_value=completed),
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = ask_claude.run()
        self.assertEqual(exit_code, 1)
        self.assertIn("authentication failed", stderr.getvalue())

    def test_installable_package_has_no_sol_cli_runtime(self) -> None:
        script = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("codex exec", script)
        self.assertNotIn("check_codex_version", script)
        self.assertNotIn("ThreadPoolExecutor", script)
        self.assertFalse((SKILL_ROOT / "runtime-manifest.json").exists())
        self.assertFalse(
            (SKILL_ROOT / "scripts" / "ask_claude_and_sol.py").exists()
        )


if __name__ == "__main__":
    unittest.main()
