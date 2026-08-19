from __future__ import annotations

from argparse import Namespace
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "ask-claude-and-sol-for-codex"
    / "scripts"
    / "ask_claude_and_sol.py"
)
SPEC = importlib.util.spec_from_file_location("ask_claude_and_sol", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
ask_both = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ask_both)


def base_args(**overrides: object) -> Namespace:
    values: dict[str, object] = {
        "provider": "both",
        "config_path": None,
        "claude_command": "claude",
        "claude_model": "claude-fable-5",
        "claude_effort": "high",
        "claude_max_budget_usd": 10,
        "claude_resume": None,
        "claude_session_persistence_default": True,
        "claude_customizations_enabled": False,
        "sol_command": "codex",
        "sol_model": "gpt-5.6-sol",
        "sol_effort": "high",
        "sol_web_search": "live",
        "sol_resume": None,
        "sol_session_persistence_default": True,
        "sol_customizations_enabled": False,
        "fresh": False,
        "persistent": False,
        "continue_sessions": False,
    }
    values.update(overrides)
    return Namespace(**values)


class RecordingStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def reconfigure(self, **kwargs: str) -> None:
        self.calls.append(kwargs)


class AskClaudeAndSolTests(unittest.TestCase):
    def test_standard_streams_are_configured_for_utf8(self) -> None:
        streams = [RecordingStream(), RecordingStream(), RecordingStream()]
        with (
            mock.patch.object(ask_both.sys, "stdin", streams[0]),
            mock.patch.object(ask_both.sys, "stdout", streams[1]),
            mock.patch.object(ask_both.sys, "stderr", streams[2]),
        ):
            ask_both.configure_standard_streams()

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
                    ask_both.parse_claude_result(raw_output)

    def test_claude_error_payload_uses_cli_error_messages(self) -> None:
        payload = {
            "is_error": True,
            "subtype": "error_max_budget_usd",
            "errors": ["Reached maximum budget"],
        }
        self.assertEqual(
            ask_both.claude_error_details(payload), "Reached maximum budget"
        )

    def test_sol_jsonl_extracts_session_answer_usage_and_item_types(self) -> None:
        raw = "\n".join(
            [
                '{"type":"thread.started","thread_id":"sol-session"}',
                '{"type":"item.completed","item":{"type":"command_execution"}}',
                '{"type":"item.completed","item":{"type":"agent_message",'
                '"text":"SOL answer"}}',
                '{"type":"turn.completed","usage":{"input_tokens":10}}',
            ]
        )
        result = ask_both.parse_sol_jsonl(raw)
        self.assertEqual(result["session_id"], "sol-session")
        self.assertEqual(result["answer"], "SOL answer")
        self.assertEqual(result["usage"], {"input_tokens": 10})
        self.assertEqual(
            result["completed_item_types"], ["command_execution", "agent_message"]
        )

    def test_sol_jsonl_rejects_invalid_lines(self) -> None:
        with self.assertRaisesRegex(ValueError, "line 2"):
            ask_both.parse_sol_jsonl('{"type":"turn.started"}\nnot-json')

    def test_claude_command_keeps_exact_read_only_tool_surface(self) -> None:
        command = ask_both.build_claude_command(base_args(fresh=True), ["claude"])
        tools = "Read,Grep,Glob,WebSearch,WebFetch"
        self.assertEqual(command[command.index("--tools") + 1], tools)
        self.assertEqual(command[command.index("--allowed-tools") + 1], tools)
        self.assertIn("--safe-mode", command)
        self.assertIn("--no-session-persistence", command)
        for mutating_tool in ("Bash", "Edit", "Write"):
            self.assertNotIn(mutating_tool, tools)

    def test_sol_command_is_read_only_isolated_and_uses_stdin(self) -> None:
        with mock.patch.object(
            ask_both,
            "discover_skill_entrypoints",
            return_value=[Path("/codex/skills/example/SKILL.md")],
        ):
            command = ask_both.build_sol_command(base_args(), ["codex"])

        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertIn("--json", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertIn("--strict-config", command)
        self.assertIn('sandbox_mode="read-only"', command)
        self.assertIn('approval_policy="never"', command)
        self.assertIn('model_reasoning_effort="high"', command)
        self.assertIn('web_search="live"', command)
        self.assertTrue(any(value.startswith("skills.config=[") for value in command))
        self.assertEqual(command[-1], "-")

    def test_paired_resume_uses_each_provider_session_id(self) -> None:
        args = base_args(claude_resume="claude-id", sol_resume="sol-id")
        claude = ask_both.build_claude_command(args, ["claude"])
        with mock.patch.object(ask_both, "discover_skill_entrypoints", return_value=[]):
            sol = ask_both.build_sol_command(args, ["codex"])
        self.assertEqual(claude[claude.index("--resume") + 1], "claude-id")
        self.assertEqual(sol[:3], ["codex", "exec", "resume"])
        self.assertEqual(sol[-2:], ["sol-id", "-"])

    def test_consultations_really_start_in_parallel(self) -> None:
        barrier = threading.Barrier(2)

        def provider(_: Namespace, __: str) -> dict[str, str]:
            barrier.wait(timeout=2)
            return {"status": "ok", "answer": "answer"}

        results = ask_both.run_consultations(
            base_args(), "prompt", {"claude": provider, "sol": provider}
        )
        self.assertEqual(list(results), ["claude", "sol"])
        self.assertEqual(ask_both.consultation_outcome(results), "complete")

    def test_partial_outcome_preserves_success_and_error(self) -> None:
        results = ask_both.run_consultations(
            base_args(),
            "prompt",
            {
                "claude": lambda _args, _prompt: {
                    "status": "ok",
                    "answer": "Claude answer",
                },
                "sol": lambda _args, _prompt: {
                    "status": "error",
                    "error": "authentication failed",
                },
            },
        )
        self.assertEqual(ask_both.consultation_outcome(results), "partial")
        self.assertEqual(results["claude"]["answer"], "Claude answer")
        self.assertEqual(results["sol"]["error"], "authentication failed")

    def test_targeted_follow_up_runs_only_selected_provider(self) -> None:
        claude = mock.Mock(return_value={"status": "ok", "answer": "answer"})
        sol = mock.Mock(return_value={"status": "ok", "answer": "answer"})
        results = ask_both.run_consultations(
            base_args(provider="sol"),
            "prompt",
            {"claude": claude, "sol": sol},
        )
        self.assertEqual(list(results), ["sol"])
        claude.assert_not_called()
        sol.assert_called_once()

    def test_config_validates_independent_provider_settings(self) -> None:
        config = json.loads(json.dumps(ask_both.FALLBACK_CONFIG))
        config["claude"]["model"] = "opus"
        config["sol"]["effort"] = "xhigh"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            loaded = ask_both.load_config(path)
        self.assertEqual(loaded["claude"]["model"], "opus")
        self.assertEqual(loaded["sol"]["effort"], "xhigh")

    def test_help_survives_a_configuration_error(self) -> None:
        with (
            mock.patch.object(
                ask_both,
                "resolve_config",
                side_effect=ValueError("invalid config"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as raised:
                ask_both.parse_args(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_old_codex_cli_is_rejected(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex-cli 0.147.0\n",
            stderr="",
        )
        with mock.patch.object(ask_both.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "too old"):
                ask_both.check_codex_version(["codex"])

    def test_sol_success_reports_cli_and_session_metadata(self) -> None:
        version = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex-cli 0.148.0\n",
            stderr="",
        )
        events = "\n".join(
            [
                '{"type":"thread.started","thread_id":"sol-id"}',
                '{"type":"item.completed","item":{"type":"agent_message",'
                '"text":"SOL answer"}}',
                '{"type":"turn.completed","usage":{"output_tokens":3}}',
            ]
        )
        consultation = subprocess.CompletedProcess(
            args=["codex", "exec"],
            returncode=0,
            stdout=events,
            stderr="",
        )
        with (
            mock.patch.object(ask_both, "resolve_command", return_value=["codex"]),
            mock.patch.object(ask_both, "build_sol_command", return_value=["codex"]),
            mock.patch.object(
                ask_both.subprocess, "run", side_effect=[version, consultation]
            ),
        ):
            result = ask_both.run_sol(base_args(), "prompt")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cli_version"], "0.148.0")
        self.assertEqual(result["session_id"], "sol-id")
        self.assertEqual(result["answer"], "SOL answer")

    def test_isolated_sol_rejects_disallowed_completed_items(self) -> None:
        version = subprocess.CompletedProcess(
            args=["codex", "--version"],
            returncode=0,
            stdout="codex-cli 0.148.0\n",
            stderr="",
        )
        events = "\n".join(
            [
                '{"type":"thread.started","thread_id":"sol-id"}',
                '{"type":"item.completed","item":{"type":"file_change"}}',
                '{"type":"item.completed","item":{"type":"agent_message",'
                '"text":"Changed it"}}',
            ]
        )
        consultation = subprocess.CompletedProcess(
            args=["codex", "exec"], returncode=0, stdout=events, stderr=""
        )
        with (
            mock.patch.object(ask_both, "resolve_command", return_value=["codex"]),
            mock.patch.object(ask_both, "build_sol_command", return_value=["codex"]),
            mock.patch.object(
                ask_both.subprocess, "run", side_effect=[version, consultation]
            ),
        ):
            result = ask_both.run_sol(base_args(), "prompt")
        self.assertEqual(result["status"], "error")
        self.assertIn("file_change", result["error"])


if __name__ == "__main__":
    unittest.main()
