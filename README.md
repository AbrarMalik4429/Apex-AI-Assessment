# What Works, What Does Not, What I Would Build Next

This is the booking portion of the Apex patient-service assessment: a Python REST backend using Supabase PostgreSQL and Groq for intent extraction. It follows the agreed booking workflow and assumes doctor-side schedules are correct.

**Works:** authenticated demo sessions; doctor search by name/specialty or previously seen doctor; patient-aware availability; database-enforced confirmed slot/date uniqueness; booking, lookup, cancellation, rescheduling and existing follow-up scheduling; clarification and numbered options; explicit confirmation; durable sequential request replay; structured Groq output with local validation; bounded provider retries; database error handling; atomic rescheduling; migrations, seed data, Docker configuration and automated tests.

**Not included:** preparation, insurance/general questions, RAG, human escalation delivery, OTP or production authentication, doctor-side schedule editing, symptom-to-specialty inference, variable appointment durations, comprehensive concurrency safety, multi-branch scheduling, and one-off extra slots. The demo endpoint intentionally grants access to one synthetic patient and must stay disabled outside a local synthetic demo. Natural-language quality is not measured by the mocked tests.

**Live database verified:** Apex AI Arabia is provisioned, seeded and connected through Supabase's session pooler with certificate and hostname verification. Nine API/database smoke checks passed against PostgreSQL, with all test writes rolled back. The dedicated runtime login and local `.env` are configured on this machine. Groq is configured locally and a live conversation smoke check passed; Docker execution remains unverified. See `docs/supabase-setup.md` for the current project setup.

**Build next:** database locking/overlap constraints and concurrent-request tests; verified patient identity; deployment hardening and per-patient database authorization if needed; real-model evaluations with consented synthetic cases; broader multilingual/date ambiguity evaluations; coordinated doctor-side schedule changes; operation retention and monitoring; the remaining assessment families. A process-local mutex alone would not protect multiple backend workers.

## Chatbot demo

Open http://127.0.0.1:8000/ after starting the server. All patient interactions happen in the conversation: booking, availability, appointment lookup, rescheduling, cancellation and existing follow-ups. Doctor/time choices, appointment cards and explicit confirmation buttons appear inline. You can also type replies such as `Option 1`, `yes`, or a new date. The page uses `/assistant/message` for every conversation action; the earlier guided endpoint remains available for API compatibility.

The Groq key is configured locally and a real-provider, rollback-isolated smoke test passed all six booking families. A fresh installation still needs its own key. Groq interprets natural language; Python enforces ownership, availability and booking policies. Exact numbered choices, reset and confirmation do not need model calls. Preparation, insurance/general knowledge and escalation delivery remain out of scope.

The transcript and pending request are kept in sessionStorage for the browser tab. On an uncertain response, the chat blocks new actions and offers a retry with the identical request ID and payload, including after a reload. A expired session requires reconnection and checking existing appointments before repeating an uncertain change. No provider keys or database credentials are sent to the browser.

No frontend build step is required; FastAPI serves `app/static`. Google Fonts is optional; system fonts are used if unavailable. This is a synthetic demo, not production patient authentication.

## Already configured on this machine

The existing local `.env` contains the verified Supabase connection and generated backend credential. Do not overwrite it with `.env.example`. Your Groq key is now configured locally. Run the API from this folder:

```powershell
& '..\..\work\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The database migrations and synthetic seed have already been applied. The runtime login intentionally cannot apply future migrations or write doctor-side seed data. Use the connected Supabase migration tools or a separate administrator connection for those operations. The ZIP excludes `.env` and all credentials.

## Quick start on Windows

Install Python 3.12+ and either use a Supabase PostgreSQL database or start the local PostgreSQL container described below. Open a terminal in this folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Edit the local `.env`:

- Set `GROQ_API_KEY` to your existing Groq key. Do not paste it into chat, commit it, or put it in a browser client. `.env` is excluded from Git and Docker builds.
- Set `DATABASE_URL` to your Supabase direct or session-pooler connection, using the `postgresql+psycopg://` driver and TLS. URL-encode special characters in the database password. Copy connection details from your project's Connect panel; do not guess its hostname.
- For the local synthetic demo only, set `DEMO_ENABLED=true`.
- Leave `GROQ_MODEL=openai/gpt-oss-20b` and `GROQ_RESPONSE_MODE=strict` initially. This is a Groq-hosted model; no OpenAI API key or OpenAI endpoint is used.

For a new database, use an administrator connection to apply migrations and load synthetic fixtures before switching to your runtime connection. These steps are already complete for Apex AI Arabia:

