# -MHelpBackend
ΙΜMHelpBackend

//check stuff

1) python server.py

2) Invoke-WebRequest -Uri "http://localhost:5000/ask" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"name":"John","question":"Hello"}'

3) curl http://localhost:5000/ping



Windows Machine Setup 

1) Install Python
2) Install pip
3) pip install flask
4) pip install flask openai chromadb
5) pip install python-dotenv
6) pip install sqlalchemy psycopg2-binary
7) pip install bcrypt

8) Set up postgress


Testing
9) Invoke-WebRequest -Uri "http://localhost:5000/users" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"email": "test@test.com", "password": "123456", "username": "testuser"}'

8) Invoke-WebRequest -Uri "http://localhost:5000/chats" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"user_id": 1}'

10) Invoke-WebRequest -Uri "http://localhost:5000/ask" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"user_id": 1, "chat_id": 1, "question": "What documents are needed for Cyprus visa?"}'

11) команда для гойды docker compose exec backend python make_admin.py ваша@почта

## Setup

    pip install -r requirements.txt
    copy .env.example .env      # then fill in the values (Windows; cp on macOS/Linux)
    python server.py

On start the server creates missing tables and adds new columns to existing ones
(`init_db()` in `models.py`), so an existing database upgrades itself. No manual migration.

## Accounts, tokens and admins

`POST /login` and `POST /users` return the user with a `role` and a `token`. Every other route
except `/ping` needs `Authorization: Bearer <token>`. The server takes the user from the token and
only lets them see and change their own chats; a `user_id` in the body is ignored.

Make the first admin after registering in the app:

    python make_admin.py you@example.com            # --remove to undo

Log out and in again in the frontend to see the admin pages. Banned users get 403 with
`"code": "banned"` on login and on every request; the ban applies immediately.

| Route | What it does |
|---|---|
| `PATCH /chats/<id>` `{title}` | Rename your chat |
| `DELETE /chats/<id>` | Delete your chat with its messages |
| `GET /admin/stats` | Users, banned, questions in 7 days and in total |
| `GET /admin/top-questions?days=7&limit=10` | Most asked questions (`days=0` = all time) |
| `GET /admin/users` | Users with question count and last activity |
| `POST /admin/users/<id>/ban` `{reason}`, `POST /admin/users/<id>/unban` | Ban / unban |
| `GET`, `POST /admin/advertisers`, `PATCH /admin/advertisers/<id>` | List, add, edit advertisers |
| `POST /admin/advertisers/<id>/status` `{status, reason, checks}` | Approve, reject, suspend, reactivate |
| `GET /admin/analytics/users?days=30&tz=-180` | Per day: new users, total users, active users |
| `GET /admin/analytics/topics?days=30&tz=-180` | Per day and in total: questions per router topic |
| `GET /admin/analytics/load?hours=6` | Active sessions now and per 5 minutes, answers in progress |
| `POST /heartbeat` | Sent by open app tabs once a minute; marks the user active |

`tz` is JavaScript's `getTimezoneOffset()`, so days are grouped in the admin's local time.

### Where the analytics numbers come from

- **Users**: `users.created_at`. Accounts made before this column existed get the date of their
  first message (set automatically on start).
- **Topics**: `/ask` saves the router's labels in `messages.topics`. Questions asked before this
  update have no topic and are shown as "no topic".
- **Active sessions**: `user_activity` gets one row per user per minute with an authenticated
  request or heartbeat (`metrics.py`); rows older than 14 days are removed. "Answers in progress"
  is counted inside the server process, so with several worker processes each reports its own.

Code: `models.py` (database), `auth.py` (tokens, `login_required`, `admin_required`),
`admin_api.py` (dashboard, users, advertisers), `analytics_api.py` (charts), `metrics.py`
(activity tracking and answers in progress).

## Prompt routing

`/ask` routes each question to a topic prompt before answering, and searches only that topic's
documents. See `PROMPT_ROUTING.md` for the design and `documents/README.md` for where to put new
source files.

The response now carries the routed labels so you can see what the router picked, plus the
sponsored slot for that turn:

`{"answer": "...", "topics": ["VISA"], "advertisement": {...} | null}`

## Sponsored slot

Every answer comes back with an `advertisement` field. It is chosen by the server, never written
by the model: one approved advertiser (`/admin/advertisers`) whose topics overlap the routed
topics, picked at random, or `null` when none matches. Refusals carry no ad.

```json
{"label": "Sponsored", "id": 7, "company": "...", "website": "...", "category": "law_firm"}
```

The frontend renders it under the answer and must keep the `label` visible — it is what separates
paid placement from the advice above it. The ad is deliberately not saved into the transcript, so
it never comes back as history and the model never learns to imitate it.

## Tests

    python tests/test_chat_flow.py    # end-to-end /ask, history and compaction
    python tests/test_admin_api.py    # tokens, chat ownership, admin routes, bans, advertisers
    python tests/test_documents.py    # document catalogue, ingestion, downloads, sponsored slot

No API key or Postgres needed — OpenAI is stubbed, Chroma uses a temp path and the
end-to-end test runs on a throwaway SQLite database.
