# AGENTS Guide for MSUT 主站

Scope: This AGENTS.md applies to the entire repository.

## Backend Overview
- The backend has been fully migrated to Python/FastAPI. Do NOT re-enable the legacy Node/Express implementation under `server/src` or `server/dist`.
- App entry: `server/app.py`
- Routes: defined in `server/auth.py`, `server/files.py`, and `server/melsave.py`
- DB/migrations: `server/db.py` (SQLite, file at `server/data.sqlite`)
- Static uploads: `server/uploads/` mounted at `/uploads`
- Utilities: `server/utils.py` (cookie options, boolean env parsing, slug/nanoid)

## API Compatibility Requirements
- Keep all existing paths, methods, query/body semantics, and response JSON identical to the current FastAPI implementation (which mirrors the previous TS backend):
  - Auth: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
  - Protected ping: `GET /api/private/ping`
  - Resources: `GET /api/resources`, `POST /api/resources`, `GET /api/resources/:slug`, `PATCH /api/resources/:id`, `DELETE /api/resources/:id`
  - Files: `POST /api/files/upload`, `GET /api/files/:id/download`
- Error shape must be `{ error: string }` (not `{ detail: ... }`).
- Cookie name must remain `token`. Use `utils.cookie_kwargs()` to preserve `SameSite`/`Secure` parity with env flags.
- Download responses must set `Content-Disposition` with UTF-8 filename* percent-encoding.

Additional tool routes (non-breaking additions):
- DSL generator (anonymous): `POST /api/melsave/generate` with JSON `{ dsl: string }` returns a `.melsave` file stream with UTF‑8 filename header.
- File likes (authenticated):
  - `GET /api/files/likes?ids=1,2,3` → `{ items: [{ id, likes, liked }] }`
  - `POST /api/files/:id/like` → like a file (idempotent)
  - `DELETE /api/files/:id/like` → remove like

## Environment & Config
- `PORT` (dev 3000, Docker 3400), `JWT_SECRET`, `NODE_ENV`, `PUBLIC_BASE_URL`, `HTTPS_ENABLED`, `COOKIE_DOMAIN`.
- HSTS should only apply if `HTTPS_ENABLED` evaluates to true (see `utils.parse_bool`).
- DB and uploads are relative to `server/` and must not be relocated without updating the Docker volumes and README.

## Local Development
- Backend: `python -m uvicorn server.app:app --reload --port 3000` (or `npm run dev:server`).
- Frontend: `npm run dev:client` (Vite proxies `/api` to `http://localhost:3000`).
- Quick verifications (not production tests):
  - `python server/_smoke.py` – basic `/api/auth/me` check
  - `python server/_test_auth.py` – register/login/logout
  - `python server/_test_files.py` – resources + upload

## Docker & Nginx
- `Dockerfile` runs FastAPI via Uvicorn and serves frontend via Nginx.
- `docker-compose.yml` exposes 1122 (web) and 3400 (API) and performs healthcheck on `http://localhost:3400/api/auth/me`.
- If you change ports or mount points, update both Dockerfile, compose and README consistently.

## Coding Conventions
- Python 3.11+. Keep dependencies minimal; prefer stdlib where possible.
- Keep changes surgical and avoid breaking API compatibility. Do not rename routes, cookie names, or response fields.
- Database operations should continue to use SQLite with `sqlite3` and the existing schema.
- File uploads must:
  - Accept multipart form field name `files`, up to 10 files, with a 50MB per-file limit.
  - Store files under `server/uploads` and record metadata in `resource_files`.
  - Preserve URL path format: `/uploads/<stored_name>`.

## Documentation & Changes
- When introducing new configuration, routes, or behavior, update:
  1) README (usage, env vars, deployment)
  2) This AGENTS.md (for future agent contributors)
- Do not remove legacy TS files unless explicitly requested; they may help future diffs. They are not executed.

## Safety & Security
- Always use `utils.cookie_kwargs()` for auth cookies to ensure cross-site cookie behavior is correct behind reverse proxies.
- Avoid leaking secrets into logs. Keep error responses generic where appropriate.

## Questions
If you’re unsure about API parity or behavior, prefer maintaining the current FastAPI implementation’s behavior and return shapes, and leave a short note in PR/commit messages (or open an issue) before making behavioral changes.
