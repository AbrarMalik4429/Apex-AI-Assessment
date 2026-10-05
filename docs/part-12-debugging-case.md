# Part 12 — Debugging Case

**Reported bug:** The assistant says “Your appointment has been rescheduled,” but the downstream tool timed out.

The immediate problem is an unsupported success claim. A timeout means the caller did not receive a result in time; it does not prove that the appointment change failed. The downstream system might have committed the change and lost the response. I would first prevent further misleading confirmations, then determine the actual booking state before retrying a mutation.

## 1. Reproduce safely

Use a disposable database, synthetic patient, an owned confirmed appointment outside the notice boundary and an available replacement. Complete the normal proposal/confirmation flow. Record the request ID, original booking ID and intended replacement details without logging credentials or unnecessary patient information.

Inject each failure separately:

| Failure point | Expected database outcome | Correct user-facing outcome |
|---|---|---|
| Before the tool starts a transaction | Original unchanged. | No success claim; definite failure only if non-execution is established. |
| During the replacement transaction, followed by rollback | Original unchanged; no replacement committed. | No success claim; safe failure or conservative unknown response. |
| After commit but before the result reaches the caller | Original rescheduled; replacement committed. | Outcome unknown until reconciled; do not claim definite failure. |
| After the API commits but the browser loses its response | Saved operation and replacement exist. | Browser retries the identical request rather than starting another change. |

Use a controlled exception or transport stub for repeatability; avoid relying only on sleep timing. Capture both the API result and the rendered chat message. If the UI displays success before the API has returned it, reproduce that independently of the model.

## 2. Diagnose the source of the false claim

Trace the same request through interpretation, confirmation, tool invocation, transaction completion, response construction and UI display. Check:

- Did the model generate success text without a verified tool result?
- Did the application construct a success response and send it before commit?
- Did exception handling return an old success value or swallow the timeout?
- Did the frontend show an optimistic success message or associate a stale response with a newer request?
- Was the change committed despite the timeout? Inspect the original status, replacement link, replacement row and stored operation response.
- Did a retry use a new request ID and execute a second mutation?

Do not infer the outcome from the assistant's wording. Database state and, for a remote tool, an authoritative operation-status lookup provide the evidence. The exact fault location remains a hypothesis until the trace reproduces it.

## 3. Fix the result contract and recovery path

The required invariant is: **show reschedule success only after an authoritative completed result confirms the change.** User consent, model intent and a submitted tool call are not completion evidence.

Keep explicit outcomes: succeeded, rejected/known failed, and unknown. A timeout with uncertain completion maps to unknown. An appropriate message is:

> I could not verify whether your appointment was rescheduled. Please retry this same request before making another change.

Never replace that with “No change was made” unless rollback or non-execution has been established. Do not automatically cancel the old appointment or create another replacement to compensate for uncertainty.

### Current take-home implementation

The downstream booking layer is Python/SQLAlchemy and PostgreSQL, not a separately deployed remote scheduling tool:

- [Workflow.confirm()](../app/workflow.py) executes the stored proposal through the booking service; it does not ask Groq to report mutation success.
- [BookingService.reschedule()](../app/booking_service.py) updates the old record and inserts its linked replacement inside the enclosing transaction.
- [execute_message()](../app/main.py) saves the operation response and commits before returning success. A database error whose outcome cannot be verified returns HTTP 503, `status: outcome_unknown`, `data.code: database_outcome_unknown`.
- An identical retry, using the same session, request ID, message and token, returns the saved result if the first transaction committed. Different input under an existing request ID is rejected.

These mechanisms already address important forms of this scenario. This document does not claim that the reported bug was observed and fixed in the current app, nor that every timeout path has been tested.

### If a remote scheduling tool is introduced

Give the downstream operation a stable idempotency key and persist its correlation/status. After a timeout, query its authoritative result before deciding whether to retry. A local database rollback cannot undo a remote commit. If the tool supports neither idempotency nor status lookup, keep the outcome unresolved and route reconciliation to staff through a real implemented process; do not blindly repeat the write or pretend a handoff occurred.

The frontend must display the backend's verified status and preserve the identical retry payload for unknown outcomes. Any new status/protocol would need end-to-end tests. Concurrent duplicate requests require additional database coordination; sequential replay alone is not a complete race-condition fix.

## 4. Test the fix

| Test | Pass criterion |
|---|---|
| Normal confirmed reschedule | Exactly one linked replacement, correct original status and success only after commit. |
| Failure during write | Original remains confirmed; no committed replacement; no success text. |
| Commit succeeds, acknowledgement lost | First response is unknown; identical retry returns saved success; exactly one replacement exists. |
| Browser response loss | UI preserves the request and does not invent success; retry displays the saved result. |
| Provider interpretation timeout | No booking action starts; safe provider error. This is distinct from a timeout after mutation. |
| Unknown outcome followed by changed retry payload | Conflict/rejection rather than a second action under the same identity. |
| Two concurrent confirmations | No duplicate/lost update; requires the planned concurrency implementation and PostgreSQL tests. |

Existing [transaction tests](../tests/test_transactions.py) exercise reschedule rollback and lost-commit-acknowledgement replay. The lost-acknowledgement test currently uses a new booking, so the reschedule-specific variant above remains an additional test to write. [Booking tests](../tests/test_booking.py) cover normal rescheduling, stale availability, confirmation and provider failure. See [Part 7](part-7-automated-tests.md) for the latest recorded 119-test run and its limitations.

I would close the incident only after reproducing the false success, verifying the relevant fix at the API and UI, reconciling any affected appointment, and recording regression evidence. This submission adds the debugging plan, not a new remote tool or a claim of production incident resolution.
