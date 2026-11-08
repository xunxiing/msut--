import os
import time
import secrets
import hmac
import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, Request, Query, Body
from fastapi.responses import JSONResponse

from .db import get_connection, DB_FILE
from . import storage as r2
from .files import _calc_daily_score, _share_url, UPLOAD_DIR
from .llm2 import tags_from_json

logger = logging.getLogger("msut.admin")

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _get_admin_password() -> str:
    pwd = os.getenv("ADMIN_PASSWORD", "").strip()
    if not pwd:
        pwd = os.getenv("DAILY_ADMIN_PASSWORD", "").strip()
    return pwd or "msut-admin-sec-8888"


def _get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "msut-secret-admin-key-2026")


def make_admin_token() -> str:
    ts = int(time.time())
    salt = secrets.token_hex(8)
    payload = f"{ts}:{salt}"
    secret = _get_jwt_secret() + ":" + _get_admin_password()
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{ts}.{salt}.{sig}"


def verify_admin_token(token: Optional[str]) -> bool:
    if not token or not isinstance(token, str):
        return False
    parts = token.strip().split(".")
    if len(parts) != 3:
        return False
    ts_str, salt, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    # 有效期 14 天 (14 * 86400)
    if time.time() - ts > 14 * 86400:
        return False
    payload = f"{ts}:{salt}"
    secret = _get_jwt_secret() + ":" + _get_admin_password()
    expected_sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected_sig)


def is_admin(request: Request) -> bool:
    # 优先从 Header 读取
    auth_header = request.headers.get("X-Admin-Token") or request.headers.get("Authorization")
    if auth_header:
        token = auth_header.replace("Bearer ", "").strip()
        if verify_admin_token(token):
            return True

    # 其次从 Cookie 读取
    cookie_token = request.cookies.get("admin_token")
    if cookie_token and verify_admin_token(cookie_token):
        return True

    # 最后尝试 Query 参数 (方便排查或下载)
    query_token = request.query_params.get("admin_token")
    if query_token and verify_admin_token(query_token):
        return True

    return False


@router.post("/login")
def admin_login(payload: dict = Body(...)):
    pwd = str(payload.get("password") or "").strip()
    expected = _get_admin_password()
    if not expected or pwd != expected:
        return JSONResponse(status_code=401, content={"error": "管理员口令错误"})

    token = make_admin_token()
    admin_path = os.getenv("ADMIN_PATH", os.getenv("VITE_ADMIN_PATH", "/msut-manage-console")).strip()
    return {
        "ok": True,
        "token": token,
        "adminPath": admin_path,
        "message": "管理控制台身份验证成功",
    }


@router.get("/check")
def admin_check(request: Request):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "未登录或登录已失效"})
    admin_path = os.getenv("ADMIN_PATH", os.getenv("VITE_ADMIN_PATH", "/msut-manage-console")).strip()
    return {"ok": True, "adminPath": admin_path}


