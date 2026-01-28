import os
import time
import secrets
import hashlib
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Body, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .db import get_connection
from .schemas import JWTPayload
from .utils import cookie_kwargs, parse_bool, nanoid, now_ms


router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "dev")
ACCESS_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60
ACCESS_TOKEN_TTL_SHORT_SECONDS = 7 * 24 * 60 * 60
REFRESH_TOKEN_TTL_SECONDS = 90 * 24 * 60 * 60

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB


def is_https_enabled() -> bool:
    is_prod = os.getenv("NODE_ENV") == "production"
    return parse_bool(os.getenv("HTTPS_ENABLED"), is_prod)


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _issue_token(uid: int, username: str, name: str, ttl_seconds: int) -> str:
    payload: JWTPayload = {
        "uid": uid,
        "username": username,
        "name": name,
        "exp": int(time.time()) + ttl_seconds,
    }
    token = jwt.encode(
        {
            "uid": uid,
            "username": username,
            "name": name,
            "exp": int(time.time()) + ttl_seconds,
        },
        JWT_SECRET,
        algorithm="HS256",
    )
    return token


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _create_refresh_token(conn, uid: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_refresh_token(token)
    expires_at = int(time.time()) + REFRESH_TOKEN_TTL_SECONDS
    conn.execute(
        "INSERT INTO auth_refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (uid, token_hash, expires_at),
    )
    return token


def _parse_token(token: Optional[str]) -> Optional[JWTPayload]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])  # type: ignore
        if not (payload.get("uid") and payload.get("username") and payload.get("name")):
            return None
        return payload  # type: ignore
    except Exception:
        return None


def get_current_user(request: Request) -> Optional[JWTPayload]:
    token = request.cookies.get("token")
    return _parse_token(token)


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=1, max_length=32)
    remember: Optional[bool] = False


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=72)
    remember: Optional[bool] = False


class ProfilePatchBody(BaseModel):
    avatarUrl: Optional[str] = Field(default=None, max_length=300)
    signature: Optional[str] = Field(default=None, max_length=200)


@router.post("/api/auth/register")
def register(body: RegisterBody, request: Request, response: Response):
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM users WHERE username = ?", (body.username,)
    ).fetchone()
    if exists:
        return JSONResponse(status_code=409, content={"error": "用户名已注册"})
    hash_ = _hash_password(body.password)
    cur.execute(
        "INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)",
        (body.username, hash_, body.name),
    )
    conn.commit()
    last_id = cur.lastrowid
    if last_id is None:
        return JSONResponse(status_code=500, content={"error": "注册失败"})
    uid = int(last_id)
    remember = bool(body.remember)
    token_ttl = ACCESS_TOKEN_TTL_SECONDS if remember else ACCESS_TOKEN_TTL_SHORT_SECONDS
    token = _issue_token(uid, body.username, body.name, token_ttl)
    response.set_cookie("token", token, **cookie_kwargs(max_age_seconds=token_ttl))
    if remember:
        refresh_token = _create_refresh_token(conn, uid)
        response.set_cookie(
            "refresh_token",
            refresh_token,
            **cookie_kwargs(max_age_seconds=REFRESH_TOKEN_TTL_SECONDS),
        )
    else:
        refresh_cookie = request.cookies.get("refresh_token")
        if refresh_cookie:
            try:
                conn.execute(
                    "DELETE FROM auth_refresh_tokens WHERE token_hash = ?",
                    (_hash_refresh_token(refresh_cookie),),
                )
                conn.commit()
            except Exception:
                pass
        ck = cookie_kwargs(max_age_seconds=0)
        response.set_cookie("refresh_token", value="", **ck)
    return {"user": {"id": uid, "username": body.username, "name": body.name}}


