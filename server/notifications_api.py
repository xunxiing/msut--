from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from .auth import get_current_user
from .db import get_connection
from .notifications import build_notification_payload, _cleanup_old


router = APIRouter()


def _require_user_id(request: Request):
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        if isinstance(payload, dict) and "uid" in payload:
            return int(payload["uid"])
    except Exception:
        return None
    return None


@router.get("/api/notifications")
def list_notifications(
    request: Request,
    page: int = Query(default=1),
    pageSize: int = Query(default=20),
):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    page = max(1, int(page or 1))
    page_size = min(50, max(1, int(pageSize or 20)))
    offset = (page - 1) * page_size
    conn = get_connection()
    _cleanup_old(conn)
    total = conn.execute(
        "SELECT COUNT(1) as c FROM notifications WHERE user_id = ?",
        (uid,),
    ).fetchone()["c"]
    rows = conn.execute(
        """
        SELECT n.id, n.type, n.content, n.created_at, n.resource_id, n.comment_id, n.actor_id,
               r.slug AS resource_slug, r.title AS resource_title,
               rc.content AS comment_content,
               u.name AS actor_name, u.username AS actor_username
        FROM notifications n
        LEFT JOIN resources r ON r.id = n.resource_id
        LEFT JOIN resource_comments rc ON rc.id = n.comment_id
        LEFT JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
        LIMIT ? OFFSET ?
        """,
        (uid, page_size, offset),
    ).fetchall()
    items = [build_notification_payload(dict(r)) for r in rows]
    return {"items": items, "page": page, "pageSize": page_size, "total": int(total)}


@router.get("/api/notifications/unread")
def list_unread(request: Request):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    _cleanup_old(conn)
    total = conn.execute(
        "SELECT COUNT(1) as c FROM notifications WHERE user_id = ?",
        (uid,),
    ).fetchone()["c"]
    rows = conn.execute(
        """
        SELECT n.id, n.type, n.content, n.created_at, n.resource_id, n.comment_id, n.actor_id,
               r.slug AS resource_slug, r.title AS resource_title,
               rc.content AS comment_content,
               u.name AS actor_name, u.username AS actor_username
        FROM notifications n
        LEFT JOIN resources r ON r.id = n.resource_id
        LEFT JOIN resource_comments rc ON rc.id = n.comment_id
        LEFT JOIN users u ON u.id = n.actor_id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
        LIMIT 5
        """,
        (uid,),
    ).fetchall()
    items = [build_notification_payload(dict(r)) for r in rows]
    return {"items": items, "total": int(total)}
