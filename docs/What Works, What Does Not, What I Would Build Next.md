# What Works, What Does Not, What I Would Build Next.

## What works

- **Patient booking workflow:** The chatbot supports checking availability, selecting a doctor and dated slot, booking, viewing active appointments, rescheduling, cancelling and scheduling an existing pending follow-up. Appointment changes require a concrete proposal and explicit server-validated confirmation.
- **Backend validation:** Python checks session-bound ownership, allowed statuses, booking horizon, leave, occupied slots and patient overlaps across doctors. Rescheduling to the same slot/date is rejected. Active lists omit cancelled, completed and rescheduled-original appointments.
- **Persistence and history:** PostgreSQL stores bookings, session state and operation responses. Rescheduling preserves the original record and links its replacement. Cancellation retains the record. A database constraint prevents two confirmed bookings for the same slot/date; sequential request replay avoids repeating a completed operation.
- **Knowledge answers:** Local retrieval supplies candidate evidence; Groq selects allowed chunk IDs; Python renders the answer and citations. Missing evidence produces a fallback. Benefit-specific uncertainty, historical references and configured clinic policies receive the implemented qualifications.
- **Guardrails and failure handling:** Structured output validation, ownership checks, confirmation tokens, injection screening and safe error responses constrain the model. Cancellation at or within the configured notice boundary requires human approval without pretending a handoff occurred.
- **Frontend/backend separation:** The frontend has its own development/build commands and public environment configuration. The backend has separate private configuration. Vercel/Render deployment files and instructions are present.

The latest recorded verification checkpoint reports 112 backend tests and 3 frontend tests passing, plus frontend build, lint and an independent-origin browser smoke check. These are recorded prior checks, not new results from writing this summary. See [verification evidence](verification.md). The [Part 6 cases](part-6-evaluation.md) are evaluation specifications and must not be presented as 24 completed live-model passes.

## What does not work yet, or remains limited

- **Real patient login:** The current session flow uses a shared synthetic demo patient. OTP login and verified individual account-to-patient mapping are not implemented. Existing ownership checks do not turn this shared demo login into production authentication.
- **Full concurrency protection:** Slot/date uniqueness, revalidation, atomic transactions and sequential replay exist. Comprehensive locking across concurrent patient, booking, doctor-schedule and workflow updates does not. A single API worker does not remove all races.
- **Doctor-side management:** The service consumes doctor schedules and leave, but has no authenticated doctor portal or schedule-editing workflow. Correct, non-overlapping doctor templates remain an assumption.
- **Actual human escalation:** The system can say that approval is required, including cancellation at or within 24 hours under the default configuration. It does not create a staff ticket, contact a human or obtain approval.
- **Knowledge guarantees:** Supplied references can be incomplete or outdated, retrieval can miss relevant passages, and the model can choose an unsuitable allowed passage. A citation is not proof of current insurance entitlement. The system does not diagnose, prescribe or verify live insurance eligibility.
- **Production operations:** This submission does not demonstrate a production deployment, production identity verification, comprehensive concurrency/load testing, or a complete monitoring and incident-response setup. Arabic evaluation remains outside the current scope.

## What I would build next

### 1. OTP patient login and patient-only record access

Replace the shared demo login with a dedicated OTP authentication flow. Verify each session on the backend and map the trusted account identity to the correct patient through a controlled enrolment process. Patients would only be able to fetch and change their own records; knowing another patient's booking UUID would not grant access.

Keep OTPs out of chatbot messages and model context. Add expiry, attempt/resend limits, recovery and revocation handling. Disable demo access in production and test cross-patient access, identity tampering and account switching. Review database policies and pooled-connection identity handling alongside application authorization.

### 2. Mutex locking and race-condition fixes

Add database-backed coordination that works across API workers and instances. Serialize competing updates, recheck state inside the transaction, and make request replay safe under simultaneous submissions. Retain the existing unique slot/date constraint and atomic rescheduling behaviour.

Cover different overlapping slots for one patient, simultaneous changes to one booking, concurrent conversation updates and doctor schedule edits. Avoid holding locks while waiting for Groq. Verify the design with independent database connections and controlled concurrent tests before treating it as production-safe.

### 3. Doctor-side scheduling and management

Add authenticated doctor/staff workflows with explicit permissions for schedules, leave, appointment status and follow-ups. Validate weekly templates and exceptions rather than assuming they are always correct. Protect existing bookings when a schedule changes, retain audit history and coordinate edits with the booking transaction locks.

Doctors would have access appropriate to their assigned work; patient login would not grant staff privileges. This is a proposed addition, not a capability of the current frontend.

These three priorities are **next-version work to complete before real patient deployment**, not changes implemented with this documentation. Further release work includes tested backups, secret management, monitoring, knowledge review and a deliberate decision about implementing human escalation.

## Submission navigation

- [Part 10 — Production Architecture](part-10-production-architecture.md): target diagram and changes from the take-home.
- [Part 5 — Guardrails & Failure Handling](part-5-guardrails-and-failure-handling.md).
- [Part 6 — Evaluation](part-6-evaluation.md).
- [Preventing unsupported knowledge-base claims](preventing-unsupported-kb-claims.md).
- [Chatbot–Python–SQL communication](chatbot-python-sql-communication.md).
- [Deployment instructions](deployment.md).
