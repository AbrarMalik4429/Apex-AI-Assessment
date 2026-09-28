# Apex AI Arabia database setup

Configured and verified on 2026-09-28.

| Setting | Value |
|---|---|
| Project | Apex AI Arabia |
| Project reference | Set locally from your Supabase project |
| Region | Choose for your deployment |
| PostgreSQL | Use a supported PostgreSQL release |
| Application schema | booking |
| Runtime role | booking_runtime |
| Working host | Copy the session-pooler host from your project Connect panel |
| Port / mode | 5432 / session pooling |
| TLS | verify-full with Supabase's public CA |
| Credential location | Backend's local .env; excluded from Git, Docker build and ZIP |
| Alembic schema revision | 603768ba3dac |

Deployment identifiers and endpoint details are intentionally omitted from this public checkpoint. Retrieve them from your own Supabase dashboard and store connection settings only in the local `.env`.

## Applied changes

Created seven application tables: patient, doctor, slot, doctor_leave, bookings, patient_session and operation. Added the migration version table, checks, foreign keys and query/relationship indexes. Enabled RLS and restricted schema access. No pre-existing application tables were present.

Loaded synthetic fixtures: 2 patients, 2 doctors, 84 recurring weekly slots, 1 leave interval, 1 completed visit and 1 pending follow-up. No real patient records were used.

The approved runtime login can read doctor/schedule/leave/patient tables, read/insert/update bookings and sessions, and read/insert operation records. It cannot delete, edit doctor schedules, manage schemas/roles or bypass RLS. It can read the Alembic version for diagnostics. Patient ownership remains enforced by Python. The account password was generated locally and was not displayed in chat.

The initial role-provisioning action required explicit approval from automatic review. The user approved the exact scope before the role was created. No bypass was used.

## Connection verification

The project's direct endpoint was not resolvable from this machine. The shared session pooler was verified using the approved role, the expected seeded tables and TLS hostname/certificate validation. The public CA was downloaded from Supabase's certificate distribution bucket:

[Supabase public CA certificate](https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt).

The Python backend reads `DATABASE_URL` and `DATABASE_SSL_ROOT_CERT` from its local `.env`. No Supabase publishable or service-role API key is needed for this PostgreSQL connection.

From the backend folder:

```powershell
& '..\..\work\.venv\Scripts\python.exe' -m scripts.check_database
& '..\..\work\.venv\Scripts\python.exe' -m scripts.smoke_database
```

The second command runs nine checks in a transaction that is always rolled back, using synthetic data and mocked language interpretation. It does not call Groq or change the demo fixtures permanently.

## Remaining setup

Add your Groq key to `GROQ_API_KEY` in the existing local `.env`, keeping the database settings intact. Then start Uvicorn using the README instructions. Do not share the `.env` or overwrite it with the example file.

Future schema changes need the Supabase administrator connector or a separate migration connection. The runtime login cannot perform migrations or doctor-side seed writes. Keep `DEMO_ENABLED=true` limited to this local synthetic demo.

Concurrency protection remains deferred as agreed. Supabase security advisors returned no findings. Initial performance advice identified three uncovered foreign keys; indexes were added. Unused-index notices on a freshly seeded project are expected and do not justify removing the query indexes.
