# Development

The only installable package is [`ask-claude-and-sol-for-codex/`](../ask-claude-and-sol-for-codex/). Tests and maintenance material in this directory are not installed with the Skill.

## Validate

Run the deterministic adapter suite from the repository root:

```text
python -B -m unittest discover -s development/tests -v
```

Static tests do not prove live Claude or SOL availability, model quality, or complete host orchestration.

## Retention

Keep current tests and this maintenance summary. Put ad-hoc audits, live traces, transcripts, benchmark runs, and generated reviews in temporary storage. Retain evaluation evidence only as a concise repository-owned summary when a published release links it.
