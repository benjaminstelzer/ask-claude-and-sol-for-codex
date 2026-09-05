# Ask Claude and SOL for Codex

A second opinion is useful. Two independent second opinions are more useful
when they do not take turns borrowing each other's assumptions.

Ask Claude and SOL for Codex is an Agent Skill that sends one question to
Claude Code and a fresh Codex SOL subagent in parallel. Claude runs through its
own authenticated CLI. SOL runs inside the Codex host that invoked the Skill,
so it needs no second Codex CLI, runtime installation, executable lookup, or
login.

The defaults are **Fable 5.1 with high reasoning effort** and **GPT-5.6 SOL with
`xhigh` (very high) reasoning effort**.

## Why this Skill?

A fresh SOL subagent receives the same self-contained question as Claude,
without copied parent turns or the other adviser's answer. It uses the existing
Codex host rather than launching another Codex CLI.

Fresh context separates the conversations. It does not create a separate
sandbox. SOL still inherits host instructions, tools, and permissions.

## How to use

Invoke the Skill explicitly or ask naturally:

```text
$ask-claude-and-sol-for-codex Review this implementation plan with the defaults.
```

```text
Ask Fable and SOL whether this fix addresses the root cause.
```

```text
Ask Claude using model alias opus and SOL with max effort to challenge this architecture.
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

In a local Codex session, ask:

```text
Install this Agent Skill for all my projects from this exact package directory:
https://github.com/benjaminstelzer/ask-claude-and-sol-for-codex/tree/main/ask-claude-and-sol-for-codex
Preserve existing customizations and ask before overwriting conflicting files.
Report the installed location and whether the host discovers the Skill.
```

The agent needs source access and permission to write to its personal Skills
location. Manual fallback: [Codex Skills guide](https://learn.chatgpt.com/docs/build-skills).

Requires Python 3.9 or newer and an authenticated Claude Code 2.1.255 or newer.
Claude usage limits and model charges apply.
The Codex host also needs subagents and access to `gpt-5.6-sol` with `xhigh`
effort. No separate Codex CLI is required. Missing subagent support produces a
partial consultation when Claude succeeds, not a fallback runtime.

## What it enforces

- **One question, two conversations.** Neither adviser sees the other's answer.
- **No silent model substitution.** Requested models must be available.
- **Independent results.** One failure does not discard the other answer.
- **Advice stays advice.** Only the calling task can act within its authority.

## How it works

Codex prepares one consultation body, starts a fresh SOL subagent, then
starts Claude without waiting for SOL. It collects both answers and presents
them separately before comparing agreement, disagreement, and useful checks.
The Python adapter owns Claude transport. The host owns paired orchestration.

### Configuration

For personal defaults, copy [config.default.json](ask-claude-and-sol-for-codex/config.default.json)
to `config.json` beside it. The personal file is ignored by Git and overrides
the shipped defaults. Model, effort, budget, persistence, and Claude
customizations remain separate settings. `claude.command` accepts a command on
`PATH` or an absolute executable path.

For a one-off override, put the choice in the request. An unavailable Codex
model is reported rather than silently replaced.

### Follow-ups

The first consultation retains Claude's session ID and SOL's agent target.
A paired follow-up resumes both. A provider-specific follow-up contacts only
that adviser. Missing handles leave the surviving result explicitly partial.
The host's follow-up control must wake an idle subagent, not merely send it a
passive message.

The SOL target is valid within the current Codex task. Spawning another
agent or opening another task starts a fresh consultation, not a continuation.

### Optional Claude deadline

The optional `--timeout-seconds <positive-number>` applies to one Claude call
and is disabled by default. Expiry returns exit 124 without an automatic retry,
budget increase, or success answer. A known resume ID survives the error, but an
interrupted turn is not guaranteed to be saved.

It terminates and waits for the direct child, not a whole process tree or remote
job. Startup and inherited pipes can delay return. Synthetic direct-child tests
passed on Windows and WSL Ubuntu. Live provider cancellation was not tested.

Repository structure and contributor detail are in the
[maintenance notes](docs/maintenance.md).

## Failure behavior

- **Complete:** Claude and SOL both returned answers.
- **Partial:** one provider returned an answer while the other failed or was
  unavailable.
- **Failed:** neither provider returned an answer.

Missing subagent support never triggers a Codex CLI fallback. A Claude failure
never discards a successful SOL result. Agreement is still not proof. The
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

## Status

Deterministic tests cover Claude transport, configuration, UTF-8, session
routing, unusable answers, and synthetic deadlines. These tests do not prove
host-native SOL orchestration.

The published v2.0.1 record retains a successful paired acceptance run. No new
SOL model run was performed for the current local adapter changes. Complete
host acceptance still needs partial failures in both directions,
provider-specific follow-ups, attribution, and repository preservation.

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

MIT. See [LICENSE](LICENSE).
