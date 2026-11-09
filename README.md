# Faisla PK API

## Configuration

Copy `.env.example` to `.env`, replace the placeholder database password with a
unique random value, and set a unique `SECRET_KEY` of at least 32 bytes. You
can generate independent values with:

```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Use the first value for `POSTGRES_PASSWORD` and the second for `SECRET_KEY`.
Keep `.env` out of source control. For local containers, `docker-compose.yml`
uses the `POSTGRES_*` settings to construct the database connection to the
Compose `db` service. For a host-run API, set `DATABASE_URL` to the host's
PostgreSQL address.

Start the local services after editing `.env`:

```powershell
docker compose up --build -d
docker compose exec api alembic upgrade head
```

Run the backend test suite in its Linux container with:

```powershell
docker compose --profile test run --build --rm test
```

The test command uses isolated SQLite test databases. CI additionally runs all
migrations, a full rollback/re-apply cycle, and the tests against temporary
PostgreSQL.

## Database migrations

The application does not create or drop tables during startup. Apply Alembic
migrations before starting the API:

```powershell
.\venv\Scripts\alembic.exe upgrade head
```

For a database that already contains the tables created by the previous
`create_all()` startup code, back up the database, verify its schema matches
revision `0001_initial`, then baseline it and apply the integrity migration:

```powershell
.\venv\Scripts\alembic.exe stamp 0001_initial
.\venv\Scripts\alembic.exe upgrade head
```

Revision `0002_profile_integrity` aborts if a lawyer has more than one profile;
resolve duplicates before applying it.

## Render deployment

The Docker runtime target starts Uvicorn and listens on Render's injected
`PORT` (falling back to `8000` for local use). If deploying as a native Python
web service instead of Docker, use:

```text
Build command: pip install -r requirements.txt
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Do not use the test target or `pytest` as the web service's start command.
Configure production environment variables such as `DATABASE_URL` and
`SECRET_KEY` in Render, and run `alembic upgrade head` as a deployment
pre-deploy command after backing up any valuable database.

## Authentication

Register clients or lawyers at `/auth/register/client` and
`/auth/register/lawyer`. Client registration stores a name, phone, city, and
address, with CNIC optional. Lawyer registration stores contact information,
practice city, office address, specialization, experience, and bar details.
Log in at `/auth/login` using OAuth2 form fields
(`username` is the email address). Access tokens are short-lived JWTs. Refresh
tokens are stored as hashes, rotate on every `/auth/refresh` request, and are
rejected after reuse. `POST /auth/logout` revokes the refresh-token family.
Deactivating an account revokes all of its refresh sessions. Apply the latest
Alembic migration before using these endpoints.
Authenticated clients can retrieve their account summary from `GET /auth/me`.

Lawyers can create, read, update, and delete their own profile under
`/lawyer-profiles/me`. Admins can list and manage any lawyer profile under
`/lawyer-profiles`.
No public admin-registration endpoint exists; provision the first admin
through a controlled operational process, never by accepting a client-supplied
role during registration.

The public marketplace is available at `GET /lawyers` and
`GET /lawyers/{profile_id}`. It includes only active lawyer accounts with
approved profiles. Pass `preferred_city` to rank lawyers in that city first;
`city` remains an exact city filter. Search supports city, specialization, minimum/maximum years
of experience, verification status, and pagination. Public results do not
include CNIC, bar-council identifiers, or password hashes.
Use the result's `user_id` as `lawyer_id` when creating an appointment;
`id` identifies the public lawyer profile.

## Appointments

Apply the current Alembic head before serving booking endpoints. Lawyer
availability uses ISO weekdays (`0` = Monday, `6` = Sunday) and Asia/Karachi
local times. The `tzdata` dependency supplies IANA rules on platforms such as
Windows that do not provide a system timezone database. If those rules are
unavailable, booking calculations log a warning and fall back to fixed UTC+05:00.
New consultations last 60 minutes.

- Lawyers manage recurring slots at `POST /availability`,
  `GET /availability/me`, `PUT /availability/{id}`, and
  `DELETE /availability/{id}`.
- Clients book and list their consultations at `POST /appointments` and
  `GET /appointments/my`.
- Lawyers list requests at `GET /appointments/lawyer` and approve, reject, or
  complete them using the corresponding `/appointments/{id}/...` endpoints.
- Clients may cancel their own pending or approved bookings with
  `PUT /appointments/{id}/cancel`.

