# Ask Claude and SOL for Codex

A second opinion is useful. Two independent second opinions are more useful
when they do not take turns borrowing each other's assumptions.

[![Test](https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/actions/workflows/test.yml/badge.svg)](https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/actions/workflows/test.yml)

Ask Claude and SOL for Codex is an Agent Skill that sends the same question to
the locally authenticated Claude Code and Codex CLIs in parallel. Claude and a
separate SOL session inspect the task independently, then the calling Codex
receives both answers together.

Both conversations persist by default. When both CLIs return session IDs, a
follow-up can continue the pair or target only one adviser. Claude and SOL have
separate model, effort, persistence, customization, and command settings.

The defaults are **Fable 5 with high reasoning effort** and **GPT-5.6 SOL with
`xhigh` (very high) reasoning effort**.

## Why this Skill?

One external review can expose a weak assumption. Two can also expose whether
the apparent agreement survives different model families and runtimes.

That only works when the two consultations remain independent. The wrapper
starts both processes concurrently, gives them the same prompt, and keeps their
answers attributed. It does not ask one model to summarize the other before
the calling Codex sees the evidence.

Agreement is still not proof. The calling Codex must verify any claim before it
becomes an edit, a Decision, a publication, or another confident victory speech
from a green unit test.

## How to use

Invoke the Skill explicitly or ask naturally:

```text
$ask-claude-and-sol-for-codex Review this implementation plan with the defaults.
```

```text
Frage Fable und SOL, ob dieser Fix die eigentliche Ursache behebt.
```

```text
Ask Opus and SOL with max effort to challenge this architecture.
```

Unless overridden, the Skill uses:

| Setting | Claude | SOL |
| --- | --- | --- |
| Model | `claude-fable-5` | `gpt-5.6-sol` |
| Reasoning effort | `high` | `xhigh` |
| Budget ceiling | USD 10 | CLI/account limit |
| Web access | `WebSearch`, `WebFetch` | live Codex search |
| Session persistence | Enabled | Enabled |
| Local customizations | Disabled | Disabled |
| Filesystem access | Read-only tools | Read-only sandbox |

Explicit `$ask-claude-and-sol-for-codex` invocation works on hosts that support
named Skill invocation.

## Install

The repository contains one installable Agent Skill directory. Usually, let
Codex install it with this prompt:

```text
Install this Agent Skill from GitHub and make it available for all my projects:
https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/tree/main/ask-claude-and-sol-for-codex
```

For a manual installation, copy the repository's
`ask-claude-and-sol-for-codex/` directory so the final path is:

```text
<skills-dir>/ask-claude-and-sol-for-codex/SKILL.md
```

The Skill requires Python 3.9 or newer, an authenticated `claude` command, and
an authenticated `codex` command. Codex CLI 0.148.0 or newer is required. The
wrapper itself uses only Python's standard library; CI currently tests it with
Python 3.11.

## What it enforces

- **Real parallelism.** Claude and SOL start concurrently rather than waiting
  for one answer to frame the other.
- **Separate attribution.** The calling Codex receives `requested_model`,
  `requested_effort`, `session_mode`, and `session_id` for each provider, plus
  provider-specific metadata and an attributed `answer` or `error`.
- **Useful partial failure.** If one provider fails, the successful answer is
  still returned. The process exits nonzero and marks the result `partial`.
- **Persistent follow-up.** Persistent calls expose the session IDs returned by
  each CLI. When both IDs are present, the pair can be resumed together; a
  follow-up may also target only Claude or only SOL.
- **Read-only consultation.** Claude has fixed read and web tools. SOL uses the
  Codex read-only sandbox with approvals disabled.
- **Isolation by default.** Local instructions, memories, Skills, plugins,
  hooks, apps, and related customizations stay out of the SOL consultation.
  Claude uses its safe mode.
- **Advice without borrowed authority.** Neither provider can authorize edits,
  publication, spending, a scope expansion, or weaker safeguards.

## How it works

The Python wrapper reads one UTF-8 prompt from standard input and launches two
subprocesses. Claude returns one JSON result. Codex runs in non-interactive
`exec --json` mode and returns a JSONL event stream. The wrapper extracts SOL's
`thread.started` session ID, final `agent_message`, usage data, and completed
item types, then emits one combined JSON object.

The official Codex CLI supports JSONL output and resumable non-interactive
sessions through `codex exec resume`. The implementation follows those public
interfaces rather than reading Codex's private session files.