@router.get("/stats")
def get_admin_stats(request: Request):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足，请先输入管理密码"})

    conn = get_connection()
    cur = conn.cursor()

    # 基础指标统计
    users_count = cur.execute("SELECT COUNT(1) FROM users").fetchone()[0]
    resources_count = cur.execute("SELECT COUNT(1) FROM resources").fetchone()[0]
    files_row = cur.execute("SELECT COUNT(1), COALESCE(SUM(size), 0) FROM resource_files").fetchone()
    files_count = files_row[0] or 0
    files_size = files_row[1] or 0

    likes_count = cur.execute("SELECT COUNT(1) FROM resource_likes").fetchone()[0]
    comments_count = cur.execute("SELECT COUNT(1) FROM resource_comments").fetchone()[0]

    # 最近注册的 6 位用户
    recent_users_rows = cur.execute(
        """
        SELECT id, username, avatar_url, signature, created_at,
          (SELECT COUNT(1) FROM resources WHERE created_by = users.id) AS resource_count
        FROM users
        ORDER BY id DESC
        LIMIT 6
        """
    ).fetchall()
    recent_users = [
        {
            "id": r["id"],
            "username": r["username"],
            "avatarUrl": r["avatar_url"] or "",
            "signature": r["signature"] or "",
            "createdAt": r["created_at"],
            "resourceCount": r["resource_count"] or 0,
        }
        for r in recent_users_rows
    ]

    # 最近发布的 6 个模组
    recent_res_rows = cur.execute(
        """
        SELECT r.id, r.slug, r.title, r.created_at, r.download_count,
               u.username AS author_name,
               cf.url_path AS cover_url_path,
               (SELECT COUNT(1) FROM resource_likes rl WHERE rl.resource_id = r.id) AS likes_count,
               (SELECT COUNT(1) FROM resource_files rf WHERE rf.resource_id = r.id) AS files_count
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        LEFT JOIN resource_files cf ON cf.id = r.cover_file_id
        ORDER BY r.id DESC
        LIMIT 6
        """
    ).fetchall()
    recent_resources = [
        {
            "id": r["id"],
            "slug": r["slug"],
            "title": r["title"],
            "createdAt": r["created_at"],
            "authorName": r["author_name"] or "已注销用户",
            "coverUrl": r["cover_url_path"] or "",
            "likes": r["likes_count"] or 0,
            "filesCount": r["files_count"] or 0,
            "downloadCount": r["download_count"] or 0,
            "shareUrl": _share_url(r["slug"]),
        }
        for r in recent_res_rows
    ]

    # 系统运行环境
    db_size = 0
    try:
        if DB_FILE.exists():
            db_size = DB_FILE.stat().st_size
    except Exception:
        pass

    system_info = {
        "dbSizeBytes": db_size,
        "r2Configured": bool(os.getenv("R2_ACCOUNT_ID") and os.getenv("R2_BUCKET")),
        "r2Bucket": os.getenv("R2_BUCKET", ""),
        "r2PublicUrl": os.getenv("R2_PUBLIC_URL", ""),
        "ragConfigured": bool(os.getenv("RAG_API_KEY")),
        "ragModel": os.getenv("RAG_LLM_MODEL", ""),
        "agentModel": os.getenv("AGENT_MODEL", ""),
        "httpsEnabled": os.getenv("HTTPS_ENABLED", "false").lower() in ("true", "1", "yes"),
        "adminPath": os.getenv("ADMIN_PATH", os.getenv("VITE_ADMIN_PATH", "/msut-manage-console")).strip(),
    }

    return {
        "ok": True,
        "metrics": {
            "usersCount": users_count,
            "resourcesCount": resources_count,
            "filesCount": files_count,
            "filesSizeBytes": files_size,
            "likesCount": likes_count,
            "commentsCount": comments_count,
        },
        "recentUsers": recent_users,
        "recentResources": recent_resources,
        "systemInfo": system_info,
    }


@router.get("/resources")
def get_admin_resources(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=100),
    q: Optional[str] = Query(default=None),
    sort_by: str = Query(default="latest"),
):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    conn = get_connection()
    cur = conn.cursor()

    where_clauses = []
    params = []

    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(r.title LIKE ? OR r.description LIKE ? OR u.username LIKE ?)")
        params.extend([term, term, term])

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # 统计总数
    count_sql = f"""
        SELECT COUNT(1)
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        {where_str}
    """
    total = cur.execute(count_sql, tuple(params)).fetchone()[0]

    # 排序规则
    order_clause = "ORDER BY r.id DESC"
    if sort_by == "likes":
        order_clause = "ORDER BY likes_count DESC, r.id DESC"
    elif sort_by == "downloads":
        order_clause = "ORDER BY r.download_count DESC, r.id DESC"
    elif sort_by == "files":
        order_clause = "ORDER BY files_count DESC, r.id DESC"

    offset = (page - 1) * page_size
    query_params = list(params) + [page_size, offset]

    list_sql = f"""
        SELECT
            r.id,
            r.slug,
            r.title,
            r.description,
            r.created_at,
            r.cover_file_id,
            r.tags,
            r.download_count,
            u.id AS author_id,
            u.username AS author_name,
            cf.url_path AS cover_url_path,
            (SELECT COUNT(1) FROM resource_likes rl WHERE rl.resource_id = r.id) AS likes_count,
            (SELECT COUNT(1) FROM resource_comments rc WHERE rc.resource_id = r.id) AS comments_count,
            (SELECT COUNT(1) FROM resource_files rf WHERE rf.resource_id = r.id) AS files_count,
            (SELECT COALESCE(SUM(rf.size), 0) FROM resource_files rf WHERE rf.resource_id = r.id) AS total_size
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        LEFT JOIN resource_files cf ON cf.id = r.cover_file_id
        {where_str}
        {order_clause}
        LIMIT ? OFFSET ?
    """

    rows = cur.execute(list_sql, tuple(query_params)).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        items.append({
            "id": d["id"],
            "slug": d["slug"],
            "title": d["title"],
            "description": d["description"] or "",
            "createdAt": d["created_at"],
            "coverUrl": d["cover_url_path"] or "",
            "authorId": d["author_id"],
            "authorName": d["author_name"] or "已注销",
            "tags": tags_from_json(d.get("tags")),
            "downloadCount": d["download_count"] or 0,
            "likesCount": d["likes_count"] or 0,
            "commentsCount": d["comments_count"] or 0,
            "filesCount": d["files_count"] or 0,
            "totalSizeBytes": d["total_size"] or 0,
            "shareUrl": _share_url(d["slug"]),
        })

    return {
        "ok": True,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": items,
    }


