# Ask Claude and SOL for Codex

A second opinion is useful. Two independent second opinions are more useful
when they do not take turns borrowing each other's assumptions.

[![Test](https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/actions/workflows/test.yml/badge.svg)](https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/actions/workflows/test.yml)

Ask Claude and SOL for Codex is an Agent Skill that sends one question to
Claude Code and a fresh Codex SOL subagent in parallel. Claude runs through its
own authenticated CLI. SOL runs inside the Codex host that invoked the Skill,
so it needs no second Codex CLI, runtime installation, executable lookup, or
login.

The defaults are **Fable 5.1 with high reasoning effort** and **GPT-5.6 SOL with
`xhigh` (very high) reasoning effort**.

## Why this architecture?

The earlier implementation launched a second Codex CLI process for SOL. That
worked until the Codex desktop executable found through WindowsApps refused to
start as a child process. Installing another private Codex runtime would repair
the symptom while preserving the unnecessary second runtime.

Current Codex releases already provide subagents in the desktop app, CLI, and
IDE extension. A fresh SOL subagent is therefore the canonical owner of the
second Codex opinion. It starts without copied parent turns, receives the same
self-contained question as Claude, and returns its result to the calling task.

That distinction matters: fresh context protects the comparison from the main
conversation's draft reasoning. It does not create a separate sandbox. The SOL
subagent still inherits host-level instructions, tools, and permissions.

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
| Model | `claude-fable-5-1` | `gpt-5.6-sol` |
| Reasoning effort | `high` | `xhigh` |
| Budget ceiling | USD 10 | Host/account limit |
| Context | Independent Claude session | Fresh subagent, no copied parent turns |
| Continuation | Claude session ID | Agent target in the current Codex task |
| Filesystem boundary | Fixed read-only tools | Host permissions plus a read-only instruction |
| Local customizations | Disabled by Claude safe mode | Host configuration may still apply |

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

Requirements:

- a current Codex host with subagents enabled;
- Python 3.9 or newer;
- an authenticated Claude Code 2.1.255 or newer command.

No Codex CLI installation is required by the Skill. If subagents are disabled
or unavailable, the Skill returns the Claude result as a partial consultation
instead of silently falling back to another Codex runtime.

Claude Code is a separate Anthropic product. Follow Anthropic's official setup
and authentication flow when `claude` is not installed or signed in.

## How it works

The calling Codex prepares one self-contained consultation body before either
provider starts. It then:

1. spawns SOL with a fresh context and immediately retains the returned agent
   target;
2. pipes the same consultation body to the Claude adapter without waiting for
   SOL;
3. collects both answers independently;
4. presents Claude and SOL separately before synthesizing agreement,
   disagreement, and checks that matter.

Starting the subagent first means SOL is already working while the potentially
long Claude process runs. Neither adviser sees the other's answer.

The Python adapter handles only Claude transport: safe-mode tool restrictions,
model and effort selection, budget limits, JSON parsing, errors, and Claude
session continuation. Paired orchestration belongs to `SKILL.md` because only
the Codex host can spawn and manage subagents.

### Configuration

The shipped
[`config.default.json`](ask-claude-and-sol-for-codex/config.default.json)
contains the persistent defaults:

```json
{
  "claude": {
    "command": "claude",
    "model": "claude-fable-5-1",
    "effort": "high",
    "max_budget_usd": 10,
    "session_persistence": true,
    "customizations": false
  },
  "sol": {
    "model": "gpt-5.6-sol",
    "effort": "xhigh"
  }
}
```

Copy it to `config.json` in the same directory for personal defaults. That file
is ignored by Git and takes precedence over the shipped configuration.

`claude.command` may be a command on `PATH` or an absolute executable path.
Claude and SOL model and effort settings can also be overridden for one
consultation. A requested SOL model must be available through the current host;
the Skill does not substitute another model silently.

### Follow-ups

The first paired consultation retains two different continuation handles:

- Claude's returned session ID;
- SOL's agent target in the current Codex task.

A paired follow-up triggers a new turn on the existing SOL agent with the host's
follow-up control and resumes Claude with its explicit session ID. A passive
message does not wake an idle SOL agent. Provider-specific follow-ups contact
only the requested adviser. If one handle is unavailable, the surviving
provider can continue and the result is marked partial.

The SOL target is not a portable CLI session ID. It cannot promise resume from
a new Codex task or another installation. A newly spawned SOL agent is a fresh
consultation, not a continuation.

## Failure behavior

- **Complete:** Claude and SOL both returned answers.
- **Partial:** one provider returned an answer while the other failed or was
  unavailable.
- **Failed:** neither provider returned an answer.

Missing subagent support never triggers a Codex CLI fallback. A Claude failure
never discards a successful SOL result. Agreement is still not proof; the
calling Codex must verify claims before they become edits, Decisions,
publication, spending, or another confident victory speech from a green unit
test.

## Independence and security limits

Claude receives only `Read`, `Grep`, `Glob`, `WebSearch`, and `WebFetch`, with
Bash, Edit, and Write withheld. Safe mode disables local Claude
customizations.

SOL receives a fresh conversation plus a read-only instruction. The current
host spawn interface does not give this Skill a separate sandbox or approval
policy for that subagent. Host-level system instructions, tools, permissions,
Skills, plugins, and other capabilities may still apply. The Skill therefore
claims conversational independence, not a customization-free or separately
sandboxed SOL runtime.

Read-only intent does not make arbitrary content safe to disclose. Search
queries and fetched URLs leave the local machine. Prompts must not contain
credentials, tokens, private keys, secret-bearing URLs, private source text
that should not reach either provider, or unrelated personal data.

## Validation boundary

Deterministic tests cover the Claude adapter, configuration, UTF-8 handling,
session routing, error preservation, and the absence of the former Codex CLI
runtime path. They cannot prove host-native subagent orchestration.

Host-level acceptance checks must verify fresh SOL context, parallel dispatch,
partial failure in both directions, provider-specific follow-ups, attribution,
and an unchanged repository after a nominal review.

## Sources

- [`SKILL.md`](ask-claude-and-sol-for-codex/SKILL.md) defines activation,
  orchestration, authority, and failure behavior.
- [`ask_claude.py`](ask-claude-and-sol-for-codex/scripts/ask_claude.py) implements
  the Claude transport.
- [`test_ask_claude.py`](tests/test_ask_claude.py) defines deterministic adapter
  coverage.
- [OpenAI Codex subagents](https://developers.openai.com/codex/subagents/)
  documents host-native parallel agents in current Codex releases.
- [Anthropic Claude Code setup](https://code.claude.com/docs/en/setup) documents
  Claude installation and authentication.

## License

MIT - see [LICENSE](LICENSE).
