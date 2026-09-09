---
format_version: 1
id: PLAN-0003
status: completed
created: 2026-09-09
updated: 2026-09-09
---

# Move SOL consultation to a normal project task

## Goal

Preserve the independent parallel SOL consultation without consuming a non-closable Codex subagent slot.

## Non-goals

- Do not change Claude transport, default models, public release state or installed Skills.

## Work items

### W-001 Replace the Codex subagent transport
Status: done
Depends on: []
Blocked by: []
Decisions: [ADR-0001]
Outcome: SOL runs in a temporary fresh normal task in the current project and that task is archived after durable result capture.
Acceptance: SKILL metadata and README describe exact-project normal-task creation, parallel collection, read-only scope, retained task-ID continuation, archival and honest unsupported-host behavior; adapter and contract tests plus validators pass.
Steps:
1. Update the installable package and public documentation.
2. Add deterministic lifecycle assertions and run repository validation.
3. Close this local-only Plan without installing, committing or publishing.
Evidence: ["Tests: 21 adapter and task-contract tests passed", "Validation: installable Skill and native Plan profile passed", "Scope: local-only; no install commit push or release performed"]
