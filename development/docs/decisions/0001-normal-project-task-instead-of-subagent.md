---
format_version: 1
id: ADR-0001
status: accepted
created: 2026-09-09
accepted: 2026-09-09
scope: orchestration/codex
---

# Use a normal project task instead of a subagent

## Decision

The SOL consultation runs in a fresh normal Codex task in the current saved project. The caller preserves its result, archives the task, and temporarily unarchives the same task only for an explicit follow-up. No Codex subagent is used.

## Problem

The tested Codex Desktop surface exposes normal task creation and archival but no reliable control to close a completed subagent and free its slot.

## Drivers

Fresh independent context, parallel Claude dispatch, bounded lifecycle, retained follow-up context and no leaked subagent capacity.

## Considered alternatives

Keeping the subagent would retain the slot problem. Running SOL in the caller would lose independence. A second Codex CLI would add another transport and authentication boundary.

## Consequences

Skill activation authorizes one temporary project task and archival. Hosts missing exact project resolution or create, wait, message, read or archive controls return a partial result instead of substituting another runtime.

## Confirmation

Instruction tests check normal-task creation, read-only scope, task-ID retention and archival. They do not prove a live paired run.

## Revisit when

The host removes normal project-task orchestration or exposes a reliably closable fresh-context mechanism with equivalent continuation.
