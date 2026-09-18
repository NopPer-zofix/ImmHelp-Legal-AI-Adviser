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

## Paid access (mock-up)

Free users get `FREE_DAILY_LIMIT` answered questions per day (10 by default). A question counts only
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

## Known backend limitations

- **No rename or delete endpoints.** The frontend tries `PATCH /chats/:id` and `DELETE /chats/:id`;
  on 404/405 it keeps the new name, or hides the chat, in this browser only. Add a `title` column and
  those two routes and the frontend uses them automatically (it also reads `title` from `GET /chats/:user_id`).
- **No authentication tokens.** `/login` returns the user object and later requests only pass `user_id`.
  Anyone who can reach the API can read other users' chats. Add JWT or session cookies before deploying.