@router.delete("/resources/{rid}")
def admin_delete_resource(request: Request, rid: int):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    conn = get_connection()
    cur = conn.cursor()

    res = cur.execute("SELECT id, title, slug FROM resources WHERE id = ?", (rid,)).fetchone()
    if not res:
        return JSONResponse(status_code=404, content={"error": "模组不存在"})

    files = cur.execute("SELECT stored_name FROM resource_files WHERE resource_id = ?", (rid,)).fetchall()

    # 级联删除关联数据
    cur.execute("DELETE FROM resource_files WHERE resource_id = ?", (rid,))
    cur.execute("DELETE FROM resource_likes WHERE resource_id = ?", (rid,))
    cur.execute("DELETE FROM resource_comments WHERE resource_id = ?", (rid,))
    cur.execute("DELETE FROM resources WHERE id = ?", (rid,))
    conn.commit()

    # 清理存储中的实体文件 (R2 / 本地)
    for f in files:
        stored = f["stored_name"]
        try:
            if "/" in stored:
                r2.delete_object(stored)
            else:
                p = UPLOAD_DIR / stored
                if p.exists():
                    p.unlink()
        except Exception as e:
            logger.warning("Admin delete: failed to remove file %s: %s", stored, e)

    return {"ok": True, "message": f"已成功删除模组: {res['title']}"}


