import os
import logging
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_from_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue
                os.environ.setdefault(key, value)
    except Exception:
        # 环境变量加载失败时静默忽略，避免影响主流程
        pass


# 在导入其余模块前优先加载根目录和 server 目录下的 .env，
# 以便 JWT / RAG 等配置在模块级读取时已生效。
_load_env_from_file(BASE_DIR / ".env")
_load_env_from_file(BASE_DIR / "server" / ".env")


from .auth import router as auth_router, get_current_user, is_https_enabled
from .db import run_migrations, DB_FILE
from .files import router as files_router
from .melsave import router as melsave_router
from .tutorials import router as tutorials_router


app = FastAPI()


# Run DB migrations at startup
@app.on_event("startup")
def _startup():
    # Basic logging config; adjustable via LOG_LEVEL env (default INFO)
    lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        logging.basicConfig(level=getattr(logging, lvl, logging.INFO))
    except Exception:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("msut.app")
    run_migrations()
    try:
        logger.info("startup complete: DATA_DIR=%s DB=%s HTTPS_ENABLED=%s", os.getenv("DATA_DIR"), str(DB_FILE), os.getenv("HTTPS_ENABLED"))
    except Exception:
        pass


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
app.include_router(tutorials_router)


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