@router.post("/api/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM users WHERE username = ?", (body.username,)
    ).fetchone()
    if not row:
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
    if not _verify_password(body.password, row["password_hash"]):
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
    remember = bool(body.remember)
    token_ttl = ACCESS_TOKEN_TTL_SECONDS if remember else ACCESS_TOKEN_TTL_SHORT_SECONDS
    token = _issue_token(int(row["id"]), row["username"], row["name"], token_ttl)
    response.set_cookie("token", token, **cookie_kwargs(max_age_seconds=token_ttl))
    if remember:
        refresh_token = _create_refresh_token(conn, int(row["id"]))
        response.set_cookie(
            "refresh_token",
            refresh_token,
            **cookie_kwargs(max_age_seconds=REFRESH_TOKEN_TTL_SECONDS),
        )
    else:
        refresh_cookie = request.cookies.get("refresh_token")
        if refresh_cookie:
            try:
                conn.execute(
                    "DELETE FROM auth_refresh_tokens WHERE token_hash = ?",
                    (_hash_refresh_token(refresh_cookie),),
                )
                conn.commit()
            except Exception:
                pass
        ck = cookie_kwargs(max_age_seconds=0)
        response.set_cookie("refresh_token", value="", **ck)
    return {
        "user": {
            "id": int(row["id"]),
            "username": row["username"],
            "name": row["name"],
            "avatarUrl": row["avatar_url"] or "",
            "signature": row["signature"] or "",
        }
    }


@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    # Clear cookie by setting max_age=0 with same attributes
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM auth_refresh_tokens WHERE token_hash = ?",
                (_hash_refresh_token(refresh_token),),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
    ck = cookie_kwargs(max_age_seconds=0)
    response.set_cookie("token", value="", **ck)
    response.set_cookie("refresh_token", value="", **ck)
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request):
    payload = get_current_user(request)
    if not payload:
        return {"user": None}
    if not isinstance(payload, dict):
        return {"user": None}
    uid = payload.get("uid")
    if uid is None:
        return {"user": None}
    
    # Fetch latest details from DB
    conn = get_connection()
    row = conn.execute(
        "SELECT id, username, name, avatar_url, signature FROM users WHERE id = ?",
        (int(uid),),
    ).fetchone()
    
    if not row:
        return {"user": None}

    return {
        "user": {
            "id": int(row["id"]),
            "username": row["username"],
            "name": row["name"],
            "avatarUrl": row["avatar_url"] or "",
            "signature": row["signature"] or "",
        }
    }