### Configuration

The shipped
[`config.default.json`](ask-claude-and-sol-for-codex/config.default.json)
contains every persistent setting:

```json
{
  "claude": {
    "command": "claude",
    "model": "claude-fable-5",
    "effort": "high",
    "max_budget_usd": 10,
    "session_persistence": true,
    "customizations": false
  },
  "sol": {
    "command": "codex",
    "model": "gpt-5.6-sol",
    "effort": "xhigh",
    "session_persistence": true,
    "customizations": false,
    "web_search": "live"
  }
}
```

Copy it to `config.json` in the same directory for personal defaults. That file
is ignored by Git and takes precedence over the shipped configuration.

`command` may be a command name on `PATH` or an absolute executable path. This
is useful on Windows when a local npm Codex runtime should take precedence over
the WindowsApps executable. No operating-system-specific path is committed to
the Skill.

Claude and SOL model aliases or full IDs and effort levels can be changed
independently for one request or in the personal configuration. Claude also has
a per-call budget ceiling. The Codex CLI uses the limits of its authenticated
account.

### Conversations

The first paired consultation starts persistent sessions by default. When both
CLIs return session IDs, the combined output exposes them at:

```text
providers.claude.session_id
providers.sol.session_id
```

A paired follow-up can resume both IDs. If only one adviser needs another
question, the wrapper can run with `--provider claude` or `--provider sol`.

`--fresh` disables persistence for one call. `--continue-sessions` resumes each
provider's latest conversation in the current working directory, but explicit
IDs are safer when several discussions exist.

### Isolation

Claude's safe mode and fixed tool list match the original Ask Claude for Codex
boundary.

SOL starts with user config and rules ignored, project instruction loading
suppressed, memories disabled, installed Skill entrypoints disabled, unrelated
capability families disabled, approval policy `never`, and filesystem sandbox
`read-only`. A small fixed instruction file defines only the second-opinion
role. Read-only shell inspection and the configured web-search mode remain
available because a reviewer who cannot inspect the evidence is mostly a mood
ring.

Either provider can deliberately use local customizations for a consultation.
That enables project-specific context, but hooks, plugins, MCP servers, apps,
or similar extensions can introduce behavior outside the wrapper's built-in
boundary. The option therefore reduces isolation and should be explicit.

### Data boundary

Read-only tools do not make arbitrary content safe to disclose. Search queries
and fetched URLs leave the local machine. Prompts must not contain credentials,
tokens, private keys, secret-bearing URLs, private source text that should not
reach either provider, or unrelated personal data.

## Cross-platform behavior

The wrapper avoids shell-specific process construction and accepts executable
names or absolute paths. The PowerShell examples in
[`SKILL.md`](ask-claude-and-sol-for-codex/SKILL.md) set BOM-less UTF-8 before
piping; the Python input layer also tolerates the UTF-8 preamble emitted by
Windows PowerShell 5.1.

Deterministic tests run on Windows, macOS, and Linux. They verify orchestration,
command construction, session routing, JSON and JSONL parsing, partial failure,
isolation flags, and UTF-8 stream setup. Those tests do not claim that every
machine already has authenticated Claude and Codex CLIs.

## Related projects

- [Ask Claude for Codex](https://github.com/benjaminstelzer/ask-claude-for-codex)
  is the single-provider base for this Skill.
- [Scoville Code](https://github.com/benjaminstelzer/scoville-code-anti-ai-slop)
  keeps implementation, scope, and validation with the calling Codex after
  consultation.
- [Codex, Fable-calibrated style](https://github.com/benjaminstelzer/codex-fable-like-system-prompt-for-gpt-5.6-sol)
  supplies the broader collaboration style used by my Codex setup.

## Status

Live provider quality still depends on the selected models, account access, and
available evidence. Parallel disagreement is information, not a bug.

## Sources

- [`SKILL.md`](ask-claude-and-sol-for-codex/SKILL.md) defines activation,
  authority, and the consultation workflow.
- [`ask_claude_and_sol.py`](ask-claude-and-sol-for-codex/scripts/ask_claude_and_sol.py)
  implements parallel Claude and SOL orchestration.
- [`test_ask_claude_and_sol.py`](tests/test_ask_claude_and_sol.py) defines the
  deterministic regression coverage.
- [OpenAI Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
  documents JSONL output and resumable `codex exec` sessions.

## License

MIT - see [LICENSE](LICENSE).