```powershell
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [Swagger API documentation](http://127.0.0.1:8000/docs). In another activated terminal:

```powershell
python scripts/demo_client.py
```

Try: `Book Dr. Amal after two months`, `Book Dr. Amal between 2026-11-02 and 2026-11-13`, or `Book Dr. Amal tomorrow afternoon`, choose a numbered time, then type `confirm`. The client attaches the returned confirmation token. Type `retry` after an uncertain response; it reuses the identical request ID and payload. `reset` clears the pending workflow. It never prints your API key or session token.

## Supabase database setup

The Alembic migration creates a private `booking` schema. Keep it out of Supabase's exposed Data API schemas. It revokes schema access from PUBLIC and enables RLS on domain/session/operation tables without public policies. The browser interacts only with FastAPI.

The configured Supabase project uses separate access: migrations run through the administrator connector, while Python uses `booking_runtime`. This role cannot bypass RLS, delete records, manage roles/schemas or modify doctor-side schedules. Role-specific policies permit only the approved backend operations. Those policies trust the backend across its patients; per-patient ownership is enforced in Python and tested. No policies grant access to `anon` or `authenticated`.

The working connection uses the Supabase session pooler, `sslmode=verify-full`, and the public CA certificate in `certs/supabase-ca.crt`. `DATABASE_SSL_ROOT_CERT` selects that certificate; if omitted, the application uses certifi's public trust bundle. An explicit `sslrootcert` URL parameter takes precedence. Transaction-mode pooling remains unverified. Never commit the database connection string.

The migration does not create a Supabase project or alter existing patient records. Seed only a dedicated synthetic demo database. The seed is idempotent when its demo patient already exists.

## Local PostgreSQL and Docker

To use local PostgreSQL while running Python on your host:

```powershell
docker compose up -d db
```

The local credentials in `.env.example` match this container. To run the API in Docker too, create `.env`, add the Groq key, and enable the synthetic demo first:

```powershell
docker compose build api
docker compose run --rm api python -m alembic upgrade head
docker compose run --rm api python -m app.seed
docker compose up -d api
```

Compose deliberately overrides the database URL to use its local `db` service. For Supabase, run Python on the host, or run the built API image with your Supabase `.env` outside this local Compose configuration. The Dockerfile does not bake in secrets. One worker is configured for the demo; even one worker does not eliminate concurrent-request races.

## Tests

```powershell
python -m pip install -r requirements-dev.lock
python -m pytest -q
python -m ruff check .
```

For actual PostgreSQL verification, set `TEST_DATABASE_URL` locally to a **test** database connection before running the same suite. The suite creates and drops `booking_test_<random>` schemas, applies the frozen SQL migration, and seeds synthetic data. It does not touch the application's `booking` schema. The supplied role needs schema creation permissions. Do not point tests at production.

The tests cover ownership, filtering across doctors, partial leave, adjacent slots, clarification, confirmation, follow-ups, policy boundaries, stale choices, atomic rollback, replay after a lost commit acknowledgement, and Groq errors. They do not establish real-model intent accuracy, network performance, production authentication or race safety. See `docs/verification.md` for the actual checks performed on this build and `docs/evaluations.md` for expected behaviours.

## Groq behaviour and troubleshooting

Only the user's current message and compact scheduling context are sent to Groq. The backend does not send stored names, phone numbers, patient IDs, booking notes, session tokens or database credentials. User-entered text may itself contain personal information; use synthetic data for the assessment. No raw request or provider response logging is implemented.

| Error code | Meaning and next step |
|---|---|
| `groq_not_configured` | Add the key locally and restart the backend. |
| `groq_authentication_failed` | Check the key and account access in Groq Console; no automatic retry. |
| `groq_rate_limited` | Respect the returned Retry-After header. Retry the same request later. Account limits vary. |
| `groq_request_rejected` | Check model availability and structured-output support. No silent switch to weaker output mode. |
| `groq_invalid_output` | JSON/schema or completion validation failed. No booking tool ran. |
| `groq_timeout` / `groq_unreachable` | No interpreted action was executed; retry later. |
| `database_outcome_unknown` | The write may have committed. Retry identical input with the same request ID before starting another change. |

Strict JSON schema is the default. If deliberately using a different Groq model that supports only JSON object mode, set `GROQ_RESPONSE_MODE=json`; local Pydantic validation still rejects unexpected fields/types. Do not expect schema validation to guarantee semantic correctness. All writes require a server-stored proposal and explicit confirmation token.

The client makes at most two attempts for 429/5xx responses, with a short bounded delay. A longer Retry-After is returned immediately. Timeouts, invalid JSON and authentication errors are not automatically retried. No provider tools, streaming or autonomous tool loop are used. Confirming a proposal makes **no LLM call**.

## Design and implementation documents

- `docs/database.md`: relationships, constraints, trust boundaries and assumptions.
- `docs/api-workflow.md`: endpoint contracts, confirmation flow and state transitions.
- `docs/openapi.json`: generated API schema; `/docs` serves the running version.
- `docs/evaluations.md`: cases, expected behaviour and pass/fail criteria.
- `docs/verification.md`: verification evidence and remaining gaps.
- `docs/booking-workflow.md`: agreed source workflow, retained as a design reference.

## Assumptions and disclosure

Slots are complete, valid, non-overlapping doctor-side appointment templates. Each booking uses exactly one slot; appointment type is descriptive and does not change its duration. Templates are same-day intervals in the configured clinic timezone (`Asia/Riyadh` by default). Monday is weekday 0. All patient-specific data access derives identity from the server-issued session.

Cancellation at or below 24 hours requires approval; no appointment mutation or escalation submission occurs. The same default applies to rescheduling as an explicit assumption from the workflow notes and can be changed independently through `RESCHEDULE_NOTICE_HOURS`. Past appointments cannot be changed. Unscheduled follow-ups are scheduled in place and keep their original clinical parent reference. Rescheduling preserves the old row and adds a replacement pointer; child links to the original visit remain historical links.

This was built with Codex assistance for design, coding, documentation and test creation. Provider behaviour was checked against official Groq documentation. Automated checks validate the implemented code paths; the candidate should review, run against their own test services, and be able to explain the design before submission. This booking-only deliverable is not the complete assessment submission.

Sources checked on 2026-09-28: [Groq structured outputs](https://console.groq.com/docs/structured-outputs), [Groq rate limits](https://console.groq.com/docs/rate-limits), [Groq API reference](https://console.groq.com/docs/api-reference), [Supabase connection options](https://supabase.com/docs/guides/database/connecting-to-postgres), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).
