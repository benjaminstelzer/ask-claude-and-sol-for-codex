# Changelog

## 2026-08-19: Initial Claude and SOL release

### Added

- Forked the proven Claude wrapper and expanded it into one parallel
  Claude-and-SOL consultation.
- Added independent Claude and SOL command, model, effort, persistence,
  customization, and web settings.
- Added persistent SOL sessions through `codex exec resume`, paired follow-ups
  with two explicit session IDs, and provider-specific follow-ups.
- Added one combined result with attributed provider answers, metadata, errors,
  and `complete`, `partial`, or `failed` outcome states.
- Added a default SOL isolation profile with read-only sandboxing, approvals
  disabled, fixed role instructions, and local Codex customizations suppressed.
- Added deterministic Windows, macOS, and Linux CI coverage.

### Validation

- Deterministic tests cover real concurrent dispatch, both provider parsers,
  session routing, partial failure, isolation arguments, disallowed SOL item
  types, UTF-8 stream setup, and minimum Codex CLI version handling.
- The installable directory passes the canonical Agent Skill validator.
- The SOL isolation configuration was audited against Codex CLI 0.148.0 prompt
  input, followed by a live persistent-session probe and resume check.
- A live paired Fable 5 and SOL run returned two persistent session IDs; both
  IDs resumed successfully and retained the previous `PARALLEL_OK` answer.

### Provenance

- Based on Ask Claude for Codex v1.0.3. The inherited Git history preserves the
  original wrapper's implementation and validation record.
