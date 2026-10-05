# Local development and environment reference

## Root directories

The **backend root is also the repository root**. There is no extra `backend/` directory.

| Application | Absolute path on this machine | Hosting root directory |
|---|---|---|
| Backend / Render | `C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend` | Repository root (`.`; leave Render Root Directory blank) |
| Frontend / Vercel | `C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend\frontend` | `frontend` |

Hosting paths assume the repository contains `app/`, `frontend/`, `requirements.lock` and `render.yaml` at its top level. If you upload the enclosing workspace instead, prefix each hosting root with `outputs/booking-backend`.

The backend root contains `app/`, `scripts/`, `knowledge-base/`, `certs/`, migrations and the private `.env`. The frontend root contains `src/`, `scripts/`, `package.json`, `vercel.json` and its own public-settings `.env`.

## Run locally: two separate terminals

Prerequisites: Python 3.12+ and Node.js 22+. Both environment files already exist on this machine; do not overwrite them. The database schema and synthetic seed are already installed.

### Terminal 1 — backend

Use the existing configured Python environment:

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend"
& "..\..\work\.venv\Scripts\python.exe" -m scripts.run_server
```

This reads `APP_HOST` and `APP_PORT` from the backend `.env`. For development with automatic code reload, use this **instead**:

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend"
& "..\..\work\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If your virtual environment is already activated, the equivalent old command is:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Only run one backend command at a time. The explicit Uvicorn host/port flags override the launcher convention; change them if you change the local API address.

### Terminal 2 — frontend

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend\frontend"
npm.cmd ci
npm.cmd run dev
```

`npm.cmd ci` is needed for initial setup or after the lockfile changes; subsequent starts only need `npm.cmd run dev`. Keep both terminals running. Press **Ctrl+C** in each terminal to stop that application.

- Website: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- Backend/API information: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Use `127.0.0.1` consistently with the supplied configuration: `localhost` is a different browser origin for CORS. Restart after `.env` changes. Refresh the browser after frontend source changes.

### Fresh checkout on another machine

From the backend root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Fill the backend environment variables below, then run `python -m scripts.run_server`. In a second terminal, from the frontend root:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm.cmd ci
npm.cmd run dev
```

The local `work/.venv` command is specific to this existing workspace; a fresh checkout uses its newly created `.venv`. Do not re-seed the existing Supabase database. New databases require separate administrator migration/seed setup, as described below.

## Build and hosting commands

| Setting | Frontend — Vercel | Backend — Render |
|---|---|---|
| Configuration file | `frontend/vercel.json` | `render.yaml` |
| Hosting root | `frontend` | Repository root |
| Runtime/preset | Other; Node.js 22+ for build | Python; Blueprint sets `PYTHON_VERSION=3.12.12` |
| Install command | `npm ci --ignore-scripts` | Included in build command |
| Build command | `npm run build` | `pip install -r requirements.lock` |
| Output directory | `dist` (relative to frontend root) | None — a running API service |
| Start command | None — Vercel serves static files | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | Website loads | `/health`; `/ready` checks database access |

Build the frontend locally from its root:

```powershell
npm.cmd run build
```

Output is `frontend/dist/`. This builds files; it does not start a server or deploy them. The public output contains only HTML, CSS, JavaScript and public API/font configuration. Python has no separate compilation step: installing `requirements.lock` prepares the backend. Render's `$PORT` expression is a hosting-shell command, not a PowerShell command to paste locally.

Import the same GitHub repository into both services, select the roots above, and set the environment variables below. The configuration files are ready; no deployment has been performed. Detailed hosting sequence: [docs/deployment.md](deployment.md).

## Frontend environment — local .env and Vercel

Local file: `frontend/.env`. On Vercel, enter values in the project's **Environment Variables** settings for the deployment environment you are using.

| Variable | Local value | Vercel value | Required? |
|---|---|---|---|
| `FRONTEND_API_BASE_URL` | `http://127.0.0.1:8000` | `https://YOUR-RENDER-SERVICE.onrender.com` | Yes; replace the placeholder with your actual API address |
| `FRONTEND_FONT_URL` | Empty, or your chosen font stylesheet URL | Empty, or your chosen font stylesheet URL | Optional |
| `FRONTEND_HOST` | `127.0.0.1` | Not needed | Local dev server only |
| `FRONTEND_PORT` | `5173` | Not needed | Local dev server only |

Vercel needs **no Groq key, database URL or Supabase credentials**. The build reads frontend environment settings and generates `frontend-config.js`; changing a Vercel value requires a new build/deployment. Missing `FRONTEND_API_BASE_URL` causes a clear build error.

## Backend environment — local .env and Render

Local file: `.env` in the backend/repository root. On Render, enter values in the service's **Environment** settings. The Blueprint prompts for entries marked `sync: false`. Add optional policy settings there if you want to override their defaults.

| Variable | Local value / purpose | Render value |
|---|---|---|
| `DATABASE_URL` | Existing private Supabase PostgreSQL connection string | Same intended database connection; copy privately, never into Git or frontend settings |
| `DATABASE_SSL_ROOT_CERT` | `certs/supabase-ca.crt` for the configured TLS connection | `certs/supabase-ca.crt` |
| `GROQ_API_KEY` | Your existing private Groq key | Your private Groq key |
| `GROQ_API_URL` | `https://api.groq.com/openai/v1/chat/completions` | Same provider endpoint |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Same model unless deliberately changed |
| `GROQ_RESPONSE_MODE` | `strict` | `strict` |
| `GROQ_TIMEOUT_SECONDS` | `15` | `15`, or omit for default |
| `FRONTEND_URL` | `http://127.0.0.1:5173` | `https://YOUR-FRONTEND.vercel.app` or its custom domain; exact origin, no path |
| `BACKEND_URL` | `http://127.0.0.1:8000`; terminal client address | `https://YOUR-RENDER-SERVICE.onrender.com` |
| `APP_HOST` | `127.0.0.1`; used by `scripts.run_server` | Not needed with the supplied Render start command |
| `APP_PORT` | `8000`; used by `scripts.run_server` | Not needed; Render supplies `PORT` |
| `PYTHON_VERSION` | Not needed in local `.env` | `3.12.12`, set by `render.yaml` |
| `CLINIC_TIMEZONE` | `Asia/Riyadh` | Same, or omit for default |
| `BOOKING_HORIZON_DAYS` | `90` | Same, or omit for default |
| `SESSION_HOURS` | `8` | Same, or omit for default |
| `CONFIRMATION_MINUTES` | `10` | Same, or omit for default |
| `CANCELLATION_NOTICE_HOURS` | `24` | Same, or omit for default |
| `RESCHEDULE_NOTICE_HOURS` | `24` | Same, or omit for default |
| `DEMO_ENABLED` | `true` for the existing synthetic chatbot demo | Blueprint defaults to `false`; see the demo-access note below |

**Demo access:** the current frontend uses `/demo/session`. With `DEMO_ENABLED=false`, it will report that the demo is disabled. Enable it only for an appropriately restricted synthetic assessment demo; it grants access to the shared demo patient. Production patient login is not implemented. Setting it to false does not create an alternative login flow.

Replace URL placeholders with the assigned hosting addresses. The two settings must point in opposite directions: Vercel's `FRONTEND_API_BASE_URL` points to Render; Render's `FRONTEND_URL` identifies the allowed Vercel browser origin. Update Render after Vercel assigns its stable address. Preview domains are different origins and are not automatically allowed.


For containers, use [Part 8](part-8-docker-and-code-quality.md). The former local PostgreSQL Compose service has been removed.
