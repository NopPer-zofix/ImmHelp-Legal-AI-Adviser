# ImmHelp: Legal AI Adviser

ImmHelp is an AI assistant that answers immigration and relocation questions for Cyprus: visas,
real estate, transport, and legal procedures. Each question is routed to the right topic, answers
are grounded in the official documents stored with the backend, and the source documents are
returned with each answer.

> ImmHelp is an information service, not legal advice. Check important decisions with a qualified
> lawyer or the relevant authority.

## Screenshots

_Screenshots coming soon._

## Features

- **Topic routing**: each question is classified (visas, transport, real estate, law, general) and
  searched only in that topic's documents.
- **Grounded answers**: answers are generated from indexed official documents, with document
  download links.
- **Chat history**: conversations are saved per user, can be renamed or deleted, and are compacted
  to keep long chats affordable.
- **Accounts and roles**: registration with consent, login with tokens, and user and admin roles.
- **Admin dashboard**: totals, most-asked questions, user management with bans, live activity, and
  charts for users and topics.
- **Advertiser review**: advertisers are approved or rejected by admins and shown in a labelled
  "Sponsored" slot next to answers. The model never writes ads.
- **Plans (mock-up)**: a free daily question limit and a demo upgrade flow. Payments are not
  connected yet.

## Architecture

```
Browser (React + Vite)
   │  /api/*  (Vite dev proxy or same-origin nginx)
   ▼
Flask backend (Python)
   ├── OpenAI API             answers, topic routing
   ├── Chroma                 vector search over the documents
   └── PostgreSQL (or SQLite) users, chats, messages, activity
```

## Tech stack

| Part | Technologies |
|---|---|
| Frontend | React 19, Vite, Recharts, plain CSS with light and dark themes |
| Backend | Python, Flask, SQLAlchemy, OpenAI API, ChromaDB, PostgreSQL |
| Dev and deploy | Docker (`Dockerfile` in each part), nginx config for the frontend |

## Repository layout

```
frontend/   React + Vite web app          → see frontend/README.md
backend/    Flask API, documents, tests   → see backend/README.md
```

## Getting started

### Prerequisites

- Node.js 20 or newer (frontend)
- Python 3.12 (backend; the Docker image uses 3.12)
- An OpenAI API key
- PostgreSQL, or a `DATABASE_URL` pointing to another database supported by SQLAlchemy

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # Windows PowerShell: copy .env.example .env
# Edit .env and fill in the values (see "Environment variables" below)
python server.py              # http://localhost:5000
```

On start the server creates any missing tables and columns, so no manual migration is needed.

Make the first admin after you register in the app:

```bash
python make_admin.py you@example.com
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env          # optional: the defaults work for local development
npm run dev                   # http://localhost:5173
```

The Vite dev server forwards `/api/*` to the backend, so the browser talks to one origin and
the backend needs no CORS setup.

### Run the frontend without the backend

```bash
cd frontend
npm run dev:mock
```

This uses an in-memory fake API. Demo logins: `demo@immhelp.cy` / `demo1234` (user) and
`admin@immhelp.cy` / `admin1234` (admin).

## Database

PostgreSQL stores users, chats, messages, activity, and advertisers. The table structure is in
[`backend/db/schema.sql`](backend/db/schema.sql). It contains structure only (no rows).

To create the empty database yourself:

```bash
createdb immhelp
psql -d immhelp -f backend/db/schema.sql
```

You don't need to run this: the backend creates missing tables and columns when it starts.
To regenerate the schema after changing `backend/models.py`:

```bash
cd backend
python db/export_schema.py > db/schema.sql
```

## Environment variables

Real `.env` files are never committed. Copy the `.env.example` file in each part and fill it in.

**Backend (`backend/.env`)**

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI key used for answers and routing |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql://user:password@localhost:5432/immhelp` |
| `JWT_SECRET` | Signs login tokens. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_DEBUG` | `1` for development, `0` in production |
| `PUBLIC_BASE_URL` | Base for document download links given to the model. Must match the frontend's `VITE_API_URL` |

**Frontend (`frontend/.env`)**

| Variable | Purpose |
|---|---|
| `BACKEND_URL` | Where the Vite dev server forwards `/api` (the Flask backend) |
| `VITE_API_URL` | Base URL the browser uses for API calls. Keep `/api` in development |
| `VITE_MOCK` | Set by `npm run dev:mock` to use the in-memory fake API |

## Deployment

- Build the frontend with `npm run build` and serve `frontend/dist/` from the same origin as the
  API, or set `VITE_API_URL` to the API's full URL and enable CORS on the backend.
- Each part has a `Dockerfile`, and `docker compose` is used for local stacks.

## Tests

```bash
cd backend
python tests/test_routing.py
python tests/test_chat_flow.py
python tests/test_admin_api.py
python tests/test_documents.py
```

The tests do not need an OpenAI key or PostgreSQL: OpenAI is stubbed, Chroma uses a temporary path,
and the end-to-end tests run on a throwaway SQLite database.

## Documentation

- [Backend README](backend/README.md): API routes, accounts and tokens, analytics, and tests
- [Backend prompt routing](backend/PROMPT_ROUTING.md): how questions are routed to topics
- [Frontend README](frontend/README.md): structure, admin pages, mock-ups, and session handling

## License

Not specified yet.