@router.patch("/resources/{rid}")
def admin_update_resource(request: Request, rid: int, payload: dict = Body(...)):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()

    conn = get_connection()
    cur = conn.cursor()

    res = cur.execute("SELECT id FROM resources WHERE id = ?", (rid,)).fetchone()
    if not res:
        return JSONResponse(status_code=404, content={"error": "模组不存在"})

    updates = []
    params = []
    if title:
        updates.append("title = ?")
        params.append(title)
    if "description" in payload:
        updates.append("description = ?")
        params.append(description)

    if updates:
        params.append(rid)
        cur.execute(f"UPDATE resources SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()

    return {"ok": True, "message": "模组信息已更新"}


@router.get("/users")
def get_admin_users(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: Optional[str] = Query(default=None),
):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    conn = get_connection()
    cur = conn.cursor()

    where_clauses = []
    params = []
    if q and q.strip():
        term = f"%{q.strip()}%"
        where_clauses.append("(u.username LIKE ? OR u.signature LIKE ?)")
        params.extend([term, term])

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    total = cur.execute(f"SELECT COUNT(1) FROM users u {where_str}", tuple(params)).fetchone()[0]

    offset = (page - 1) * page_size
    query_params = list(params) + [page_size, offset]

    sql = f"""
        SELECT
            u.id,
            u.username,
            u.avatar_url,
            u.signature,
            u.created_at,
            (SELECT COUNT(1) FROM resources r WHERE r.created_by = u.id) AS resource_count,
            (SELECT COUNT(1) FROM resource_comments c WHERE c.user_id = u.id) AS comment_count
        FROM users u
        {where_str}
        ORDER BY u.id DESC
        LIMIT ? OFFSET ?
    """

    rows = cur.execute(sql, tuple(query_params)).fetchall()
    items = [
        {
            "id": r["id"],
            "username": r["username"],
            "avatarUrl": r["avatar_url"] or "",
            "signature": r["signature"] or "",
            "createdAt": r["created_at"],
            "resourceCount": r["resource_count"] or 0,
            "commentCount": r["comment_count"] or 0,
        }
        for r in rows
    ]

    return {
        "ok": True,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "items": items,
    }


@router.delete("/users/{uid}")
def admin_delete_user(request: Request, uid: int):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    conn = get_connection()
    cur = conn.cursor()

    user = cur.execute("SELECT id, username FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})

    # 注销用户
    cur.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()

    return {"ok": True, "message": f"用户 {user['username']} 已注销"}


@router.get("/daily")
def get_admin_daily_status(request: Request, date: Optional[str] = Query(default=None)):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    now_bj = datetime.now(timezone(timedelta(hours=8)))
    date_str = date.strip() if date and re.match(r"^\d{4}-\d{2}-\d{2}$", date.strip()) else now_bj.strftime("%Y-%m-%d")

    conn = get_connection()
    cur = conn.cursor()

    override = cur.execute(
        "SELECT hero_resource_id, picked_ids FROM daily_recommendations_override WHERE date = ?",
        (date_str,),
    ).fetchone()

    is_manual = False
    override_hero_id = None
    override_picked_ids: List[int] = []
    if override:
        is_manual = True
        override_hero_id = override["hero_resource_id"]
        try:
            override_picked_ids = [int(x) for x in json.loads(override["picked_ids"] or "[]")]
        except Exception:
            override_picked_ids = []

    # 获取全量候选列表
    rows = cur.execute(
        """
        SELECT
          r.id,
          r.slug,
          r.title,
          r.description,
          r.created_at,
          r.cover_file_id,
          r.tags,
          r.download_count,
          u.username AS author_username,
          cf.url_path AS cover_url_path,
          (SELECT COUNT(1) FROM resource_likes rl WHERE rl.resource_id = r.id) AS likes_count,
          (SELECT COUNT(1) FROM resource_files rf WHERE rf.resource_id = r.id) AS files_count
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        LEFT JOIN resource_files cf ON cf.id = r.cover_file_id
        ORDER BY r.id DESC
        """
    ).fetchall()

    candidates = []
    for row in rows:
        d = dict(row)
        rid = d["id"]
        has_cover = bool(d["cover_url_path"])
        desc_len = len(d["description"] or "")
        files_count = int(d["files_count"] or 0)
        likes = int(d["likes_count"] or 0)
        downloads = int(d["download_count"] or 0)
        score = _calc_daily_score(
            date_str,
            rid,
            has_cover=has_cover,
            desc_len=desc_len,
            files_count=files_count,
            likes=likes,
            downloads=downloads,
        )
        candidates.append({
            "id": rid,
            "slug": d["slug"],
            "title": d["title"],
            "author": d["author_username"] or "已注销",
            "coverUrl": d["cover_url_path"] or "",
            "likes": likes,
            "filesCount": files_count,
            "downloadCount": downloads,
            "dailyScore": round(score, 2),
            "shareUrl": _share_url(d["slug"]),
        })

    candidates.sort(key=lambda x: x["dailyScore"], reverse=True)

    return {
        "ok": True,
        "date": date_str,
        "isManual": is_manual,
        "heroId": override_hero_id,
        "pickedIds": override_picked_ids,
        "candidates": candidates,
    }


@router.post("/daily/override")
def admin_override_daily(request: Request, payload: dict = Body(...)):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    date_str = str(payload.get("date") or "").strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return JSONResponse(status_code=400, content={"error": "无效的日期格式 (YYYY-MM-DD)"})

    hero_id = payload.get("hero_id")
    hero_id = int(hero_id) if hero_id is not None and str(hero_id).isdigit() else None

    picked_ids = payload.get("picked_ids") or []
    if not isinstance(picked_ids, list):
        picked_ids = []
    picked_ids_clean = [int(x) for x in picked_ids if str(x).isdigit()]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO daily_recommendations_override (date, hero_resource_id, picked_ids, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(date) DO UPDATE SET
          hero_resource_id = excluded.hero_resource_id,
          picked_ids = excluded.picked_ids,
          updated_at = datetime('now')
        """,
        (date_str, hero_id, json.dumps(picked_ids_clean)),
    )
    conn.commit()
    return {"ok": True, "message": f"已成功保存 {date_str} 的推荐调度"}


@router.delete("/daily/override")
def admin_reset_daily(request: Request, date: str = Query(...)):
    if not is_admin(request):
        return JSONResponse(status_code=401, content={"error": "权限不足"})

    date_str = date.strip()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM daily_recommendations_override WHERE date = ?", (date_str,))
    conn.commit()
    return {"ok": True, "message": f"已重置 {date_str} 为算法伪随机自然轮播"}
