import os
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .auth import router as auth_router, get_current_user, is_https_enabled
from .db import run_migrations
from .files import router as files_router
from .melsave import router as melsave_router


app = FastAPI()


# Run DB migrations at startup
@app.on_event("startup")
def _startup():
    run_migrations()


# Security headers / HSTS
@app.middleware("response")
async def security_headers(request: Request, call_next: Callable):
    response: Response = await call_next(request)
    # mimic basic helmet config: HSTS enabled when https enabled
    if is_https_enabled():
        response.headers.setdefault("Strict-Transport-Security", "max-age=15552000; includeSubDomains")
    # Allow static cross-origin resource loading (disable CORP akin to helmet crossOriginResourcePolicy: false)
    # We simply do not set CORP header.
    return response


# Static files for uploads (public)
uploads_path = Path(__file__).resolve().parent / "uploads"
app.mount("/uploads", StaticFiles(directory=str(uploads_path), html=False, check_dir=True), name="uploads")


# Routers
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(melsave_router)


@app.get("/api/private/ping")
def private_ping(request: Request):
    payload = get_current_user(request)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    return {"pong": True}


# Root health for convenience
@app.get("/")
def root():
    return {"ok": True}
