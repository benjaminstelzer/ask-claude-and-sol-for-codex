# Changelog

## v3.0.0 - 2026-09-09

- Replace subagent dispatch with fresh normal Codex Desktop project tasks, preserving results before archiving and reusing task IDs for explicit follow-ups.
- This is a breaking host requirement. Codex CLI alone and hosts without normal project-task controls are not supported.
- The task-and-archive workflow has deterministic instruction coverage, not new live paired-consultation qualification.

- Document host and tool requirements in the README compatibility block, matching the Skill frontmatter.

- Added the `compatibility` frontmatter field declaring host and tool requirements. No behavior change.

## v2.1.1 - 2026-09-05

- Move repository development into `development/` and keep the installable Skill in its own top-level directory.
- Update current paths while retaining historical evidence and its path mapping.

## v2.1.0 - 2026-09-05

- Shortened the README, moved contributor layout notes to docs/maintenance.md, and made agent installation the primary path. Safety and evidence limits remain explicit.
- Added the optional --timeout-seconds Claude CLI setting, disabled by default. Expiry returns exit 124 without retry or budget escalation.
- Documented the standalone package and development-test layout and removed generated working caches.
- Documented direct-child cancellation limits without changing the host-owned SOL lane or saved configuration.
- Included the repository license in the copied package. All 20 tests passed on Windows and WSL Ubuntu without provider calls.

## 2026-09-01: Fable 5.1 default (v2.0.1)

### Changed

- Raised the Claude default from Fable 5 to Fable 5.1 while preserving `high`
  Claude effort and the independent GPT-5.6 SOL `xhigh` default.
- Updated the shipped configuration, Claude adapter fallback, Skill contract,
  README, and regression coverage to request `claude-fable-5-1` consistently.

### Validation

- The deterministic Claude-adapter tests and Agent Skill package validation
  passed.
- A host-level acceptance run dispatched a fresh SOL subagent and a live Claude
  consultation on Claude Code 2.1.257. Claude requested
  `claude-fable-5-1` with `high` effort and returned without permission denials;
  both advisers returned independently.

## 2026-08-24: Host-native SOL subagent (v2.0.0)

### Changed

- Replaced the second Codex CLI process with a fresh host-native SOL subagent.
  The Skill no longer installs, locates, authenticates, or invokes a Codex CLI.
- Moved paired dispatch, collection, attribution, partial-failure handling, and
  follow-up routing into `SKILL.md`, where the calling Codex can access the
  host's subagent controls.
- Reduced the Python wrapper to the Claude Code adapter and retained Claude's
  read-only tools, safe mode, configuration, JSON errors, and session resume.
- Reduced SOL configuration to model and effort. Removed its command, web-search,
  customization, CLI persistence, and runtime settings.

### Contract changes

- Fresh SOL context prevents parent turns from being copied, but the subagent
  inherits host-level instructions, tools, and permissions. Read-only SOL
  behavior is instructed rather than enforced by a separate sandbox.
- SOL follow-ups use an agent target within the current Codex task. They are not
  portable CLI session IDs and do not promise cross-task resume.
- The calling Codex now combines provider results; there is no paired wrapper
  JSON object, Codex CLI version, JSONL usage record, or completed-item list.
- Hosts without usable subagents return a partial Claude result instead of
  falling back to another Codex runtime.

### Validation

- Deterministic tests cover the Claude adapter and reject the removed SOL CLI
  configuration and runtime path.
- A host-level acceptance run dispatched a fresh SOL subagent before starting
  the Claude adapter. Both returned independently, and a later turn-triggering
  follow-up to the retained SOL target recalled its earlier task context.

## 2026-08-20: SOL xhigh default (v1.0.1)

### Changed

- Raised the default SOL reasoning effort from `high` to `xhigh` while keeping
  Fable at `high` and preserving explicit per-call and personal configuration
  overrides.
- Updated the shipped configuration, internal fallback, Skill contract, README,
  examples, and regression coverage together.

### Validation

- The official OpenAI model guidance lists `xhigh` as a supported GPT-5.6 SOL
  reasoning effort and keeps `max` available as the separate highest setting.
- Deterministic tests verify that shipped, fallback, parsed, and command-level
  SOL defaults all resolve to `xhigh`.
- A live call without an effort override requested `xhigh` and completed through
  Codex CLI `0.148.0`.

## 2026-08-19: Initial release (v1.0.0)

### Added

- Forked the proven Claude wrapper and expanded it into one parallel
  Claude-and-SOL consultation.
- Added independent Claude and SOL command, model, effort, persistence,
  customization, and web settings.
- Added persistent SOL sessions through `codex exec resume`, paired follow-ups
  with explicit session IDs, and provider-specific follow-ups.
- Added one combined result with attributed provider answers, metadata, errors,
  and `complete`, `partial`, or `failed` outcome states.
- Added a default SOL isolation profile with read-only sandboxing, approvals
  disabled, fixed role instructions, and local Codex customizations suppressed.
- Added deterministic Windows, macOS, and Linux CI coverage.

### Fixed

- Distinguished the calling Codex from the Codex CLI that runs SOL instead of
  switching between the undefined role name `Main` and `Codex`.
- Documented the Python 3.9 runtime floor and the Python 3.11 CI baseline.
- Qualified session persistence around IDs actually returned by each CLI.
- Aligned the documented result fields, `answer` or `error` behavior, model
  alias support, and PowerShell example location with the Skill contract.
- Removed a redundant platform summary while preserving the concrete
  Windows, macOS, and Linux test statement.

### Validation

- Deterministic tests cover real concurrent dispatch, both provider parsers,
  session routing, partial failure, isolation arguments, disallowed SOL item
  types, UTF-8 stream setup, and minimum Codex CLI version handling.
- The installable directory passes the canonical Agent Skill validator.
- The SOL isolation configuration was audited against Codex CLI 0.148.0 prompt
  input, followed by a live persistent-session probe and resume check.
- A live paired Fable 5 and SOL run returned two persistent session IDs; both
  IDs resumed successfully and retained the previous `PARALLEL_OK` answer.
- Independent Fable 5 and SOL audits agreed that the README was broadly
  consistent and voice-aligned, then identified the bounded precision fixes
  above.
- The official Codex CLI reference confirmed that `exec resume --last` remains
  scoped to the current working directory, so that documented behavior was not
  changed.
- PEP 585 confirmed the Python 3.9 floor required by the wrapper's runtime type
  alias.

### Provenance

- Based on Ask Claude for Codex v1.0.3. The inherited Git history preserves the
  original wrapper's implementation and validation record.
