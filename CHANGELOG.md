# Changelog

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
