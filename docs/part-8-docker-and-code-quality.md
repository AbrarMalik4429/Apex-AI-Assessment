# Part 8 — Docker & Code Quality

## Delivered setup

The previous backend-only Compose setup has been replaced with one consistent two-service definition:

- [Root Dockerfile](../Dockerfile): Python 3.12 API, locked dependencies, explicit application-file copies, non-root runtime user and a liveness health check.
- [Frontend Dockerfile](../frontend/Dockerfile): Node 22 build stage followed by an unprivileged Nginx static server. Only compiled public assets enter the final frontend image.
- [compose.yaml](../compose.yaml): API and frontend with separate ports, frontend startup after API liveness, runtime backend environment injection and public-only frontend build arguments.
- Separate [.dockerignore](../.dockerignore) and [frontend/.dockerignore](../frontend/.dockerignore) allowlist build inputs. Neither real environment file is copied into an image.

The old `db` service, automatic `DOCKER_DATABASE_URL` override and Compose-created database volume declaration are removed. The example environment no longer offers the old `LOCAL_POSTGRES_*`/database-override variables. No existing container, volume, private environment file or database was deleted. Old variables in a user's private environment are simply unused by this Compose definition.

## Configure and run

Requires Docker Engine/Desktop with Compose v2 and Linux containers. From the backend/repository root, copy `.env.example` and `frontend/.env.example` only if their real counterparts do not already exist.

| File | Required configuration |
|---|---|
| Root `.env` | Private `DATABASE_URL`, appropriate TLS certificate setting, Groq key/provider/model settings, `FRONTEND_URL`, host `APP_PORT`. `DEMO_ENABLED=true` is needed for the shared synthetic demo. |
| `frontend/.env` | Browser-reachable `FRONTEND_API_BASE_URL`, host `FRONTEND_PORT`, optional `FRONTEND_FONT_URL`. No credentials. |

Default examples expose the API at `http://127.0.0.1:8000` and frontend at `http://127.0.0.1:5173`. URLs remain environment configuration. The API listens on port 8000 inside its container and Nginx on 8080; Compose maps the configured host ports to those internal ports. `DOCKER_BIND_ADDRESS` defaults to loopback.

`FRONTEND_API_BASE_URL` must be reachable from the user's browser: do not set it to `http://api:8000`, which is only a possible container-network address. `FRONTEND_URL` must match the browser's exact frontend origin for CORS. The optional font URL is public.

```powershell
docker compose --env-file .env --env-file frontend/.env config --quiet
docker compose --env-file .env --env-file frontend/.env up --build -d
docker compose --env-file .env --env-file frontend/.env ps
docker compose --env-file .env --env-file frontend/.env logs --tail 50 api frontend
```

The two `--env-file` flags supply Compose interpolation; only the root file is passed to the API container. The frontend receives only its two allowlisted public build arguments. Avoid sharing expanded `docker compose config` output because it can include secrets; `config --quiet` validates without printing it.

Stop this stack without deleting database data:

```powershell
docker compose --env-file .env --env-file frontend/.env down
```

Rebuild the frontend after changing its API/font settings: they are compiled public configuration. Backend changes to runtime environment take effect when Compose recreates the API container. This static container serves built assets, not the Node development server.

## Database and health behaviour

Compose uses the database already configured in `DATABASE_URL`, including the existing Supabase connection. It does not automatically migrate or seed on startup. Database credentials must permit the intended operations; the normal runtime login should not gain schema-management permissions.

For a newly created disposable database, migration/seed must be an explicit administrative setup step, as described in the [README](../README.md). Do not reseed the existing project. A host-local database address needs a container-reachable hostname; `localhost` inside the API container is the container itself. TLS certificate paths must refer to files inside the image, such as the included public `certs/supabase-ca.crt`, not a Windows absolute path.

The API Docker health check calls `/health` and proves process liveness only. `/ready` checks database connectivity and whether Groq is configured; it does not verify that the key works. The frontend check verifies that Nginx serves its root page. Passing these checks does not establish booking correctness or provider availability.

## Dependency management and structure

Python dependencies are declared in [pyproject.toml](../pyproject.toml); [requirements.lock](../requirements.lock) and [requirements-dev.lock](../requirements-dev.lock) pin runtime and development packages. Docker installs the runtime lock rather than resolving version ranges at build time. Keep lockfiles synchronized when dependencies change.

Frontend metadata and [package-lock.json](../frontend/package-lock.json) support `npm ci --ignore-scripts`. The frontend currently has no third-party npm application dependencies. Node is used to build/test; it is not included in the final Nginx stage.

Base images use maintained tags, not immutable digests. This allows upstream patches but means builds are not byte-for-byte reproducible. Before a production release, select and scan tested image digests and schedule dependency updates; no digest pinning or vulnerability scan is claimed here.

The project keeps responsibilities explicit:

| Directory/module | Responsibility |
|---|---|
| `app/main.py` | HTTP endpoints, sessions, transactions and safe error responses. |
| `app/contracts.py` | Validated request, interpretation and response structures. |
| `app/workflow.py` | Clarification, proposal and confirmation transitions. |
| `app/booking_service.py` | Owned booking operations and availability/policy checks. |
| `app/groq_client.py`, `app/knowledge.py` | Provider boundary and evidence retrieval/rendering. |
| `frontend/src/`, `frontend/scripts/` | Browser interface and independent build/development tools. |
| `migrations/`, `tests/`, `docs/` | Schema history, automated evidence and implementation explanations. |

Code-quality controls include typed/Pydantic contracts, small service boundaries, meaningful regression tests and Ruff checks. Model interpretation is separated from authorization and database writes. No broad rewrite was needed to provide container packaging. Detailed setup/environment tables have moved to [local-development.md](local-development.md), leaving the README as an entry point.

## Verification and remaining limitation

Checks performed for this change:

- **119 backend tests passed** on isolated SQLite fixtures; one existing TestClient deprecation warning remains.
- **3 frontend tests passed**, including public-config allowlisting and private-file exclusion.
- Full repository Ruff check and frontend static build passed.
- Compose YAML parsed successfully; checked that it contains only API/frontend services, no database URL override, and only public frontend build arguments.

**Docker is unavailable on this machine. Image builds, image pulls, Nginx configuration execution, Compose interpolation and container networking have not been runtime-verified.** YAML parsing is not a replacement for `docker compose config` or a container smoke test.

On a Docker-enabled host, run the commands above and verify both services become healthy; call `/ready`; load the browser UI; perform a synthetic booking/confirmation and knowledge query; inspect image contents for private-file exclusion; stop/restart and confirm persistent database state. Confirm occupied local ports are free before starting. Do not claim production readiness until these checks and the identity/concurrency requirements in [Part 10](part-10-production-architecture.md) are addressed.

Vercel/Render native deployment remains supported; using these local Docker files is not a requirement for the existing native hosting approach. See [deployment.md](deployment.md).
