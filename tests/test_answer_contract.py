from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ROOT.name / "scripts" / "ask_claude.py"
SPEC = importlib.util.spec_from_file_location("answer_adapter", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class AnswerContractTests(unittest.TestCase):
    def invoke(self, payload: dict) -> tuple[int, str, str]:
        with mock.patch.object(adapter, "resolve_config", return_value=(None, adapter.FALLBACK_CONFIG)):
            args = adapter.parse_args(["--fresh"])
        stdout, stderr = io.StringIO(), io.StringIO()
        result = subprocess.CompletedProcess(["claude"], 0, json.dumps(payload), "")
        with (
            mock.patch.object(adapter, "parse_args", return_value=args),
            mock.patch.object(adapter, "read_prompt", return_value="review"),
            mock.patch.object(adapter, "resolve_claude_command", return_value=["claude"]),
            mock.patch.object(adapter.subprocess, "run", return_value=result),
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            code = adapter.run()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_unusable_answers_fail_without_success_output(self) -> None:
        for payload in ({}, {"result": None}, {"result": ""}, {"result": " \n\t"},
                        {"result": 42}, {"result": []}, {"result": {}}, {"result": False}):
            with self.subTest(payload=payload):
                code, stdout, stderr = self.invoke(payload)
                self.assertEqual(1, code)
                self.assertEqual("", stdout)
                self.assertIn("Claude returned no answer", stderr)

    def test_useful_answer_keeps_exact_text_and_metadata(self) -> None:
        answer = "  Prüfergebnis\n"
        code, stdout, stderr = self.invoke({"result": answer, "session_id": "session-123", "model": "reported-model"})
        self.assertEqual((0, ""), (code, stderr))
        output = json.loads(stdout)
        self.assertEqual(answer, output["answer"])
        self.assertEqual("session-123", output["session_id"])
        self.assertEqual("reported-model", output["reported_model"])

    def test_provider_error_is_not_replaced_by_empty_answer_error(self) -> None:
        code, stdout, stderr = self.invoke({"is_error": True, "errors": ["budget exhausted"]})
        self.assertEqual((1, ""), (code, stdout))
        self.assertIn("budget exhausted", stderr)
        self.assertNotIn("Claude returned no answer", stderr)


if __name__ == "__main__":
    unittest.main()
