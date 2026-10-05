# Start the project in VS Code

These commands use **PowerShell** in VS Code and your existing Python environment and `.env` files. Docker is not required.

## 1. Open the project

In VS Code, choose **File → Open Folder** and open:

```text
C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend
```

Choose **Terminal → New Terminal**. Select PowerShell if it is not already selected.

## 2. Terminal 1: start the backend

Copy and run:

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend"
& "..\..\work\.venv\Scripts\python.exe" -m scripts.run_server
```

Leave this terminal running. This command reads the backend host, port, database and Groq settings from the root `.env` file.

**Optional: automatic reload while editing Python.** Stop the command above with **Ctrl+C**, then use this instead, assuming the default local host/port:

```powershell
& "..\..\work\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run only one backend command at a time. The reload command's explicit host/port overrides the environment's host/port settings.

## 3. Terminal 2: start the frontend

Click the terminal **+** button to open another PowerShell terminal. Copy and run:

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend\frontend"
npm.cmd ci --ignore-scripts
npm.cmd run dev
```

Leave this terminal running too. `npm.cmd ci --ignore-scripts` is only needed for initial setup or after the dependency lockfile changes. On later starts, use:

```powershell
cd "C:\Users\user\Documents\Codex\2026-09-28\hey-i-got-an-assessment-to\outputs\booking-backend\frontend"
npm.cmd run dev
```

The frontend reads its public configuration from `frontend/.env`. Refresh the browser after editing frontend files; this development server does not provide automatic browser refresh.

## 4. Open the application

With the default local settings:

- **Chatbot:** [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **API documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **API liveness:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Database readiness:** [http://127.0.0.1:8000/ready](http://127.0.0.1:8000/ready)

Use the addresses printed in your terminals if your configured ports differ. Use `127.0.0.1` consistently rather than mixing it with `localhost`, since these are different browser origins.

## 5. Stop or restart

Press **Ctrl+C** in each running terminal to stop that service. To restart, rerun its startup command. Restart the relevant service after changing an `.env` file.

## If something does not start

| Problem | What to check |
|---|---|
| Python executable not found | The existing environment path is specific to this workspace. Use the fresh-environment instructions below if it has been moved or removed. |
| `npm.cmd` not found | Install Node.js 22+ and reopen VS Code so its terminal receives the updated PATH. |
| Address/port already in use | Another instance may already be running. Stop that instance in its terminal, or configure different ports and matching frontend/backend URLs. |
| Frontend cannot reach the API | Start Terminal 1; check `FRONTEND_API_BASE_URL` in `frontend/.env` and `FRONTEND_URL` in root `.env`. |
| Demo disabled | For this local synthetic demo, set `DEMO_ENABLED=true` in root `.env` and restart the backend. This is shared demo access, not individual patient login. |
| Database/provider error | Check `/ready` and the backend terminal. Verify the private database/Groq settings locally; do not paste secrets into chat or commit them. `/ready` does not verify that the Groq key is valid. |

Your environment files and database are already configured. Do **not** overwrite the files, rerun seed commands or apply migrations just to start the existing application.

## Only if the existing Python environment is unavailable

From the repository root, create a replacement local environment:

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.lock
& ".\.venv\Scripts\python.exe" -m scripts.run_server
```

This requires Python 3.12+ and uses the existing root `.env`. On subsequent starts, only run the last command. It avoids needing to change PowerShell's activation policy.

For full setup and hosting details, see [README](README.md) and [local development](docs/local-development.md).
