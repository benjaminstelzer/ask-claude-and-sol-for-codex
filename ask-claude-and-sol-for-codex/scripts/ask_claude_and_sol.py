#!/usr/bin/env python3
"""Ask Claude Code and Codex SOL for parallel read-only second opinions."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


CLAUDE_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
SOL_EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
SOL_WEB_SEARCH_MODES = ("disabled", "cached", "indexed", "live")
READ_ONLY_CLAUDE_TOOLS = "Read,Grep,Glob,WebSearch,WebFetch"
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
VERSION_PATTERN = re.compile(r"codex-cli\s+(\d+)\.(\d+)\.(\d+)")
MIN_CODEX_CLI_VERSION = (0, 148, 0)
SKILL_DIR = Path(__file__).resolve().parent.parent
SOL_INSTRUCTIONS_PATH = SKILL_DIR / "references" / "sol-second-opinion.md"
USER_CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.default.json"

CLAUDE_CONFIG_KEYS = {
    "command",
    "model",
    "effort",
    "max_budget_usd",
    "session_persistence",
    "customizations",
}
SOL_CONFIG_KEYS = {
    "command",
    "model",
    "effort",
    "session_persistence",
    "customizations",
    "web_search",
}
FALLBACK_CONFIG: dict[str, Any] = {
    "claude": {
        "command": "claude",
        "model": "claude-fable-5",
        "effort": "high",
        "max_budget_usd": 10,
        "session_persistence": True,
        "customizations": False,
    },
    "sol": {
        "command": "codex",
        "model": "gpt-5.6-sol",
        "effort": "xhigh",
        "session_persistence": True,
        "customizations": False,
        "web_search": "live",
    },
}

SOL_DISABLED_FEATURES = (
    "apps",
    "auth_elicitation",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "memories",
    "multi_agent",
    "plugins",
    "recommended_plugins",
    "remote_plugin",
    "request_permissions_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "view_image",
    "workspace_dependencies",
)
SOL_DISALLOWED_COMPLETED_ITEMS = {
    "file_change",
    "image_generation",
    "mcp_tool_call",
    "computer_use",
}


def configure_standard_streams() -> None:
    input_reconfigure = getattr(sys.stdin, "reconfigure", None)
    if callable(input_reconfigure):
        input_reconfigure(encoding="utf-8-sig", errors="replace")

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def positive_amount(value: str) -> float:
    amount = float(value)
    if not math.isfinite(amount) or amount <= 0:
        raise argparse.ArgumentTypeError("budget must be greater than zero")
    return amount


def model_name(value: str) -> str:
    if not MODEL_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError("model must be an alias or full model ID")
    return value


def non_empty_value(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("value must not be empty")
    return value


def _validate_exact_keys(
    payload: dict[str, Any], expected: set[str], label: str, path: Path
) -> None:
    missing = expected - payload.keys()
    unknown = payload.keys() - expected
    if missing:
        raise ValueError(
            f"{label} config in {path} is missing: {', '.join(sorted(missing))}"
        )
    if unknown:
        raise ValueError(
            f"{label} config in {path} has unknown keys: "
            f"{', '.join(sorted(unknown))}"
        )


def _validate_common_provider_config(
    payload: dict[str, Any], label: str, path: Path
) -> None:
    for key in ("command", "model"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise ValueError(f"{label}.{key} in config {path} must be a string")
    try:
        model_name(payload["model"])
    except argparse.ArgumentTypeError as error:
        raise ValueError(f"invalid {label}.model in config {path}: {error}") from error
    for key in ("session_persistence", "customizations"):
        if not isinstance(payload[key], bool):
            raise ValueError(f"{label}.{key} in config {path} must be true or false")


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"cannot read config {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in config {path}: {error}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"config {path} must contain a JSON object")
    _validate_exact_keys(payload, {"claude", "sol"}, "top-level", path)

    claude = payload["claude"]
    sol = payload["sol"]
    if not isinstance(claude, dict) or not isinstance(sol, dict):
        raise ValueError(f"claude and sol in config {path} must be JSON objects")

    _validate_exact_keys(claude, CLAUDE_CONFIG_KEYS, "claude", path)
    _validate_exact_keys(sol, SOL_CONFIG_KEYS, "sol", path)
    _validate_common_provider_config(claude, "claude", path)
    _validate_common_provider_config(sol, "sol", path)

    if claude["effort"] not in CLAUDE_EFFORT_LEVELS:
        raise ValueError(
            f"claude.effort in config {path} must be one of: "
            f"{', '.join(CLAUDE_EFFORT_LEVELS)}"
        )
    budget = claude["max_budget_usd"]
    if (
        isinstance(budget, bool)
        or not isinstance(budget, (int, float))
        or not math.isfinite(budget)
        or budget <= 0
    ):
        raise ValueError(
            f"claude.max_budget_usd in config {path} must be greater than zero"
        )

    if sol["effort"] not in SOL_EFFORT_LEVELS:
        raise ValueError(
            f"sol.effort in config {path} must be one of: "
            f"{', '.join(SOL_EFFORT_LEVELS)}"
        )
    if sol["web_search"] not in SOL_WEB_SEARCH_MODES:
        raise ValueError(
            f"sol.web_search in config {path} must be one of: "
            f"{', '.join(SOL_WEB_SEARCH_MODES)}"
        )
    return payload


def resolve_config(explicit_path: Path | None) -> tuple[Path | None, dict[str, Any]]:
    if explicit_path is not None:
        return explicit_path, load_config(explicit_path)
    if USER_CONFIG_PATH.is_file():
        return USER_CONFIG_PATH, load_config(USER_CONFIG_PATH)
    if DEFAULT_CONFIG_PATH.is_file():
        return DEFAULT_CONFIG_PATH, load_config(DEFAULT_CONFIG_PATH)
    return None, json.loads(json.dumps(FALLBACK_CONFIG))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", type=Path)
    config_args, _ = config_parser.parse_known_args(raw_argv)
    try:
        config_path, config = resolve_config(config_args.config)
    except ValueError:
        if not any(argument in ("-h", "--help") for argument in raw_argv):
            raise
        config_path, config = None, json.loads(json.dumps(FALLBACK_CONFIG))

    claude = config["claude"]
    sol = config["sol"]
    parser = argparse.ArgumentParser(
        description=(
            "Pipe one prompt from stdin to Claude Code and Codex SOL in "
            "parallel. Both consultations are read-only by default."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=config_path,
        help="use a specific JSON config instead of config.json or config.default.json",
    )
    parser.add_argument(
        "--provider",
        choices=("both", "claude", "sol"),
        default="both",
        help="consult both providers or target one provider for a follow-up",
    )
    parser.add_argument("--claude-command", type=non_empty_value, default=claude["command"])
    parser.add_argument("--claude-model", type=model_name, default=claude["model"])
    parser.add_argument(
        "--claude-effort", choices=CLAUDE_EFFORT_LEVELS, default=claude["effort"]
    )
    parser.add_argument(
        "--claude-max-budget-usd",
        type=positive_amount,
        default=claude["max_budget_usd"],
    )
    parser.add_argument("--sol-command", type=non_empty_value, default=sol["command"])
    parser.add_argument("--sol-model", type=model_name, default=sol["model"])
    parser.add_argument("--sol-effort", choices=SOL_EFFORT_LEVELS, default=sol["effort"])
    parser.add_argument(
        "--sol-web-search",
        choices=SOL_WEB_SEARCH_MODES,
        default=sol["web_search"],
    )

    session_group = parser.add_mutually_exclusive_group()
    session_group.add_argument(
        "--fresh", action="store_true", help="run selected providers without persistence"
    )
    session_group.add_argument(
        "--persistent",
        action="store_true",
        help="start persistent sessions for selected providers",
    )
    session_group.add_argument(
        "--continue-sessions",
        action="store_true",
        help="continue each selected provider's latest session in this directory",
    )
    parser.add_argument(
        "--claude-resume", type=non_empty_value, metavar="SESSION_ID_OR_NAME"
    )
    parser.add_argument("--sol-resume", type=non_empty_value, metavar="SESSION_ID_OR_NAME")

    claude_customizations = parser.add_mutually_exclusive_group()
    claude_customizations.add_argument(
        "--with-claude-customizations",
        dest="claude_customizations_enabled",
        action="store_true",
    )
    claude_customizations.add_argument(
        "--without-claude-customizations",
        dest="claude_customizations_enabled",
        action="store_false",
    )
    sol_customizations = parser.add_mutually_exclusive_group()
    sol_customizations.add_argument(
        "--with-sol-customizations",
        dest="sol_customizations_enabled",
        action="store_true",
    )
    sol_customizations.add_argument(
        "--without-sol-customizations",
        dest="sol_customizations_enabled",
        action="store_false",
    )
    parser.set_defaults(
        claude_customizations_enabled=claude["customizations"],
        sol_customizations_enabled=sol["customizations"],
    )

    args = parser.parse_args(raw_argv)
    args.config_path = config_path
    args.claude_session_persistence_default = claude["session_persistence"]
    args.sol_session_persistence_default = sol["session_persistence"]
    if (args.claude_resume or args.sol_resume) and (
        args.fresh or args.persistent or args.continue_sessions
    ):
        parser.error(
            "provider resume IDs cannot be combined with --fresh, --persistent, "
            "or --continue-sessions"
        )
    if args.provider == "claude" and args.sol_resume:
        parser.error("--sol-resume requires --provider sol or --provider both")
    if args.provider == "sol" and args.claude_resume:
        parser.error("--claude-resume requires --provider claude or --provider both")
    return args


def resolve_command(requested: str, label: str) -> list[str]:
    expanded = os.path.expandvars(os.path.expanduser(requested))
    path = Path(expanded)
    resolved = str(path.resolve()) if path.is_file() else shutil.which(expanded)
    if resolved is None:
        raise RuntimeError(f"{label} CLI was not found: {requested}")

    resolved_path = Path(resolved)
    if resolved_path.suffix.lower() == ".ps1":
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            raise RuntimeError(
                f"{label} resolves to a PowerShell script, but PowerShell was not found"
            )
        return [powershell, "-NoProfile", "-File", str(resolved_path)]
    return [str(resolved_path)]


def read_prompt() -> str:
    prompt = sys.stdin.read()
    if not prompt.strip():
        raise ValueError("prompt must be provided through stdin")
    return prompt


def provider_session_mode(args: argparse.Namespace, provider: str) -> str:
    resume = getattr(args, f"{provider}_resume")
    if resume:
        return "resume"
    if args.continue_sessions:
        return "continue"
    if args.fresh:
        return "fresh"
    if args.persistent:
        return "persistent"
    if getattr(args, f"{provider}_session_persistence_default"):
        return "persistent"
    return "fresh"


def build_claude_command(
    args: argparse.Namespace, claude_command: list[str]
) -> list[str]:
    command = [
        *claude_command,
        "-p",
        "--model",
        args.claude_model,
        "--effort",
        args.claude_effort,
        "--output-format",
        "json",
        "--permission-mode",
        "dontAsk",
        "--tools",
        READ_ONLY_CLAUDE_TOOLS,
        "--allowed-tools",
        READ_ONLY_CLAUDE_TOOLS,
        "--max-budget-usd",
        format(args.claude_max_budget_usd, "g"),
    ]
    mode = provider_session_mode(args, "claude")
    if mode == "fresh":
        command.append("--no-session-persistence")
    elif mode == "resume":
        command.extend(["--resume", args.claude_resume])
    elif mode == "continue":
        command.append("--continue")
    if not args.claude_customizations_enabled:
        command.append("--safe-mode")
    return command


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def discover_skill_entrypoints(codex_home: Path | None = None) -> list[Path]:
    root = (codex_home or _codex_home()) / "skills"
    if not root.is_dir():
        return []
    return sorted(path.resolve() for path in root.rglob("SKILL.md") if path.is_file())


def disabled_skills_override(paths: list[Path]) -> str:
    entries = ",".join(
        f"{{path={_toml_string(str(path))},enabled=false}}" for path in paths
    )
    return f"skills.config=[{entries}]"


def sol_isolation_arguments(skill_paths: list[Path] | None = None) -> list[str]:
    paths = discover_skill_entrypoints() if skill_paths is None else skill_paths
    arguments = [
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "-c",
        "project_doc_max_bytes=0",
        "-c",
        "agents.enabled=false",
        "-c",
        "apps._default.enabled=false",
        "-c",
        "memories.generate_memories=false",
        "-c",
        "memories.use_memories=false",
        "-c",
        f"model_instructions_file={_toml_string(str(SOL_INSTRUCTIONS_PATH.resolve()))}",
        "-c",
        disabled_skills_override(paths),
    ]
    for feature in SOL_DISABLED_FEATURES:
        arguments.extend(["--disable", feature])
    return arguments


def build_sol_command(args: argparse.Namespace, sol_command: list[str]) -> list[str]:
    mode = provider_session_mode(args, "sol")
    command = [*sol_command, "exec"]
    if mode in ("resume", "continue"):
        command.append("resume")
    command.extend(
        [
            "--json",
            "--model",
            args.sol_model,
            "--skip-git-repo-check",
            "-c",
            'approval_policy="never"',
            "-c",
            'sandbox_mode="read-only"',
            "-c",
            f"model_reasoning_effort={_toml_string(args.sol_effort)}",
            "-c",
            f"web_search={_toml_string(args.sol_web_search)}",
        ]
    )
    if not args.sol_customizations_enabled:
        command.extend(sol_isolation_arguments())
    if mode == "fresh":
        command.append("--ephemeral")
    if mode == "resume":
        command.append(args.sol_resume)
    elif mode == "continue":
        command.append("--last")
    command.append("-")
    return command


def optional_field(payload: dict[str, Any], name: str) -> Any:
    value = payload.get(name)
    return value if value not in ("", None) else None


def parse_claude_result(raw_output: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as error:
        raise ValueError(f"Claude returned invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Claude returned JSON that is not an object")
    return payload


def claude_error_details(payload: dict[str, Any]) -> str | None:
    subtype = payload.get("subtype")
    has_error_subtype = isinstance(subtype, str) and subtype.startswith("error")
    if payload.get("is_error") is not True and not has_error_subtype:
        return None
    errors = payload.get("errors")
    if isinstance(errors, list):
        messages = [message for message in errors if isinstance(message, str)]
        if messages:
            return "; ".join(messages)
    for key in ("result", "terminal_reason", "subtype"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "Claude reported an unspecified error"


def parse_sol_jsonl(raw_output: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_output.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"SOL returned invalid JSONL on line {line_number}: {error}"
            ) from error
        if not isinstance(event, dict):
            raise ValueError(f"SOL JSONL line {line_number} is not an object")
        events.append(event)
    if not events:
        raise ValueError("SOL returned no JSONL events")

    thread_id: str | None = None
    answer: str | None = None
    usage: dict[str, Any] | None = None
    completed_item_types: list[str] = []
    errors: list[str] = []
    for event in events:
        event_type = event.get("type")
        if event_type == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
        elif event_type == "item.completed":
            item = event.get("item")
            if isinstance(item, dict):
                item_type = item.get("type")
                if isinstance(item_type, str):
                    completed_item_types.append(item_type)
                if item_type == "agent_message" and isinstance(item.get("text"), str):
                    answer = item["text"]
        elif event_type == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = event["usage"]
        elif event_type in ("turn.failed", "error"):
            error = event.get("error") or event.get("message")
            if isinstance(error, dict):
                error = error.get("message")
            errors.append(str(error or event_type))

    return {
        "session_id": thread_id,
        "answer": answer,
        "usage": usage,
        "completed_item_types": completed_item_types,
        "errors": errors,
    }


def _process_error(completed: subprocess.CompletedProcess[str]) -> str:
    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()
    return stderr or stdout or f"process exited with code {completed.returncode}"


def run_claude(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    try:
        command = build_claude_command(
            args, resolve_command(args.claude_command, "Claude Code")
        )
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(_process_error(completed))
        payload = parse_claude_result(completed.stdout)
        error_details = claude_error_details(payload)
        if error_details is not None:
            raise RuntimeError(error_details)
        answer = payload.get("result")
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Claude returned no answer")
        return {
            "status": "ok",
            "requested_model": args.claude_model,
            "requested_effort": args.claude_effort,
            "session_mode": provider_session_mode(args, "claude"),
            "session_id": optional_field(payload, "session_id"),
            "customizations_enabled": args.claude_customizations_enabled,
            "reported_model": optional_field(payload, "model"),
            "num_turns": optional_field(payload, "num_turns"),
            "duration_ms": optional_field(payload, "duration_ms"),
            "total_cost_usd": optional_field(payload, "total_cost_usd"),
            "permission_denials": payload.get("permission_denials") or [],
            "answer": answer,
        }
    except (OSError, RuntimeError, ValueError) as error:
        return {
            "status": "error",
            "requested_model": args.claude_model,
            "requested_effort": args.claude_effort,
            "session_mode": provider_session_mode(args, "claude"),
            "error": str(error),
        }


def parse_codex_version(raw_output: str) -> tuple[int, int, int]:
    match = VERSION_PATTERN.search(raw_output)
    if match is None:
        raise ValueError(f"cannot parse Codex CLI version from: {raw_output.strip()}")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def check_codex_version(sol_command: list[str]) -> str:
    completed = subprocess.run(
        [*sol_command, "--version"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(_process_error(completed))
    raw_version = (completed.stdout or completed.stderr).strip()
    version = parse_codex_version(raw_version)
    if version < MIN_CODEX_CLI_VERSION:
        minimum = ".".join(str(part) for part in MIN_CODEX_CLI_VERSION)
        raise RuntimeError(
            f"Codex CLI {'.'.join(str(part) for part in version)} is too old; "
            f"version {minimum} or newer is required"
        )
    return ".".join(str(part) for part in version)


def run_sol(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    try:
        sol_command = resolve_command(args.sol_command, "Codex")
        cli_version = check_codex_version(sol_command)
        command = build_sol_command(args, sol_command)
        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(_process_error(completed))
        payload = parse_sol_jsonl(completed.stdout)
        if payload["errors"]:
            raise RuntimeError("; ".join(payload["errors"]))
        if not isinstance(payload["answer"], str) or not payload["answer"].strip():
            raise RuntimeError("SOL returned no answer")
        disallowed = sorted(
            set(payload["completed_item_types"]) & SOL_DISALLOWED_COMPLETED_ITEMS
        )
        if disallowed and not args.sol_customizations_enabled:
            raise RuntimeError(
                "isolated SOL run used disallowed completed item types: "
                + ", ".join(disallowed)
            )
        return {
            "status": "ok",
            "requested_model": args.sol_model,
            "requested_effort": args.sol_effort,
            "session_mode": provider_session_mode(args, "sol"),
            "session_id": payload["session_id"],
            "customizations_enabled": args.sol_customizations_enabled,
            "cli_version": cli_version,
            "web_search": args.sol_web_search,
            "usage": payload["usage"],
            "completed_item_types": payload["completed_item_types"],
            "answer": payload["answer"],
        }
    except (OSError, RuntimeError, ValueError) as error:
        return {
            "status": "error",
            "requested_model": args.sol_model,
            "requested_effort": args.sol_effort,
            "session_mode": provider_session_mode(args, "sol"),
            "error": str(error),
        }


ProviderRunner = Callable[[argparse.Namespace, str], dict[str, Any]]


def run_consultations(
    args: argparse.Namespace,
    prompt: str,
    runners: dict[str, ProviderRunner] | None = None,
) -> dict[str, dict[str, Any]]:
    available = runners or {"claude": run_claude, "sol": run_sol}
    selected = ["claude", "sol"] if args.provider == "both" else [args.provider]
    unordered: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {
            executor.submit(available[provider], args, prompt): provider
            for provider in selected
        }
        for future in as_completed(futures):
            provider = futures[future]
            try:
                unordered[provider] = future.result()
            except Exception as error:  # Keep the sibling result visible.
                unordered[provider] = {"status": "error", "error": str(error)}
    return {provider: unordered[provider] for provider in selected}


def consultation_outcome(results: dict[str, dict[str, Any]]) -> str:
    successes = sum(result.get("status") == "ok" for result in results.values())
    if successes == len(results):
        return "complete"
    if successes:
        return "partial"
    return "failed"


def run() -> int:
    try:
        args = parse_args()
        prompt = read_prompt()
    except (RuntimeError, ValueError) as error:
        print(f"ask-claude-and-sol: {error}", file=sys.stderr)
        return 2

    results = run_consultations(args, prompt)
    outcome = consultation_outcome(results)
    output = {
        "config_path": (
            str(args.config_path.resolve()) if args.config_path is not None else None
        ),
        "outcome": outcome,
        "providers": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if outcome == "complete" else 1


if __name__ == "__main__":
    configure_standard_streams()
    raise SystemExit(run())