@router.post("/api/auth/refresh")
def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        return JSONResponse(status_code=401, content={"error": "需要重新登录"})
    token_hash = _hash_refresh_token(refresh_token)
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT user_id, expires_at FROM auth_refresh_tokens WHERE token_hash = ?",
        (token_hash,),
    ).fetchone()
    if not row:
        ck = cookie_kwargs(max_age_seconds=0)
        response.set_cookie("refresh_token", value="", **ck)
        return JSONResponse(status_code=401, content={"error": "登录已过期"})
    now = int(time.time())
    if int(row["expires_at"]) <= now:
        cur.execute(
            "DELETE FROM auth_refresh_tokens WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
        ck = cookie_kwargs(max_age_seconds=0)
        response.set_cookie("refresh_token", value="", **ck)
        return JSONResponse(status_code=401, content={"error": "登录已过期"})

    user = cur.execute(
        "SELECT id, username, name, avatar_url, signature FROM users WHERE id = ?",
        (int(row["user_id"]),),
    ).fetchone()
    if not user:
        cur.execute(
            "DELETE FROM auth_refresh_tokens WHERE token_hash = ?", (token_hash,)
        )
        conn.commit()
        ck = cookie_kwargs(max_age_seconds=0)
        response.set_cookie("refresh_token", value="", **ck)
        return JSONResponse(status_code=401, content={"error": "用户不存在"})

    new_refresh = secrets.token_urlsafe(32)
    new_hash = _hash_refresh_token(new_refresh)
    new_expires = now + REFRESH_TOKEN_TTL_SECONDS
    cur.execute(
        """
        UPDATE auth_refresh_tokens
        SET token_hash = ?, expires_at = ?, last_used_at = datetime('now')
        WHERE token_hash = ?
        """,
        (new_hash, new_expires, token_hash),
    )
    conn.commit()

    token = _issue_token(
        int(user["id"]), user["username"], user["name"], ACCESS_TOKEN_TTL_SECONDS
    )
    response.set_cookie(
        "token", token, **cookie_kwargs(max_age_seconds=ACCESS_TOKEN_TTL_SECONDS)
    )
    response.set_cookie(
        "refresh_token",
        new_refresh,
        **cookie_kwargs(max_age_seconds=REFRESH_TOKEN_TTL_SECONDS),
    )
    return {
        "user": {
            "id": int(user["id"]),
            "username": user["username"],
            "name": user["name"],
            "avatarUrl": user["avatar_url"] or "",
            "signature": user["signature"] or "",
        }
    }


@router.get("/api/auth/profile")
def get_profile(request: Request):
    payload = get_current_user(request)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    uid = payload.get("uid")
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, username, name, avatar_url, signature FROM users WHERE id = ?",
        (int(uid),),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    return {
        "user": {
            "id": int(row["id"]),
            "username": row["username"],
            "name": row["name"],
            "avatarUrl": row["avatar_url"] or "",
            "signature": row["signature"] or "",
        }
    }


@router.patch("/api/auth/profile")
def patch_profile(request: Request, body: ProfilePatchBody = Body(default=ProfilePatchBody())):
    payload = get_current_user(request)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    uid = payload.get("uid")
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    updates = []
    params = []
    if body.avatarUrl is not None:
        updates.append("avatar_url = ?")
        params.append(body.avatarUrl)
    if body.signature is not None:
        updates.append("signature = ?")
        params.append(body.signature)
    if not updates:
        return JSONResponse(status_code=400, content={"error": "没有可更新的字段"})

    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            (*params, int(uid)),
        )
        conn.commit()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "更新失败"})

    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, username, name, avatar_url, signature FROM users WHERE id = ?",
        (int(uid),),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    return {
        "user": {
            "id": int(row["id"]),
            "username": row["username"],
            "name": row["name"],
            "avatarUrl": row["avatar_url"] or "",
            "signature": row["signature"] or "",
        }
    }


@router.post("/api/auth/avatar/upload")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    payload = get_current_user(request)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    uid = payload.get("uid")
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    ct = (file.content_type or "").lower()
    if not ct.startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "只支持图片文件"})

    orig = file.filename or "avatar"
    ext = Path(orig).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        # best-effort infer extension from content-type
        if ct.endswith("png"):
            ext = ".png"
        elif ct.endswith("jpeg") or ct.endswith("jpg"):
            ext = ".jpg"
        elif ct.endswith("gif"):
            ext = ".gif"
        elif ct.endswith("webp"):
            ext = ".webp"
        else:
            ext = ".png"

    stored_name = f"avatar-{int(uid)}-{now_ms()}-{nanoid()}{ext}"
    tmp = UPLOAD_DIR / f"{stored_name}.part"
    dest = UPLOAD_DIR / stored_name
    size = 0
    try:
        with tmp.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_AVATAR_SIZE:
                    try:
                        tmp.unlink(missing_ok=True)  # type: ignore[arg-type]
                    except Exception:
                        pass
                    return JSONResponse(status_code=413, content={"error": "头像文件过大（最大 5MB）"})
                f.write(chunk)
        tmp.replace(dest)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass
        return JSONResponse(status_code=500, content={"error": "上传失败"})

    avatar_url = f"/uploads/{stored_name}"
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET avatar_url = ? WHERE id = ?",
            (avatar_url, int(uid)),
        )
        conn.commit()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "保存失败"})
    return {"avatarUrl": avatar_url}
