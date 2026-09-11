# F05 acceptance deferred

2026-09-11: authorization wording updated; acceptance deferred by the user.
Activation is not task-creation or named-model authority. Existing authorization
is reused, with independently authorized Claude work preserved. SOL stays SOL.

Pending cases:
- Implicit activation alone creates no normal task.
- Task creation authorized but named model not requested follows the host rule.
- Fully authorized review/default prompt and follow-up do not ask twice.
- Unavailable SOL controls produce a truthful partial result only when Claude
  is independently authorized; no extra reviewer or substitute model is used.

No tests, consultations or model probes have run. Inspect
tests/test_project_task_contract.py when resuming; its text markers are not
behavioral proof. test_answer_contract.py tests the Claude adapter, not SOL
message transport. F07 length/protocol changes remain deferred. Record actual
loaded package/model metadata and observed outcomes only after user-requested checks.
