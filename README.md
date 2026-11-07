# FamousRelatives

A small web app that uses the FamilySearch API to compute and visualize relationship paths between a user and a curated list of historically/culturally significant people.

*Focus:* API integration, reliability patterns (timeouts/retries), caching to reduce external calls, and containerized deployment (Docker).

## Why this project
The original FamilySearch "Famous Relatives" feature is intentionally limited and subjective, with a small, non-controversial list of historically important people.

This project was created to explore an alternative approach:
allowing users to define their *own curated lists of culturally relevant figures*, with a regional or personal focus, making the experience more meaningful and engaging.

At the same time, the project was designed to practice real-world backend challenges, including:
- Working with an external API (latency, failures, rate limits)
- Reducing request volume via caching to protect upstream services
- Handling transient errors safely (timeouts, retries, clear error messages)
- Shipping a reproducible environment using Docker

The result is a product-driven idea combined with real engineering constraints.

## AI-assisted development
This is also a practice project for working with AI coding tools — especially [Claude Code](https://claude.com/claude-code). Much of the code, refactoring, debugging and documentation was done in collaboration with Claude Code, as a way to build hands-on skills in:
- Describing features and bugs clearly so an AI agent can act on them
- Reviewing, testing and correcting AI-generated changes
- Using an agent for multi-file refactors, UI tweaks and documentation
- Keeping a human in the loop for design decisions, security and commits

## Project structure
```
famousrelatives/
├── app.py                  # Flask web server + routes (accounts, token capture, tree processing)
├── fs_proxy.py             # Local proxy for FamilySearch API (rate limiting, retries)
├── famosos.csv             # Curated list of person IDs + display info
├── docker-compose.yml      # Local environment orchestration (MySQL only)
├── Dockerfile              # App container definition
├── start-system.bat        # One-click startup script (Windows)
├── db/                     # DB initialization + cache/account schema
├── listener/               # Node script that captures the FamilySearch session token via CDP
├── services/               # Business logic
│   ├── tree_functions.py   # Relationship fetching, parsing, caching
│   ├── cards.py
│   ├── csv_validation.py
│   └── validators.py
├── static/
├── templates/
│   ├── login.html            # Sign-in page: opens FamilySearch via the token capturer
│   ├── dashboard_header.html # Logged-in header: token status + actions menu
│   ├── plantilla_arboles.html # Main results page (cards + graph)
│   └── loading.html
└── reference/               # Example FamilySearch API responses (for development)
```

## Browser extension (recommended for family use)
`extension/` is a self-contained Chrome/Edge/Brave extension that replaces the whole local stack (Flask, proxy, token listener, MySQL, Docker):
- **Login:** reads the `fssessionid` cookie of the FamilySearch session already open in the browser (no capture script).
- **API calls:** made directly from the extension with that session as a Bearer token (no proxy). Same rate limiting and retries as `fs_proxy.py`.
- **Cache:** IndexedDB in each user's browser, per FamilySearch account. Family data never leaves the computer.
- **Famous people list:** read-only from Supabase (`famosos` and `categorias` tables, see `supabase/schema.sql`). Edit the list in the Supabase Table Editor and everyone gets it on the next open.

```
extension/
├── manifest.json, background.js, app.html, config.js (Supabase URL + public anon key)
└── js/
    ├── fs-api.js    # FamilySearch requests (port of fs_proxy.py)
    ├── trees.js     # relationship parsing/caching (port of services/tree_functions.py)
    ├── store.js     # IndexedDB (replaces db/db.py)
    ├── famosos.js   # Supabase list + offline copy
    ├── session.js   # FamilySearch login detection
    └── app.js       # startup, progress, actions menu (replaces app.py)
```

- Build the zip to share: `powershell -File scripts\build-extension.ps1` → `dist\famousrelatives-extension.zip`.
- Install steps for non-technical users: `extension/INSTALAR.md`.
- Load the famous people list into Supabase from `famosos.csv`: `python scripts/seed_supabase.py`, then run `supabase/seed.sql` in the Supabase SQL editor.

## Setup (local Flask version)

### Requirements
- Python 3.10+
- Node.js (for the token listener)
- Docker (for MySQL only)

### Environment variables
Create a `.env` file in the project root (never commit it):
```
SECRET_KEY=some_random_secret        # required for Flask session cookies
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=famousrelatives
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...
SEC_CH_UA='"Chromium";v="148", "Brave";v="148", "Not/A)Brand";v="99"'
SEC_CH_UA_MOBILE=?0
SEC_CH_UA_PLATFORM="Windows"
SEC_GPC=1
SEC_FETCH_SITE=same-origin
RATE_LIMIT_INTERVAL=0.2   # seconds between FamilySearch requests per token
MAX_RETRIES_429=3         # retries after a 429 (honoring Retry-After)
MAX_WORKERS=2             # people processed in parallel
BRAVE_PATH=C:\Users\you\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe  # optional, used by the in-app token capturer
```
Use your browser's DevTools (Network tab) to capture the correct `User-Agent` and `sec-ch-ua` values for your browser version.

### Starting the app (Windows)
```
start-system.bat
```
This launches the MySQL container, the local FamilySearch proxy, and the Flask app in separate windows, then opens the browser directly on `http://localhost:5000/` — the site's own login page. It does **not** touch FamilySearch on startup; the FamilySearch session token is only captured on demand (see below). Running it again at any time first stops any previously-running instance of this project (Flask app, proxy, listener, capture browser) before relaunching, so re-running it never stacks up duplicate processes.

### Stopping the app (Windows)
```
stop-system.bat
```
Stops everything belonging to this project: `app.py` (both the Werkzeug reloader parent and worker, whether launched from the venv or a global `python` on PATH), `fs_proxy.py`, any running `node listen.js`, and the app's Brave window (matched by the `--remote-debugging-port=9222` flag or the `chrome_debug_profile` folder). Safe to run even if nothing is currently running.

### Manual startup
```bash
# 1. Start MySQL
docker-compose up -d db

# 2. Start proxy (separate terminal)
venv\Scripts\activate
python fs_proxy.py

# 3. Start Flask app (separate terminal)
venv\Scripts\activate
python app.py
```

## Core workflow
1. The user signs in with FamilySearch: the sign-in page runs the token capturer automatically (or accepts a pasted token). The app asks FamilySearch who owns the token (`/platform/users/current`) and uses that FamilySearch person ID as the app account. There is no separate username or password. The capturer can be run again from the dashboard's settings menu when the token expires.
   - `start-system.bat` opens the app in Brave with the DevTools port 9222 and its own profile (`chrome_debug_profile`). Running the capturer opens FamilySearch in a new tab of that same window; a listener grabs the session token via Chrome DevTools Protocol once the user logs in (instantly if already logged in), closes that tab and switches back to the app. If that browser isn't running, the capturer opens it. Each click first stops any leftover listener from a previous attempt.
3. App loads a CSV with a curated list of FamilySearch person IDs.
4. Person IDs are processed in parallel in the background (`MAX_WORKERS`, default 2):
   - Check cache (no automatic expiry) to avoid repeated API calls.
   - If not cached: call FamilySearch relationship endpoint via local proxy.
   - Normalize/parse the relationship path to a consistent format.
5. The first worker to resolve a person fetches the viewer's own portrait via the FamilySearch portrait endpoint; all workers then apply it to their trees.
6. The dashboard opens right away and polls `/progress`; each tree appears as soon as it's saved.

## Authentication & Security
- There are no app passwords: an account is a row in `usuarios` keyed by the FamilySearch person ID (`viewer_person_id`), created on first sign-in. `username` and `password_hash` are unused leftovers kept because the columns are NOT NULL.
- Signing out clears the session and the captured token in `.env`, and the sign-in page doesn't reopen FamilySearch on its own after that.
- The FamilySearch token is **never persisted server-side** (not in the DB, not on disk beyond the brief capture hand-off below). It lives only in the browser's Flask session cookie, so it disappears when the browser closes or the user logs out — every new session needs a fresh capture or paste.
- The FamilySearch token is only captured on demand — from the sign-in page or the "Ejecutar capturador de token" action, never on startup — which opens FamilySearch in a new tab of the app's browser and runs a listener (CDP) that writes the captured token to `.env`. The next `/capture-status` poll from that browser reads it from `.env` and stores it in that browser's session only.
- Only one capture can run at a time (shared Chrome debug profile), so usage across accounts must be sequential.
- The `.env` file is gitignored — never commit it.
- Note: the `usuarios` table still has unused `familysearch_token`/`token_updated_at` columns left over from an earlier DB-persisted design; they're dead schema now, kept rather than dropped to avoid an unprompted destructive migration.

*Recommendation (production):*
- Use server-side session storage and secure cookies
- Add input validation for CSV uploads

## Performance & caching
To reduce the number of calls to FamilySearch (and speed up repeated queries), the app stores results in a DB cache.

- Cache key: `(persona_id, user_id)` — each account gets its own cached results
- No automatic expiry: a cached result (found or not) is reused indefinitely once written. It's only bypassed by "Actualizar todo" (`force_refresh`), or naturally missed for a `person_code` with no cached row yet for that account (e.g. newly added to `famosos.csv`).
- Goal: fewer upstream requests, lower latency, better UX

The local proxy (`fs_proxy.py`) adds an additional layer: per-token request spacing and automatic retry with `Retry-After` on HTTP 429 responses. If the logs show `429 — waiting`, raise `RATE_LIMIT_INTERVAL` or lower `MAX_WORKERS`.

MySQL connections use a pool (`pool_size=10`) initialized once at startup, eliminating per-query TCP handshake overhead.

## Tech stack
- Python / Flask (backend + API client + parsing)
- HTML/CSS (server-rendered templates)
- vis.js (relationship graph)
- MySQL (cache)
- Docker + docker-compose (MySQL only; app runs locally). `docker-compose.yml`'s `app` service is opt-in only (`docker-compose --profile containerized up`) and isn't part of the documented local dev flow — a bare `docker-compose up` never starts it, to avoid a second `app.py` fighting the host-run one for port 5000.
- Node.js (browser token listener)

## Roadmap
- [x] Add default timeouts + safe retries for API calls
- [x] Add input validation + CSV schema checks
- [x] Add basic rate limiting (per session)
- [x] Add tests for parsing/normalization utilities
- [x] Add CI (GitHub Actions) to run tests and linting
- [x] Get token automatically
- [x] Show viewer's own profile picture
- [x] Multi-user accounts, each with its own cached trees
- [x] Token capture is opt-in (triggered from the UI), not forced before site login
- [x] FamilySearch token is session-only, never persisted server-side