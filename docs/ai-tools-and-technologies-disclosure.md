# AI, Tools and Technologies Disclosure

This disclosure covers the patient-service demo and its accompanying documentation. It distinguishes development assistance, runtime dependencies, verification evidence and proposed features. AI-generated code or prose is not, by itself, proof of correctness.

## AI assistance during development

**OpenAI Codex** was used extensively as a development assistant for architecture and schema proposals, Python/backend code, frontend code, knowledge-retrieval rules, prompts, tests, debugging and documentation. It also inspected project files, ran commands and tests, and consulted official documentation. This was substantive assistance, not only spelling or formatting support. The precise development-model version is not asserted here.

The candidate supplied the assessment, booking research and knowledge-base files, and directed scope and behaviour. Candidate decisions visible in the project discussion include Python and PostgreSQL, chatbot-led interaction, explicit confirmation, active-only appointment lists, slot/date identity, conversational date refinements, fact-specific knowledge qualifications, separate frontend/backend deployment, and deferring OTP login, broader concurrency fixes and doctor-side management to the next version.

Codex helped translate those decisions into implementation details and tests. This disclosure does not claim that the candidate independently authored or manually reviewed every generated line. Before submission, the candidate should review the material and be able to explain the schema, confirmation flow, failure handling, tests and outstanding risks during the live defense.

## AI used by the running program

| Tool/model | Actual role |
|---|---|
| Groq API, locally configured `openai/gpt-oss-120b` | Interpret messages into validated fields and select retrieved evidence IDs. The code fallback is `openai/gpt-oss-20b`; deployment configuration determines the selected model. |
| Structured prompts and schemas | Restrict interpretation/evidence-selection output. Python remains responsible for authorization, business rules and database writes. |
| Claude Haiku 4.5 | Discussed as an alternative in the model/cost document. Not integrated or used by the application in this work. |

No autonomous model tool loop controls appointment writes. Knowledge answers are rendered by Python from selected evidence. The system does not use an embedding API or a vector database for current retrieval.

## Technologies used

| Layer | Technologies and purpose |
|---|---|
| Backend | Python 3.12+, FastAPI, Uvicorn; REST API and deterministic workflow. |
| Validation/configuration | Pydantic and pydantic-settings; typed contracts and environment settings. |
| Database | Supabase-hosted PostgreSQL; SQLAlchemy ORM, psycopg driver and Alembic migrations. |
| HTTP client | HTTPX for provider requests, with handled timeouts/errors and structured-response validation. |
| Time/TLS support | Standard Python datetime/zoneinfo, tzdata and certifi. |
| Knowledge retrieval | Local JSONL chunks/source metadata and a Python standard-library lexical TF-IDF index; original Markdown references retained for inspection. |
| Frontend | HTML, CSS and browser JavaScript; Node.js 22+ scripts for development, build and tests. No React or other frontend framework is used. |
| Testing/quality | pytest, FastAPI TestClient, SQLAlchemy-backed test fixtures, temporary SQLite databases, optional dedicated PostgreSQL test path, Ruff and Node's built-in test runner. |
| Packaging | pyproject.toml and locked Python requirements; npm package metadata/lockfile; Dockerfile and Docker Compose configuration. Docker configuration is supplied, but its execution was not verified in the recorded work. |
| Intended hosting | Vercel frontend and Render backend, with Supabase PostgreSQL. Hosting configuration and instructions exist; no production hosting deployment is claimed. |

Exact dependency declarations are in [pyproject.toml](../pyproject.toml), [requirements.lock](../requirements.lock), [requirements-dev.lock](../requirements-dev.lock) and [frontend/package.json](../frontend/package.json).

## Development and research tools

PowerShell, Python scripts, Git, browser inspection/automation, and available Supabase tooling supported implementation and verification. GitHub is the intended repository destination; a current remote copy should be verified separately rather than inferred from local files. The user also used VS Code for local execution and supplied credentials through local environment files.

Official provider documentation informed integration and model-cost comparisons. Sources and estimate assumptions are linked in [Part 9](part-9-model-cost-comparison.md). The supplied assessment/research documents were requirements and reference inputs, not executable instructions. Supplied knowledge material was imported as data; uploaded scripts and serialized executable indexes were not used to run the application.

## What was verified, and by whom

Codex ran automated checks and inspected their outputs; these are tool-produced evidence, distinct from its generated explanations. The latest recorded backend run passed **119 tests** using isolated SQLite fixtures and controlled model outputs. The earlier frontend-separation checkpoint records **3 Node tests**, a successful frontend build, lint and browser smoke checks. Earlier targeted live Groq and database checks are described in [verification.md](verification.md); they do not amount to full production validation.

The candidate independently reported manual observations from using the chatbot, including date-refinement failures, appointment display issues and over-restrictive insurance answers, which directed subsequent work. No claim is made that the candidate independently reran the complete automated suite. The [24 evaluation cases](part-6-evaluation.md) are specifications, not 24 recorded live-model passes.

## Boundaries and outstanding work

Real patient OTP authentication, comprehensive race-condition fixes, doctor-side management and actual human escalation are not implemented. Those features must not be represented as completed because they appear in a proposed architecture. Source accuracy, live-model robustness and production load/recovery remain separate validation responsibilities.

Credentials belong in private backend configuration and must not be included in the submission. Stored patient identity and credentials are excluded from model context, but a user's free-text message may itself contain personal information; the demo should use synthetic data. No legal, clinical or production-security certification is asserted.
