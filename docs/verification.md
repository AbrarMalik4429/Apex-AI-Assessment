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
