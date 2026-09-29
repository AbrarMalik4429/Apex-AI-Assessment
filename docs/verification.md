# Verification record

Verified locally on 2026-09-28 using Python 3.12.14 on Windows.

| Check | Result |
|---|---|
| `python -m pytest -q` | 42 passed. Business and API tests used SQLite with foreign keys enabled. Groq tests used HTTP mock transport. |
| `python -m ruff check .` | Passed. |
| `python -m compileall -q app migrations scripts tests` | Passed. |
| `python -m alembic upgrade head --sql` | Passed; schema and index revisions also applied to Apex AI Arabia through Supabase migrations, with the Alembic version synchronized. |
| OpenAPI generation | Generated `docs/openapi.json` from the FastAPI app. |
| Dependency resolution | Runtime and development requirements resolved into cross-platform lock files. |
| TLS-verified Supabase connection | Passed using the dedicated runtime role and session pooler. |
| `python -m scripts.check_database` | Passed: 2 doctors, 84 slots; no schedule insert privilege, no booking delete privilege, no RLS bypass. |
| `python -m scripts.smoke_database` | Eight live PostgreSQL/API checks passed: session, availability, booking, replay, rescheduling, cancellation, follow-up and cross-doctor patient filtering. All test writes rolled back. Groq was mocked. |
| Supabase security advisors | No findings after runtime policies were applied. |

The test runner emitted a Starlette deprecation warning recommending `httpx2` for future TestClient compatibility. The pinned current test suite succeeds with HTTPX; this is not a Groq API failure.

## Important evidence

- Filtering removes overlapping appointments across different doctors and retains adjacent times.
- A stale proposed slot is rechecked before booking.
- A forged booking ID cannot cross the session patient's ownership boundary.
- Exactly 24 hours requires approval; 24 hours plus one second permits cancellation.
- A rescheduling write error rolls back the inserted replacement and preserves the original booking.
- A simulated successful commit followed by a lost acknowledgement produces `outcome_unknown`; identical retry returns the stored success without another booking.
- Scheduling a follow-up keeps its original booking ID and parent relationship.
- Expired sessions, expired confirmations, old confirmation tokens and extra request fields are rejected.
- Groq credentials are sent only to the fixed HTTPS endpoint. Authentication errors are not retried; short transient errors get bounded retries; long Retry-After values return immediately.
- Invalid schemas, extra patient fields and truncated model output are rejected before any booking action.

## Not verified

No live Groq request, real-model accuracy evaluation, Docker build or container startup was performed. The Groq key is still unconfigured. Supabase provisioning, a direct Python-to-pooler connection and the rollback-isolated API checks were completed successfully.

The full unit suite still uses SQLite and mocked provider responses. The separate live PostgreSQL smoke suite complements it rather than replacing it. The full suite also supports `TEST_DATABASE_URL` using an administrator-owned disposable test database/schema; the restricted runtime role deliberately cannot create those schemas. Run a synthetic end-to-end message through your configured Groq account to verify model access and strict-output support.

Concurrency safety and production authentication are explicitly outside this build. Passing sequential SQLite tests does not establish those guarantees.

The final performance-advisor pass contained only [unused-index informational notices](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index). The three missing foreign-key indexes were resolved. A final query confirmed zero smoke-test sessions/operations and the original completed visit plus pending follow-up were intact.

## Slot identity and uniqueness update — 2026-09-29

Added migration `603768ba3dac`, the `bookings.slot_id` foreign key, and a unique confirmed `(slot_id, appointment_date)` index. All 49 automated tests pass, including seven new regression tests for duplicate rejection, date reuse, cancellation reuse, required slot identity, follow-ups, API conflict handling and reschedule rollback. The earlier 42-test record above describes the initial checkpoint.

The updated live PostgreSQL smoke script passed all nine checks, including an actual duplicate insert rejected by `uq_bookings_confirmed_slot_date`. All smoke writes were rolled back. Supabase confirms migration `603768ba3dac`, no scheduled booking without a slot, and no security advisor findings. Ruff, compilation and offline Alembic SQL generation passed.

## Patient frontend — 2026-09-29

All 52 automated tests pass, including guided booking/replay, authorization, rescheduling, cancellation and follow-up flows without a model call. Playwright checked the live portal at desktop (1440px) and mobile (390px) widths, selected a time and opened the confirmation dialog. No JavaScript errors or horizontal mobile overflow were observed. The browser check did not confirm a live appointment.

## Chatbot and live Groq update — 2026-09-29

The root UI is now conversational. All 54 automated tests pass. A real Groq request verified authentication without exposing the credential. `python -m scripts.smoke_chat` passed natural-language availability, option selection and confirmation, appointment lookup, rescheduling, cancellation and follow-up scheduling against PostgreSQL; its database writes were rolled back. These are smoke checks, not a comprehensive model-quality evaluation.

Live browser checks exercised booking → doctor choice → time choice → inline confirmation, then abandoned the proposal without booking. Desktop/mobile views had no JavaScript errors or horizontal overflow. A separate browser test with synthetic network responses verified typed `yes` attaches the proposal token and a lost response can be retried with the identical payload after reloading the tab. This supersedes the earlier record that Groq was unconfigured/unverified. Docker remains unverified.

The live test found that model extraction could copy time fields when selecting an option. Exact numbered replies now resolve server-stored options without calling the model; a regression test covers that path and the availability-to-booking transition.

## Same-time reschedule restriction — 2026-09-30

The original slot/date is omitted from rescheduling options. Explicit requests for the same slot/date return `same_appointment_time` before confirmation and are rejected again by the booking service before writing. The same recurring slot on another date remains valid. All 56 automated tests pass. Cancelled and rescheduled records do not block availability; their former times are shown only if current template, future-time, leave and confirmed-booking checks pass.

## Weekday schedule and date-range update — 2026-09-30

All 64 automated tests pass. New coverage checks 80 templates (eight per weekday per doctor), exact date/weekday/time matching, no weekend options, calendar month-end/leap-year calculations, range conflict filtering, preserved option selection and persistence of the displayed date/time on confirmation.

Live Supabase verification confirms eight templates for each weekday 0–4 for both doctors. `python -m scripts.smoke_date_windows` passed real Groq/PostgreSQL requests: October 7 (8 options), October 7–20 (20 sampled options), and 'after two months' resolved from September 30 to November 30–December 13 (20 sampled options). Confirming a selected option preserved its slot, date and start/end times. All smoke-test database writes were rolled back.
