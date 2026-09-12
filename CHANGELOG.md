# Changelog

## v3.0.3 - 2026-09-11

- Resolve task and model authority from the actual user request and host rules. Reuse existing authorization and preserve an independently authorized Claude consultation when the SOL lane is unavailable.

## v3.0.1 - 2026-09-10

- Deliver the SOL opinion directly to the verified calling task instead of
  replaying conversation logs.
- Keep the same destination for follow-ups and report missing delivery instead
  of treating silence as a complete answer.

## v3.0.0 - 2026-09-09

- Run SOL in a fresh normal Codex Desktop project task, preserve the result
  before archiving, and reuse its task ID for explicit follow-ups.
- This is a breaking host change. Codex CLI alone and hosts without normal
  project-task controls are no longer supported.

## v2.1.0 - 2026-09-05

- Added an optional Claude timeout. Expiry returns exit 124 without retrying or
  raising the budget.

## v2.0.1 - 2026-09-01

- Changed the default Claude model from Fable 5 to Fable 5.1 while keeping
  `high` effort and the SOL `xhigh` default.

## v2.0.0 - 2026-08-24

- Replaced the second Codex CLI process with a fresh host-native SOL task.
- Kept Claude in the read-only adapter while the calling Codex now owns paired
  dispatch, attribution, partial failures, and follow-up routing.
- SOL follow-ups now use a retained task ID. They are not portable Codex CLI
  session IDs.
- Hosts without usable project tasks return a partial Claude result instead of
  switching to another SOL runtime.

## v1.0.1 - 2026-08-20

- Raised the default SOL reasoning effort from `high` to `xhigh` while keeping
  per-call and personal configuration overrides.

## v1.0.0 - 2026-08-19

- Added parallel Claude and SOL consultations with independent settings,
  attributed answers, provider-specific follow-ups, and explicit complete,
  partial, or failed outcomes.
- Added persistent SOL conversations and kept Claude on a fixed read-only tool
  surface.
- Required Python 3.9 or newer for the wrapper.
