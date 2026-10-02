# Separate frontend and backend

## What runs where

| Component | Local development | Deployment | Responsibility |
|---|---|---|---|
| Frontend (`frontend/`) | Node development server, port from frontend/.env (5173 here) | Vercel static hosting | HTML/CSS/JavaScript, chat display, source references, option/confirmation buttons, requests to the API |
| Backend (`app/`, `scripts/`, `knowledge-base/`) | FastAPI, port from root .env (8000 here) | Render Python web service | Patient sessions, booking validation, database transactions, knowledge retrieval, Groq calls and safeguards |
| Supabase | Existing hosted project | Same configured PostgreSQL service | Doctors, slots, patients, bookings, sessions and operation records |
| Groq | Called by Python only | Called by Render only | Intent interpretation and knowledge evidence selection |

The browser downloads the website from the frontend origin, then sends authenticated API requests directly to the backend origin. There is no Vercel Python server, API proxy or duplicated booking logic. Both applications remain in one GitHub repository. Python stays at the repository root so existing backend commands and migration paths remain valid.

## Run locally: two terminals

From the project root, `outputs/booking-backend`:

```powershell
& "..\..\work\.venv\Scripts\python.exe" -m scripts.run_server
```

Alternatively, with your Python virtual environment activated, the familiar command still works:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, from the same project root:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the frontend address printed in the terminal (current local configuration: http://127.0.0.1:5173). The API is at http://127.0.0.1:8000; its `/` now returns service information, and `/docs` remains the API documentation. Stop either server with Ctrl+C in its own terminal. No existing user-owned process was restarted during the split.

Node.js 22+ is required. There are no third-party frontend dependencies. On a fresh checkout, copy root `.env.example` to `.env` and `frontend/.env.example` to `frontend/.env`, then fill the appropriate values. Do not overwrite existing environment files. The existing local files have already been configured for separate ports and backend credentials were preserved.

## Environment ownership

Root `.env` / Render environment:
- `DATABASE_URL`, `DATABASE_SSL_ROOT_CERT`: existing database connection and certificate path.
- `GROQ_API_KEY`, `GROQ_API_URL`, `GROQ_MODEL`, `GROQ_RESPONSE_MODE`: server-only provider settings.
- `FRONTEND_URL`: exact allowed browser origin. Local value is http://127.0.0.1:5173; deployed value is the stable Vercel/custom-domain origin. No trailing path. A different preview domain is not automatically permitted.
- `BACKEND_URL`: address used by the terminal demo client.
- `APP_HOST`, `APP_PORT`: local Python launcher settings. Render's start command uses its assigned `$PORT`.
- Existing clinic policy/timezone settings remain here.

`frontend/.env` / Vercel environment:
- `FRONTEND_API_BASE_URL`: required backend address. Local value is http://127.0.0.1:8000; production value is the Render API address. Missing/invalid values fail the frontend build rather than silently pointing to Vercel.
- `FRONTEND_FONT_URL`: optional stylesheet URL; empty uses system fonts.
- `FRONTEND_HOST`, `FRONTEND_PORT`: local development server only.

The frontend build generates `/frontend-config.js` from an explicit two-field allowlist (`apiBaseUrl`, `fontUrl`). It copies only four public files to `frontend/dist`: index.html, frontend-config.js, static/app.js and static/style.css. It never copies `.env`, Python, KB files or secrets. Environment changes on Vercel require rebuilding/redeploying; local env changes require restarting the Node server. Local source changes appear on browser refresh.

## Render

Use `render.yaml` at the repository root for a Blueprint, or create a Python Web Service manually:

- Root directory: repository root (the folder containing app/ and requirements.lock).
- Build: `pip install -r requirements.lock`.
- Start: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Health check: `/health`; check `/ready` separately for database connectivity.
- Fill the external variables marked `sync: false` using the existing connection/provider values and the final frontend/backend addresses.
- Include `knowledge-base/` and `certs/` in the repository. Do not run database seeding or schema migrations as part of each web build.

The Blueprint leaves `DEMO_ENABLED=false`. The current UI requires the synthetic demo session endpoint, so enable it only for an appropriately restricted synthetic demo; otherwise production login must be implemented first. No hosting resources have been created by adding this configuration.

## Vercel

Import the same GitHub repository and set **Root Directory = frontend**. `frontend/vercel.json` supplies:

- Framework preset: Other.
- Install: `npm ci --ignore-scripts`.
- Build: `npm run build`.
- Output: `dist`.

Add `FRONTEND_API_BASE_URL` for the relevant deployment environment, optionally add `FRONTEND_FONT_URL`, and deploy. Do not add Groq or database credentials. After obtaining the frontend's stable origin, configure Render's `FRONTEND_URL` to match and redeploy the backend. If you use preview deployments, explicitly configure their allowed origin before testing them against an API.

Render can be deployed first and the Vercel origin entered afterwards. No schema rebuild is required. The frontend API-docs link also uses the configured backend address.

## Verification

- Backend regression suite: 112 tests passed.
- Frontend tests: 3 passed (build allowlist, invalid URL handling, independent server and private-path isolation).
- `npm run build` and Ruff passed.
- A real browser connected to two temporary local servers, created a synthetic session and received a knowledge answer through actual cross-origin requests. The test used a disposable SQLite database and stubbed Groq, not live booking data. API-docs routing, secret exclusion and mobile overflow checks passed.
- Render/Vercel deployment and Docker execution have not been performed.

Configuration references checked on 2026-10-02: https://vercel.com/docs/project-configuration/vercel-json and https://render.com/docs/blueprint-spec .
