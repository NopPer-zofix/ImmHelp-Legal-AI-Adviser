# IMMHelpFrontEnd

React + Vite frontend for the ImmHelp immigration adviser. Replaces the old Streamlit `main.py`
and talks to the same Flask backend (`IMMHelpBackend/server.py`) without backend changes.

## Run

Requires Node.js 20+.

```bash
npm install
cp .env.example .env      # optional, defaults work for local development
npm run dev               # http://localhost:5173, backend expected on :5000
```

Start the backend first (`python server.py`). The Vite dev server forwards every `/api/*` request to
Flask, so the browser sees a single origin and the backend needs no CORS setup.

### Without the backend

```bash
npm run dev:mock
```

Uses an in-memory fake API (`src/api/mock.js`). Log in with `demo@immhelp.cy` / `demo1234`.

### Production build

```bash
npm run build             # static files in dist/
```

Serve `dist/` from the same origin as the API (nginx, or Flask's static folder) and proxy `/api` to Flask.
If the API lives on another origin, set `VITE_API_URL` at build time and enable CORS on the backend.

## Structure

```
src/
  api/http.js          fetch wrapper for every backend endpoint
  api/mock.js          fake backend for UI work
  hooks/useChats.js    chat list, active chat, sending, retry, rename, delete
  lib/storage.js       remembered login, local chat names and deletions
  components/          AuthPage, ChatApp, Sidebar, ChatItem, UserMenu,
                       Welcome, Thread, Message, Composer, ConfirmDialog, Toast
  styles.css           design tokens, light and dark themes
```

## Admin mode

Two user types: `admin` and `user` (`src/lib/roles.js`). Admins get an "Admin dashboard" item in the
user menu and can open `#/admin`; everyone else sees a "for administrators" page there.

The dashboard shows totals, the most asked questions (7 days, 30 days, all time) and the user list with
search, a status filter, and ban / unban with a reason. Admins and your own account can't be banned.
Banned users can't log in or ask questions; their history is kept.

In mock mode log in as `admin@immhelp.cy` / `admin1234`.

### Backend

The admin routes live in `IMMHelpBackend/admin_api.py` (see the backend README for the list).
Make the first admin with `python make_admin.py you@example.com` in the backend folder, then log out
and in again. The role shown in the browser only decides which pages appear; the server checks the
token and the role from the database on every `/admin` request.

### Analytics

`#/admin/analytics` has three parts:

- **Right now**, refreshed every 30 seconds: active sessions (users whose app was open in the last
  2 minutes), answers being generated at this moment, questions in the last hour, and a chart of
  active sessions over the last 6 or 24 hours.
- **Users** for 7, 30 or 90 days: total accounts, users active each day, new sign-ups per day.
- **Topics**: share of each router topic and a stacked chart per day.

Every logged-in, visible tab sends `POST /heartbeat` once a minute (`src/hooks/useHeartbeat.js`), so
"active sessions" counts people with the app open, not only people typing. Charts use Recharts and
load only with the admin pages.

### Advertisers

`#/admin/ads`: admins add advertisers, check them and decide. Stored in the `advertisers` table.
Nothing is shown to users yet.

- Statuses: pending review → approved / rejected; approved → suspended → reactivated; rejected → back to review.
- Approval needs every review check ticked (registration, licence for law firms, estate agents and
  insurers, website without outcome promises) and, for licensed categories, a licence number.
- Rejecting or suspending needs a reason. Editing company, registration, category, licence or website of
  an approved advertiser sends it back to review.
- Each advertiser targets topics (visas, transport, housing) that match the backend router topics.
- Categories, checks and rules: `src/lib/advertisers.js`.

Ad placements and pay-per-click billing are not designed yet.

## Model picker (mock-up)

The composer has a model menu with two options: GPT-5 (default) and Claude (Opus 5, Pro only).
The list lives in `src/lib/models.js`; the choice is remembered per user and shown under each answer.
The selected id is sent to `/ask` as `model`, but the current server ignores it and always uses its own
OpenAI model. To make the choice real, route `/ask` to the matching provider SDK by that id.

## Registration consent

After the registration form is filled in, a dialog shows the service notice (information service, not
legal advice, no legal responsibility). The account is created only after the user ticks the checkbox and
clicks "Agree and create account". Text and version live in `src/lib/consent.js`.

The accepted version is sent to `POST /users` as `consent`; the server stores it in
`users.consent_version` with the time of registration.

## Paid access (mock-up)

Free users get `FREE_DAILY_LIMIT` answered questions per day (5 by default). A question counts only
after the backend answers it, so failed requests are free. At 3 remaining the composer shows a warning;
at 0 it is replaced by an upgrade prompt.

- `src/lib/plans.js` holds the limit, prices and plan features.
- `src/hooks/useSubscription.js` tracks the plan and today's usage.
- `src/components/UpgradeDialog.jsx` is the plans, checkout, success and manage-subscription flow.
  The checkout is a demo: nothing is charged and card details never leave the page.

The plan and the counter are stored in the browser (`localStorage`), so this is a UI mock-up, not
enforcement: clearing site data resets the counter. For real paid access, the backend has to count
messages in `/ask`, return 402 when the limit is reached, and store subscriptions coming from a payment
provider's webhook (e.g. Stripe Checkout).

## Sessions

`/login` and `/users` return a token that the client sends as `Authorization: Bearer …`.
When the server answers 401 (token expired, 7 days) or 403 with `code: "banned"`, the app logs out
and shows the reason on the login screen. Chat names and deletions are stored on the server.
