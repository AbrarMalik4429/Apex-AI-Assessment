# Apex chatbot frontend

Independent static frontend. Node.js 22+; no third-party frontend dependencies.

```powershell
# Only for a fresh checkout; preserve an existing .env:
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm.cmd ci
npm.cmd run dev
```

Run the Python API separately. Configure FRONTEND_API_BASE_URL in this folder's .env; configure the matching frontend origin as FRONTEND_URL in the backend's .env. This folder must never contain database or Groq credentials.

`npm run build` writes the four public files to dist/. `npm test` checks config isolation and serving. Vercel should use this folder as its project root; vercel.json contains the build settings. See ../docs/deployment.md for commands, environment ownership and deployment steps.
