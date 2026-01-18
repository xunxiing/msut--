# AGENTS Guide for MSUT 主站

Scope: This AGENTS.md applies to the entire repository.

## Backend Overview
- The backend has been fully migrated to Python/FastAPI. Do NOT re-enable the legacy Node/Express implementation under `server/src` or `server/dist`.
- App entry: `server/app.py`
- Routes: defined in `server/auth.py`, `server/files.py`, `server/melsave.py`, `server/tutorials.py` (tutorial docs + RAG), `server/agent_api.py` (agent chat + melsave tool calls), and `server/notifications_api.py`.
- DB/migrations: `server/db.py` (SQLite, file at `server/data.sqlite`)
- Static uploads: `server/uploads/` mounted at `/uploads`
- Utilities: `server/utils.py` (cookie options, boolean env parsing, slug/nanoid)

## API Compatibility Requirements
- Keep all existing paths, methods, query/body semantics, and response JSON identical to the current FastAPI implementation (which mirrors the previous TS backend):
  - Auth: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
  - Protected ping: `GET /api/private/ping`
  - Resources: `GET /api/resources`, `POST /api/resources`, `GET /api/resources/:slug`, `PATCH /api/resources/:id`, `DELETE /api/resources/:id`
- Files: `POST /api/files/upload`, `GET /api/files/:id/download`
  - Upload accepts multipart field `files` (<=10, 50MB each). Optional form field `saveWatermark` (boolean) enables extracting a watermark from `.melsave` uploads and persisting it for later checks.
- Error shape must be `{ error: string }` (not `{ detail: ... }`).
- Cookie name must remain `token`. Use `utils.cookie_kwargs()` to preserve `SameSite`/`Secure` parity with env flags.
- Download responses must set `Content-Disposition` with UTF-8 filename* percent-encoding.

Additional tool routes (non-breaking additions):
- DSL generator (anonymous): `POST /api/melsave/generate` with JSON `{ dsl: string }` returns a `.melsave` file stream with UTF-8 filename header.
- Auth refresh (cookie-based):
  - `POST /api/auth/refresh` → refreshes access cookie using `refresh_token`, returns `{ user }` or `{ error }`.
- Resource likes (authenticated):
  - `GET /api/resources/likes?ids=1,2,3` → `{ items: [{ id, likes, liked }] }`
  - `POST /api/resources/:id/like` → like a resource (idempotent)
  - `DELETE /api/resources/:id/like` → remove like
- Notifications (authenticated):
  - `GET /api/notifications` → list notifications
  - `GET /api/notifications/unread` → latest notifications for bell preview (`total` is unread count)
  - `POST /api/notifications/read-all` → mark all notifications as read
- Watermark check (anonymous): `POST /api/watermark/check` with multipart `file` (`.melsave`/`.zip`). Returns `{ watermark, length, embedded, matches: [{ fileId, resourceId, resourceSlug, resourceTitle, originalName, urlPath }] }`.
- Tutorial management (authenticated, per-user):
 - `GET /api/my/tutorials` → `{ items: [{ id, slug, title, description, created_at, updated_at }] }`
 - `PATCH /api/tutorials/:id` → update title/description/content of a tutorial owned by the current user, and refresh its embeddings for RAG
  - `DELETE /api/tutorials/:id` → delete a tutorial owned by the current user (cascades its RAG chunks)
 - Agent chat + generation (authenticated):
  - `POST /api/agent/sessions` → create a session
  - `GET /api/agent/sessions` → list own sessions
  - `GET /api/agent/sessions/{id}/messages` → pull session history
  - `POST /api/agent/ask` → send a user message (optionally with `sessionId`), starts an async run that may call the melsave generator tool
 - `GET /api/agent/runs/{runId}` → poll run status/result (download URL for generated `.melsave`)

New resource image management (non-breaking additions):
- Resource images (authenticated, owner only):
  - `POST /api/resources/{id}/images/upload` → upload one or more image files for a resource; files are stored in `resource_files` and can be used as covers or gallery images.
  - `GET /api/resources/{id}/images` → list all image-type files under a resource (filtered by MIME/extension) plus current `coverFileId`, for cover/gallery management.

## Environment & Config
- `PORT` (dev 3000, Docker 3400), `JWT_SECRET`, `NODE_ENV`, `PUBLIC_BASE_URL`, `HTTPS_ENABLED`, `COOKIE_DOMAIN`.
- RAG / LLM (optional, for tutorial search + QA, typically via OpenAI-compatible APIs such as 硅基流动):
  - `RAG_API_BASE` – HTTP base (e.g. `https://api.siliconflow.cn/v1`).
  - `RAG_API_KEY` – API key used for both embeddings and chat.
  - `RAG_LLM_MODEL` – chat model name (e.g. `deepseek-ai/DeepSeek-V3.2-Exp`).
  - `RAG_EMBED_MODEL` – embedding model name (e.g. `BAAI/bge-m3`).
  - `RAG_EMBED_DIM` – embedding dimension (e.g. `1024`), used for sanity logging.
- Agent LLM (for multi-turn `.melsave` generation):
  - `AGENT_API_BASE`/`AGENT_API_KEY` – OpenAI-compatible gateway for the agent; defaults to the RAG values.
  - `AGENT_MODEL` – chat model used for tool calls (default filled with `moonshotai/Kimi-K2-Thinking`).
  - Prompt files live under `server/agent/全自动生成.txt` (agent guidance) and `server/agent/芯片教程.txt` (domain tutorial); the agent reads both before tool calls.
- HSTS should only apply if `HTTPS_ENABLED` evaluates to true (see `utils.parse_bool`).
- DB and uploads are relative to `server/` and must not be relocated without updating the Docker volumes and README.
  - The SQLite DB location is controlled by `DATA_DIR` (default `server/data/`) with the file `data.sqlite`. Do not change without adjusting Docker volumes and README.

## Local Development
- Backend: `python -m uvicorn server.app:app --reload --port 3000` (or `npm run dev:server`).
- Frontend: `npm run dev:client` (Vite proxies `/api` to `http://localhost:3000`).
- Quick verifications (not production tests):
  - `python server/_smoke.py` – basic `/api/auth/me` check
  - `python server/_test_auth.py` – register/login/logout
  - `python server/_test_files.py` – resources + upload

## Docker & Nginx
- `Dockerfile` builds the frontend assets and the final image runs **FastAPI via Uvicorn (port 3400)** plus a minimal Node-based static server (`serve`) that exposes the built frontend from `/app/web/dist` on **port 80** (no Nginx inside the container).
- `docker-compose.yml` exposes ports `1122:80` (frontend static files) and `3400:3400` (backend API). The container image itself includes a healthcheck on `http://localhost:3400/api/auth/me`.
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
- Auth cookies include `token` (access) and `refresh_token` (refresh, optional “记住我”); keep names stable.
- Avoid leaking secrets into logs. Keep error responses generic where appropriate.

## Questions
If you’re unsure about API parity or behavior, prefer maintaining the current FastAPI implementation’s behavior and return shapes, and leave a short note in PR/commit messages (or open an issue) before making behavioral changes.