Only active lawyers with approved profiles can be booked. Pending and approved
appointments block overlapping times for both the lawyer and client. Requests
are serialized on the involved user rows to prevent concurrent double-booking
on PostgreSQL.

## Case management

Lawyers create cases for active client accounts with `POST /cases`, update case
details with `PUT /cases/{id}`, and change status with
`PUT /cases/{id}/status`. The assigned lawyer can append notes through
`POST /cases/{id}/notes`. Clients, assigned lawyers, and admins can read
permitted cases and notes; clients and lawyers list their own cases at
`GET /cases/my`, while admins can list all cases at `GET /cases`.

Case notes and status history are append-only. Every case starts with an
initial `OPEN` history entry, and each later status change is written atomically
with the case update. `GET /cases/{id}/status-history` exposes the audit trail
to case participants and admins. `CLOSED` is terminal and cannot be reopened.

## Case documents

Configure `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and
`CLOUDINARY_API_SECRET` in `.env`, then apply the current Alembic head before
using document endpoints. Files are stored as authenticated Cloudinary assets;
the API returns short-lived signed download URLs only after checking that the
requester is a case participant or admin.

- Upload a multipart file to `POST /cases/{case_id}/documents`. Optional form
  fields are `document_type` (`contract`, `evidence`, `court_order`,
  `agreement`, `id_document`, or `other`) and `description`.
- List documents at `GET /cases/{case_id}/documents` and get one at
  `GET /documents/{document_id}`.
- Delete a document at `DELETE /documents/{document_id}`. The uploader, the
  assigned lawyer, or an admin may delete it; the Cloudinary asset is removed
  before its database metadata.

Uploads are limited to 10 MiB and checked against PDF, DOC, DOCX, JPEG, or PNG
file signatures. The original filename is metadata only; storage uses a
server-generated identifier. Add malware scanning and a recovery/reconciliation
process before handling sensitive production documents.

## Admin APIs

All `/admin` routes require an authenticated admin account. Provision the first
admin through an operational process; public registration cannot grant the
admin role.

- `GET /admin/users` lists users with optional `role`, `is_active`, and email
  `search` filters, plus bounded `offset`/`limit` pagination.
- `GET /admin/users/{user_id}` returns safe account fields without password
  hashes. `PUT /admin/users/{user_id}/activate` and `/deactivate` manage account
  access. Admins cannot deactivate themselves or the last active admin.
- `GET /admin/lawyers/pending` lists verification records. The `user_id` in
  each result is used with `PUT /admin/lawyers/{user_id}/approve` or `/reject`.
- `GET /admin/dashboard` returns user, lawyer, case, and pending-appointment
  counts.

## Notifications

`GET /notifications` returns the authenticated user's notifications with
bounded pagination. Mark one read with `PUT /notifications/{id}/read`; users
cannot access another account's notification. Notifications are written in
the same database transaction as appointment requested/approved/rejected/
cancelled, case created/updated/status changed, and document uploaded/deleted
events. Delivery is in-app only; email, push, and background retries are not
configured.

## Frontend

The Next.js 15 application is in `frontend/`. Install Node.js 20 LTS or later,
then create `frontend/.env.local` from `.env.example` and set
`FAISLA_API_URL` to the backend URL. Local development defaults to
`http://127.0.0.1:8000`; production requires the server-side `FAISLA_API_URL`
to be set (for example, the public HTTPS URL of the Render API) and does not
silently fall back to localhost. Set this variable in the Vercel project's
Environment Variables for each deployment environment. It is not a
`NEXT_PUBLIC_*` variable: requests are forwarded server-to-server through the
Next.js API routes. Install dependencies and start the development server from
that directory:

```powershell
cd frontend
npm install
npm run typecheck
npm run lint
npm run build
npm run dev
```

The frontend uses a same-origin Next.js API proxy for backend requests and
stores access/refresh tokens in HttpOnly cookies rather than browser storage.
The frontend includes public lawyer search/detail, registration and sign-in,
appointment and availability management, case details/notes/status history,
case document uploads and downloads, in-app notifications, and admin dashboard,
lawyer-review, and user-management screens. Some records are identified by
numeric user ID because the current backend responses do not include related
party names.

## Tests

Run the unit tests with the configured project interpreter:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

The Docker test image uses `python -m pytest -q`. The current test files are
`test_lawyer_profiles.py`, `test_booking.py`, `test_case_management.py`,
`test_documents.py`, and `test_admin_notifications.py`.