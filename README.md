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

## Project structure
```
famousrelatives/
├── app.py                  # Flask web server + routes
├── fs_proxy.py             # Local proxy for FamilySearch API (rate limiting, retries)
├── famosos.csv             # Curated list of person IDs + display info
├── docker-compose.yml      # Local environment orchestration (MySQL only)
├── Dockerfile              # App container definition
├── start-system.bat        # One-click startup script (Windows)
├── db/                     # DB initialization + cache schema
├── listener/               # Browser extension that captures the session token
├── services/               # Business logic
│   ├── tree_functions.py   # Relationship fetching, parsing, caching
│   ├── cards.py
│   ├── csv_validation.py
│   └── validators.py
├── static/
├── templates/              # HTML templates
└── reference/              # Example FamilySearch API responses (for development)
```

## Setup

### Requirements
- Python 3.10+
- Node.js (for the token listener)
- Docker (for MySQL only)

### Environment variables
Create a `.env` file in the project root (never commit it):
```
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
RATE_LIMIT_INTERVAL=0.1
```
Use your browser's DevTools (Network tab) to capture the correct `User-Agent` and `sec-ch-ua` values for your browser version.

### Starting the app (Windows)
```
start-system.bat
```
This launches the MySQL container, the local FamilySearch proxy, and the Flask app in separate windows. The session token is captured automatically via the browser listener.

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
1. User opens the app — a Brave window launches and the listener captures the FamilySearch session token automatically.
2. App loads a CSV with a curated list of FamilySearch person IDs.
3. Person IDs are processed in parallel (3 concurrent workers):
   - Check cache (1-week TTL) to avoid repeated API calls.
   - If not cached: call FamilySearch relationship endpoint via local proxy.
   - Normalize/parse the relationship path to a consistent format.
4. The first worker to resolve a person fetches the viewer's own portrait via the FamilySearch portrait endpoint; all workers then apply it to their trees.
5. Render results in the UI.

## Authentication & Security
- The app requires a *user-provided FamilySearch session token*.
- Tokens are *not persisted* in the database or repository.
- The token is captured automatically from the browser session and passed in memory only.
- The `.env` file is gitignored — never commit it.

*Recommendation (production):*
- Use server-side session storage and secure cookies
- Add input validation for CSV uploads

## Performance & caching
To reduce the number of calls to FamilySearch (and speed up repeated queries), the app stores results in a DB cache.

- Cache key: `(person_id, viewer_person_id)`
- TTL: 1 week
- Goal: fewer upstream requests, lower latency, better UX

The local proxy (`fs_proxy.py`) adds an additional layer: per-token request spacing and automatic retry with `Retry-After` on HTTP 429 responses.

MySQL connections use a pool (`pool_size=10`) initialized once at startup, eliminating per-query TCP handshake overhead.

## Tech stack
- Python / Flask (backend + API client + parsing)
- HTML/CSS (server-rendered templates)
- vis.js (relationship graph)
- MySQL (cache)
- Docker + docker-compose (MySQL only; app runs locally)
- Node.js (browser token listener)

## Roadmap
- [x] Add default timeouts + safe retries for API calls
- [x] Add TTL-based cache invalidation
- [x] Add input validation + CSV schema checks
- [x] Add basic rate limiting (per session)
- [x] Add tests for parsing/normalization utilities
- [x] Add CI (GitHub Actions) to run tests and linting
- [x] Get token automatically
- [x] Show viewer's own profile picture