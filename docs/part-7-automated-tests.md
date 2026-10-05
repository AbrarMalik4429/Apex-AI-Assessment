# Part 7 — Automated Tests

## Scope and recorded result

The submission includes automated tests for deterministic booking functions, API validation, knowledge safeguards and failure recovery. Seven additional parametrized cases were added in [test_notice_policy.py](../tests/test_notice_policy.py).

**Verification on 6 October 2026: 119 backend tests passed.** Ruff passed for the added test file. This run used temporary SQLite databases and controlled model outputs; no live patient database or Groq calls were used. One existing Starlette/httpx TestClient deprecation warning was reported. These results do not establish production PostgreSQL concurrency safety or live-model intent accuracy.

## Core-function and failure-path coverage

| Area | Behaviour checked | Tests |
|---|---|---|
| Booking and confirmation | No write before confirmation; valid confirmation persists the appointment; missing tokens cannot authorize a write. | [test_booking.py](../tests/test_booking.py) |
| Availability | Occupancy, leave and patient overlaps across doctors remove affected options; adjacent slots remain eligible; stale choices are rechecked. | [test_booking.py](../tests/test_booking.py) |
| Appointment lists | Active records are filtered by status and ownership. | [test_appointment_listing.py](../tests/test_appointment_listing.py) |
| Rescheduling/cancellation | Correct status and replacement linkage, cancellation success, already-cancelled handling, and preservation of the original on failure. | [test_booking.py](../tests/test_booking.py), [test_workflow_edges.py](../tests/test_workflow_edges.py) |
| Policy boundaries | Cancellation/rescheduling notice thresholds, no fabricated escalation and execution-time rechecks. | [test_booking.py](../tests/test_booking.py), [test_notice_policy.py](../tests/test_notice_policy.py) |
| Invalid identity/input | Reject cross-patient changes, client-supplied patient identity, invalid dates/options and expired sessions or tokens. | [test_booking.py](../tests/test_booking.py), [test_workflow_edges.py](../tests/test_workflow_edges.py) |
| Date interpretation | Backend calendar offsets and conversational date refinements. | [test_date_windows.py](../tests/test_date_windows.py), [test_date_refinements.py](../tests/test_date_refinements.py) |
| Database constraints | Duplicate confirmed slot/date rejection and safe conflict responses. | [test_slot_identity.py](../tests/test_slot_identity.py) |
| Transaction failure/replay | Reschedule rollback; recovery after a lost commit acknowledgement using the identical request. | [test_transactions.py](../tests/test_transactions.py) |
| Provider failures | Safe handling of provider errors and invalid structured output. | [test_groq.py](../tests/test_groq.py), [test_booking.py](../tests/test_booking.py) |
| Knowledge/injection | Evidence allowlists, rejected extra fields, missing-evidence fallbacks, poisoned-source exclusion, injection rejection and fact-specific qualifications. | [test_knowledge.py](../tests/test_knowledge.py) |

Tests inspect database effects and machine-readable outcomes, not just response wording. Controlled model outputs exercise downstream enforcement independently of whether a live model interprets a prompt correctly.

## Meaningful tests added for this requirement

### Rescheduling uses the original start time — three cases

`test_reschedule_notice_uses_original_start` requests a replacement several days later and varies the original appointment's remaining notice:

| Notice | Required outcome |
|---|---|
| 23h 59m 59s | `requires_approval` / `notice_policy`; original remains confirmed; no replacement inserted. |
| Exactly 24h | Same rejection: the boundary is inclusive. |
| 24h and 1s | Replacement is confirmed; original becomes rescheduled and links to the replacement. |

This detects an incorrect comparison against the replacement date, an off-by-one boundary and unintended writes on rejection.

### Valid confirmation cannot bypass a newly reached boundary — two cases

`test_confirmation_rechecks_notice_after_clock_crosses_boundary` exercises both cancellation and rescheduling through the API. It obtains a proposal at 24h 2m before the original start, advances the test clock three minutes, then confirms with the still-valid token.

Both cases must return `requires_approval` and `notice_policy`, no confirmation token and an honest statement that no approval request was submitted. Persisted records must show the unchanged confirmed original, no replacement link and no inserted booking. The test also verifies that confirmation does not call the model again.

### Separate policy settings — two cases

`test_cancellation_and_rescheduling_have_independent_thresholds` uses an appointment 30 hours away with one threshold set to 48 hours and the other to 24, then reverses those settings. Only the action requiring 48 hours must be blocked. This detects accidentally applying one action's configuration to both.

## Running the tests

From the backend root with its Python environment activated and development requirements installed:

```powershell
python -m pytest -q
python -m pytest tests/test_notice_policy.py -q
python -m ruff check tests/test_notice_policy.py
```

Without `TEST_DATABASE_URL`, the harness uses isolated temporary SQLite databases, synthetic fixtures and a controlled clock. PostgreSQL verification requires a dedicated test database through `TEST_DATABASE_URL`; the harness creates and drops temporary test schemas and needs suitable permissions. Do not use production credentials. See the [README](../README.md) and [verification record](verification.md).

## Highest-risk behaviour not covered in the 48-hour submission: race conditions

**Concurrent requests can each validate stale state and then perform conflicting writes. This is the highest-risk gap.** Current tests cover sequential replay, injected transaction failures, stale choices and slot/date uniqueness. They do not establish full correctness under simultaneous PostgreSQL transactions across connections, API workers or server instances.

### Example: one patient, overlapping slots with different doctors

1. Request A checks the patient's appointments and sees no overlap.
2. Before A commits, request B checks and also sees no overlap.
3. The requests use different slot IDs, so the unique `(slot_id, appointment_date)` constraint does not reject the pair.
4. Without additional coordination, both could commit, leaving the patient double-booked.

Other unproven cases include simultaneous cancellation/rescheduling of one booking, concurrent conversation updates, identical request IDs arriving together, and future doctor-side edits racing with booking. Atomicity protects one transaction's changes; it does not serialize every business decision. One API worker is not a general fix.

### Existing partial protections

- Availability revalidation before mutation.
- Database uniqueness for confirmed slot/date combinations.
- Transactional rescheduling and rollback.
- Stored responses for sequential replay and lost-acknowledgement recovery.

These should not be described as a complete mutex or comprehensive race-condition solution. SQLite regression success also does not prove PostgreSQL locking behaviour.

### Next-version implementation and tests

Add database-backed coordination shared across workers for patient timelines, affected bookings, workflow state and atomic request claims. Revalidate inside the protected transaction, retain constraints, acquire locks consistently and avoid holding locks during external model calls.

Then test with independent PostgreSQL connections and synchronization barriers that deliberately overlap transactions. Include competing claims to one slot, different overlapping slots for one patient, simultaneous cancel/reschedule, duplicate request replay, lock timeout/deadlock recovery and rollback. Repeat across workers and inspect committed database state. Add doctor-edit races when that workflow exists.

**No locking fix or parallel-request safety claim is added by this test change.** OTP login and doctor-side workflows remain next-version features and have no implemented-feature test coverage yet. Live-model robustness, source correctness and production load/recovery require separate evaluation.

Related: [Part 6 evaluation plan](part-6-evaluation.md), [Part 10 production architecture](part-10-production-architecture.md), [Part 11 workflow vs agent](part-11-workflow-vs-agent.md).
