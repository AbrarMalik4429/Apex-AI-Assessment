# What Works, What Does Not, What I Would Build Next.

**Works:** Python/FastAPI booking, availability, active appointment lookup, confirmed cancellation/rescheduling, pending follow-ups and source-cited knowledge answers. The independent frontend talks to the API; Python controls ownership, policies and database writes.

**Not production-ready:** shared synthetic demo login; no OTP, doctor-side management or submitted human escalation; incomplete concurrency protection. Docker files are provided, but container execution has not been verified on this machine.

**Next:** individual OTP login and patient-only records, database-backed race-condition fixes, then authenticated doctor-side workflows. See the [submission summary](<docs/What Works, What Does Not, What I Would Build Next.md>).

## Quick start

For this existing workspace, use the copy-and-paste [VS Code startup guide](START-IN-VSCODE.md).

Requires Python 3.12+, Node.js 22+ and a configured PostgreSQL database. Run commands from the repository root (the backend root). The frontend root is `frontend/`. Copy examples only if the real files do not already exist:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
```

Set backend `.env`: `DATABASE_URL`, `DATABASE_SSL_ROOT_CERT`, `GROQ_API_KEY`, `GROQ_API_URL`, `GROQ_MODEL`, `FRONTEND_URL`, `APP_HOST`, `APP_PORT`. Enable `DEMO_ENABLED=true` only for a restricted synthetic demo. Frontend `frontend/.env` needs `FRONTEND_API_BASE_URL`, `FRONTEND_HOST`, `FRONTEND_PORT`; the font URL is optional. Keep all credentials out of frontend settings and Git.

Use the existing provisioned database without reseeding. For a **new disposable database only**, run migrations and seed with a role permitted to create the schema:

```powershell
python -m alembic upgrade head
python -m app.seed
```

Start the API:

```powershell
python -m scripts.run_server
```

In a second terminal:

```powershell
cd frontend
npm.cmd ci --ignore-scripts
npm.cmd run dev
```

Open the address configured in `FRONTEND_URL` (example: `http://127.0.0.1:5173`). API docs are at `BACKEND_URL` plus `/docs`. Ports and origins must match across both environment files. Full variable tables, absolute paths and the existing workspace Python command are in [local development](docs/local-development.md).

## Docker: frontend and backend

Requires Docker Engine/Desktop with Compose v2 and Linux containers. With both environment files configured:

```powershell
docker compose --env-file .env --env-file frontend/.env config --quiet
docker compose --env-file .env --env-file frontend/.env up --build -d
docker compose --env-file .env --env-file frontend/.env ps
```

Compose uses the configured database; it does not create, seed or replace it. The frontend's API URL is browser-facing, not the internal container name. Backend and frontend publish to loopback by default. Stop with the same command prefix followed by `down`. Detailed setup, health checks and troubleshooting: [Part 8 — Docker & Code Quality](docs/part-8-docker-and-code-quality.md).

## Build, tests and hosting

```powershell
python -m pip install -r requirements-dev.lock
python -m pytest -q
python -m ruff check .
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run build
```

Frontend output: `frontend/dist/`. Python uses the locked dependency installation rather than a separate compilation step. Latest recorded backend result: **119 passed**; see [verification](docs/verification.md) for test scope and remaining gaps.

| Host | Root | Build | Start/output |
|---|---|---|---|
| Vercel frontend | `frontend` | `npm ci --ignore-scripts` then `npm run build` | `dist` |
| Render API | Repository root | `pip install -r requirements.lock` | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

URLs and secrets belong in each host's environment settings. No deployment is performed by these files. See [deployment](docs/deployment.md).

## Repository structure

```text
app/                 API, validated contracts, workflow, booking service, retrieval
frontend/            Browser source, Node build/tests, static-server Dockerfile
knowledge-base/      Backend-only source documents, chunks and metadata
migrations/          Versioned database schema changes
scripts/             Launch and diagnostic commands
certs/               Public database CA certificate
tests/               Automated backend tests
docs/                Assessment, setup and verification documents
Dockerfile           Non-root Python API image
compose.yaml         Two-service local container setup
```

Dependencies are declared in `pyproject.toml` and pinned in `requirements.lock` / `requirements-dev.lock`; frontend metadata and lockfile are under `frontend/`. Read [AI/tools disclosure](docs/ai-tools-and-technologies-disclosure.md) for development assistance and evidence boundaries.

## Assessment documents

- [Part 8 — Docker & Code Quality](docs/part-8-docker-and-code-quality.md): container design, dependencies, structure and verification limits.

- [Part 12 — Debugging Case](docs/part-12-debugging-case.md): reproduce, diagnose, fix and test a false reschedule-success claim after a timeout.
- [Bonus — Judgment Challenge](docs/bonus-judgment-challenge.md): a clearly labelled hypothetical leadership instruction, challenged in under 400 words.
- [AI, Tools and Technologies Disclosure](docs/ai-tools-and-technologies-disclosure.md): assistance, runtime stack, verification evidence and unfinished features.
- [Part 13 — Engineer-to-Business Communication](docs/part-13-engineer-to-business-communication.md): a short customer explanation of AI limitations, reliability checks and human approval for late changes.
- [Part 9 — Model / Cost Comparison](docs/part-9-model-cost-comparison.md): configured Groq 120B versus Claude Haiku 4.5, 100,000-interaction budget and explicit latency assumptions.
- [Part 7 — Automated Tests](docs/part-7-automated-tests.md): core/failure coverage, added notice-policy tests, results and the highest-risk concurrency gap.
- [Part 11 — Workflow vs Agent](docs/part-11-workflow-vs-agent.md): why deterministic controls govern appointment changes, particularly the 24-hour cancellation/rescheduling boundary.
- [Final submission summary](<docs/What Works, What Does Not, What I Would Build Next.md>): what works, what remains limited and the three next-version priorities.
- [Part 10 — Production Architecture](docs/part-10-production-architecture.md): target architecture diagram and changes required before real patient deployment.
- [Part 6 — Evaluation](docs/part-6-evaluation.md): 24 booking, adversarial and knowledge-base cases with expected behaviour, pass/fail criteria and a results template.
- [Part 5 — Guardrails & Failure Handling](docs/part-5-guardrails-and-failure-handling.md): ambiguity, unavailable slots, invalid IDs/errors, injection, sensitive information and human-approval boundaries.
- [Preventing unsupported knowledge-base claims](docs/part-2-rag-preventing-unsupported-kb-claims.md): evidence selection, deterministic safeguards, qualifications, fallback responses, examples and limitations.
- `docs/chatbot-python-sql-communication.md`: complete communication contracts, SQL interaction, scenario walkthroughs and assessment mapping.

- `docs/database.md`: relationships, constraints, trust boundaries and assumptions.
- `docs/api-workflow.md`: endpoint contracts, confirmation flow and state transitions.
- `docs/openapi.json`: generated API schema; `/docs` serves the running version.
- `docs/evaluations.md`: cases, expected behaviour and pass/fail criteria.
- `docs/verification.md`: verification evidence and remaining gaps.
- `docs/booking-workflow.md`: agreed source workflow, retained as a design reference.

