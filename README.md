# FamousRelatives

A browser extension that uses your FamilySearch tree to find how you're related to a curated list of famous people, and shows each relationship path as a card and a graph.

## Why this project
FamilySearch's own "Famous Relatives" feature uses a small, generic list. This project lets you curate **your own list** of culturally relevant people (here, mostly Uruguayan and regional figures), so the results mean more to you and your family.

It's also a practice project in working with an external API (rate limits, retries, caching) and in AI-assisted development: much of the code was written with [Claude Code](https://claude.com/claude-code), with a human reviewing design, security and commits.

## How it works
```
 Browser extension ──── FamilySearch API (with the user's own session)
        │
        ├── IndexedDB (results, per FamilySearch account, stays on the computer)
        │
        └── Supabase (read-only list of famous people + categories)
```

1. **Login:** the extension reads the `fssessionid` cookie of the FamilySearch session already open in the browser and sends it as a Bearer token. No password or token capture needed. If there's no session, it asks the user to log in and continues automatically.
2. **Famous people list:** downloaded from Supabase on every open (last copy kept for offline use).
3. **Search:** for each person, the extension asks FamilySearch for the relationship path, 2 at a time, one request every 0.2 s, retrying on 429/5xx. If the path goes through a spouse, it also looks for a blood path through one of the person's parents.
4. **Cache:** each result (including "no relationship") is stored in IndexedDB and never expires. Only new people in the list are searched; "Actualizar mis árboles" re-searches everyone (at most once every 5 minutes).
5. **Dashboard:** cards with filters (category, country, closeness, ancestor branch, in-law relationships), a graph popup per person, and a button to download everything as a standalone HTML file.

## Project structure
```
extension/                  # The app (Chrome / Edge / Brave, Manifest V3)
├── manifest.json, background.js, app.html
├── config.js               # Supabase URL + public read-only key
├── INSTALAR.md             # Install guide for non-technical users (Spanish)
└── js/
    ├── app.js              # Startup, progress, actions menu
    ├── session.js          # FamilySearch login detection
    ├── fs-api.js           # FamilySearch requests (rate limit, retries)
    ├── trees.js            # Relationship parsing + caching
    ├── store.js            # IndexedDB
    ├── famosos.js          # Supabase list + offline copy
    └── main.js, switch.js, card.js, popup.js, graph.js, ...  # Dashboard UI
supabase/schema.sql         # Tables + read-only policies
supabase/seed.sql           # Generated from famosos.csv
famosos.csv                 # Source list of famous people
scripts/
├── seed_supabase.py        # famosos.csv → supabase/seed.sql
└── build-extension.ps1     # extension/ → dist/famousrelatives-extension.zip
reference/                  # Example FamilySearch API responses
```

## Usage

### Install (for family members)
Share `dist/famousrelatives-extension.zip` together with [extension/INSTALAR.md](extension/INSTALAR.md): unzip, open `chrome://extensions`, enable Developer mode, "Load unpacked". Code updates require replacing the folder and pressing reload (↻); list updates arrive automatically.

### Edit the famous people list
In the Supabase dashboard → **Table Editor**:
- `famosos`: `person_code` (FamilySearch ID), `name`, `info`, `topics` (categories), `paises`, `wiki`.
- `categorias`: optional description shown when a category is selected (HTML allowed).

Removing someone from `famosos` hides them from everyone's dashboard. To bulk-load from the CSV instead: `python scripts/seed_supabase.py`, then run `supabase/seed.sql` in the SQL Editor (it inserts/updates, it doesn't delete).

### Develop
1. Load `extension/` with "Load unpacked" and press reload (↻) after each change.
2. Build the shareable zip: `powershell -File scripts\build-extension.ps1`.
3. Lint: `npm install` once, then `npm run lint` (ESLint). CI also runs pytest/flake8 and a secret scan (gitleaks) on every push.

## Privacy & security
- The FamilySearch session never leaves the browser; results are stored only in the user's IndexedDB.
- The Supabase key in `config.js` is the public anon key: Row Level Security allows reading only (no inserts, updates or deletes).
- `examples/` (exported family trees) and `.env` are gitignored: they contain private data.

## Legacy: local Flask version
The original version is still in the repo: a Flask app (`app.py`, `templates/`, `static/`), a local proxy (`fs_proxy.py`), a Node token capturer (`listener/`, via Chrome DevTools Protocol) and a MySQL cache (`db/`, in Docker). The extension replaces all of it; `trees.js` and `fs-api.js` are ports of `services/tree_functions.py` and `fs_proxy.py`.

To run it on Windows: create a `.env` (`SECRET_KEY`, `DB_*`, browser headers; see `app.py` and `fs_proxy.py`), then run `start-system.bat` (starts MySQL, proxy and Flask, opens `http://localhost:5000`). Stop it with `stop-system.bat`. It reads the list from `famosos.csv`, not Supabase.

## Tech stack
JavaScript (Manifest V3 extension, IndexedDB) · vis-network (graphs) · Supabase (Postgres) · Python (seed script, legacy Flask app) · GitHub Actions (tests)

## Roadmap
- [x] Timeouts, retries and rate limiting for FamilySearch calls
- [x] Per-account cache, viewer portrait, category/country/ancestor filters
- [x] Browser extension: no local server, no token capture, list in Supabase
- [ ] Remove the legacy Flask version once the extension is confirmed
