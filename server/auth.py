import os
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Body, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .db import get_connection
from .schemas import JWTPayload
from .utils import cookie_kwargs, parse_bool


router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "dev")


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


def _issue_token(uid: int, username: str, name: str) -> str:
    payload: JWTPayload = {"uid": uid, "username": username, "name": name}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
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


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=72)


@router.post("/api/auth/register")
def register(body: RegisterBody, response: Response):
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM users WHERE username = ?", (body.username,)).fetchone()
    if exists:
        return JSONResponse(status_code=409, content={"error": "用户名已注册"})
    hash_ = _hash_password(body.password)
    cur.execute(
        "INSERT INTO users (username, password_hash, name) VALUES (?, ?, ?)",
        (body.username, hash_, body.name),
    )
    conn.commit()
    uid = int(cur.lastrowid)
    token = _issue_token(uid, body.username, body.name)
    response.set_cookie("token", token, **cookie_kwargs())
    return {"user": {"id": uid, "username": body.username, "name": body.name}}


@router.post("/api/auth/login")
def login(body: LoginBody, response: Response):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM users WHERE username = ?", (body.username,)).fetchone()
    if not row:
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
    if not _verify_password(body.password, row["password_hash"]):
        return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
    token = _issue_token(int(row["id"]), row["username"], row["name"]) 
    response.set_cookie("token", token, **cookie_kwargs())
    return {"user": {"id": int(row["id"]), "username": row["username"], "name": row["name"]}}


@router.post("/api/auth/logout")
def logout(response: Response):
    # Clear cookie by setting max_age=0 with same attributes
    ck = cookie_kwargs()
    ck["max_age"] = 0
    response.set_cookie("token", value="", **ck)
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request):
    payload = get_current_user(request)
    if not payload:
        return {"user": None}
    return {"user": {"id": int(payload["uid"]), "username": payload["username"], "name": payload["name"]}}
