# FamousRelatives

A small web app that uses the FamilySearch API to compute and visualize relationship paths between a user and a curated list of historically/culturally significant people.

*Focus:* API integration, reliability patterns (timeouts/retries), caching to reduce external calls, and containerized deployment (Docker).

## Why this project
The original FamilySearch “Famous Relatives” feature is intentionally limited and subjective, with a small, non-controversial list of historically important people.

This project was created to explore an alternative approach:
allowing users to define their *own curated lists of culturally relevant figures*, with a regional or personal focus, making the experience more meaningful and engaging.

At the same time, the project was designed to practice real-world backend challenges, including:
- Working with an external API (latency, failures, rate limits)
- Reducing request volume via caching to protect upstream services
- Handling transient errors safely (timeouts, retries, clear error messages)
- Shipping a reproducible environment using Docker

The result is a product-driven idea combined with real engineering constraints.

## Demo
- Screenshot: Insert TOKEN page

- Screenshot: CSV upload + results table

## Core workflow
1. User provides a *FamilySearch access token* (not stored permanently).
2. App loads a CSV with a curated list of FamilySearch person IDs.
3. For each person ID:
   - Check cache (TTL-based) to avoid repeated API calls.
   - If not cached: call FamilySearch relationship endpoint.
   - Normalize/parse the relationship path to a consistent format.
4. Render results in the UI (and optionally persist temporary results for performance).

## Authentication & Security
- The app requires a *user-provided FamilySearch access token*.
- Tokens are *not persisted* in the database or repository.
- Tokens should be provided via *environment variables* or a local .env file (never committed).
- The app only uses the token to perform FamilySearch API requests during the session.

*Recommendation (production):*
- Use server-side session storage and secure cookies
- Add input validation for CSV uploads
- Add rate limiting and request timeouts by default

## Performance & caching
To reduce the number of calls to FamilySearch (and speed up repeated queries), the app stores results temporarily in a DB cache.

- Cache key: (user/target person ID) or (relationship query signature)
- TTL: configurable (e.g., 1h / 24h)
- Goal: fewer upstream requests, lower latency, better UX

## Tech stack
- Python (backend + API client + parsing)
- HTML/CSS (server-rendered templates)
- MySQL (temporary cache)
- Docker + docker-compose (reproducible local environment)

## Project structure
- app.py — web server + routes
- arboles_funciones.py — relationship parsing/normalization utilities
- templates/ — HTML templates
- mysql/ — DB initialization / cache schema
- docker-compose.yml — local environment orchestration
- Dockerfile — app container definition

## Roadmap
- [ ] Add default timeouts + safe retries for API calls
- [ ] Add TTL-based cache invalidation
- [ ] Add input validation + CSV schema checks
- [ ] Add basic rate limiting (per session)
- [ ] Add tests for parsing/normalization utilities
- [ ] Add CI (GitHub Actions) to run tests and linting
