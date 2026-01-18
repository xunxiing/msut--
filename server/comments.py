import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse

from .auth import get_current_user
from .db import get_connection
from .sensitive_words import filter_sensitive, load_sensitive_words
from .notifications import create_notification


router = APIRouter()
logger = logging.getLogger("msut.comments")


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        if isinstance(payload, dict) and "uid" in payload:
            return int(payload["uid"])
        return None
    except Exception:
        return None


def _load_words_cached() -> List[str]:
    if not hasattr(_load_words_cached, "_cache"):
        setattr(_load_words_cached, "_cache", load_sensitive_words())
    return getattr(_load_words_cached, "_cache")


def _mask_content(content: str) -> str:
    words = _load_words_cached()
    return filter_sensitive(content, words)


def _build_tree(items: List[Dict]) -> List[Dict]:
    nodes: Dict[int, Dict] = {}
    roots: List[Dict] = []
    for item in items:
        item["children"] = []
        nodes[int(item["id"])] = item
    for item in items:
        parent_id = item.get("parent_id")
        if parent_id is not None and int(parent_id) in nodes:
            nodes[int(parent_id)]["children"].append(item)
        else:
            roots.append(item)
    return roots


@router.get("/api/resources/{rid}/comments")
def list_resource_comments(
    request: Request,
    rid: int,
    page: int = Query(default=1),
    pageSize: int = Query(default=20),
):
    page = max(1, int(page or 1))
    page_size = min(50, max(1, int(pageSize or 20)))
    offset = (page - 1) * page_size
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resources WHERE id = ?", (rid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_comments WHERE resource_id = ?",
        (rid,),
    ).fetchone()["c"]
    rows = cur.execute(
        """
        SELECT
          rc.id,
          rc.resource_id,
          rc.user_id,
          rc.parent_id,
          rc.content,
          rc.created_at,
          rc.updated_at,
          u.name AS user_name,
          u.username AS user_username
        FROM resource_comments rc
        LEFT JOIN users u ON u.id = rc.user_id
        WHERE rc.resource_id = ?
        ORDER BY rc.id ASC
        LIMIT ? OFFSET ?
        """,
        (rid, page_size, offset),
    ).fetchall()
    items = [dict(r) for r in rows]
    uid = _require_user_id(request)
    comment_ids = [int(i["id"]) for i in items]
    likes_map: Dict[int, int] = {cid: 0 for cid in comment_ids}
    liked_set = set()
    if comment_ids:
        placeholders = ",".join(["?"] * len(comment_ids))
        likes_rows = cur.execute(
            f"SELECT comment_id, COUNT(1) as c FROM resource_comment_likes WHERE comment_id IN ({placeholders}) GROUP BY comment_id",
            tuple(comment_ids),
        ).fetchall()
        likes_map.update({int(r["comment_id"]): int(r["c"]) for r in likes_rows})
        if uid is not None:
            liked_rows = cur.execute(
                f"SELECT comment_id FROM resource_comment_likes WHERE user_id = ? AND comment_id IN ({placeholders})",
                (uid, *comment_ids),
            ).fetchall()
            liked_set = {int(r["comment_id"]) for r in liked_rows}
    output = []
    for item in items:
        comment_id = int(item["id"])
        output.append(
            {
                "id": comment_id,
                "resource_id": int(item["resource_id"]),
                "user_id": int(item["user_id"]),
                "parent_id": int(item["parent_id"])
                if item.get("parent_id") is not None
                else None,
                "content": item["content"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
                "user": {
                    "id": int(item["user_id"]),
                    "name": item["user_name"] or "",
                    "username": item["user_username"] or "",
                },
                "likes": likes_map.get(comment_id, 0),
                "liked": comment_id in liked_set,
            }
        )
    return {
        "items": _build_tree(output),
        "page": page,
        "pageSize": page_size,
        "total": int(total),
    }


@router.post("/api/resources/{rid}/comments")
def create_resource_comment(
    request: Request,
    rid: int,
    content: Optional[str] = Body(default=None, embed=True),
    parentId: Optional[int] = Body(default=None, embed=True),
):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    if not content or not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "评论内容不能为空"})
    clean_content = _mask_content(content.strip())
    if not clean_content:
        return JSONResponse(status_code=400, content={"error": "评论内容不能为空"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resources WHERE id = ?", (rid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    parent_id = None
    if parentId is not None:
        parent_row = cur.execute(
            "SELECT id FROM resource_comments WHERE id = ? AND resource_id = ?",
            (parentId, rid),
        ).fetchone()
        if not parent_row:
            return JSONResponse(status_code=404, content={"error": "父评论不存在"})
        parent_id = int(parentId)
    info = cur.execute(
        """
        INSERT INTO resource_comments (resource_id, user_id, parent_id, content)
        VALUES (?, ?, ?, ?)
        """,
        (rid, uid, parent_id, clean_content),
    )
    try:
        if parent_id is not None:
            parent_owner = cur.execute(
                "SELECT user_id, content FROM resource_comments WHERE id = ?",
                (parent_id,),
            ).fetchone()
            if parent_owner and parent_owner["user_id"] is not None:
                create_notification(
                    user_id=int(parent_owner["user_id"]),
                    actor_id=uid,
                    notif_type="comment_reply",
                    resource_id=rid,
                    comment_id=int(parent_id),
                    content=parent_owner["content"],
                )
    except Exception:
        pass
    conn.commit()
    comment_id = info.lastrowid
    if comment_id is None:
        return JSONResponse(status_code=500, content={"error": "创建评论失败"})
    comment_id = int(comment_id)
    row = cur.execute(
        """
        SELECT rc.id, rc.resource_id, rc.user_id, rc.parent_id, rc.content, rc.created_at, rc.updated_at,
               u.name AS user_name, u.username AS user_username
        FROM resource_comments rc
        LEFT JOIN users u ON u.id = rc.user_id
        WHERE rc.id = ?
        """,
        (comment_id,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=500, content={"error": "创建评论失败"})
    return {
        "item": {
            "id": int(row["id"]),
            "resource_id": int(row["resource_id"]),
            "user_id": int(row["user_id"]),
            "parent_id": int(row["parent_id"])
            if row["parent_id"] is not None
            else None,
            "content": row["content"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "user": {
                "id": int(row["user_id"]),
                "name": row["user_name"] or "",
                "username": row["user_username"] or "",
            },
            "likes": 0,
            "liked": False,
        }
    }


@router.patch("/api/comments/{cid}")
def update_comment(
    request: Request, cid: int, content: Optional[str] = Body(default=None, embed=True)
):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    if not content or not isinstance(content, str):
        return JSONResponse(status_code=400, content={"error": "评论内容不能为空"})
    clean_content = _mask_content(content.strip())
    if not clean_content:
        return JSONResponse(status_code=400, content={"error": "评论内容不能为空"})
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, user_id FROM resource_comments WHERE id = ?",
        (cid,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "评论不存在"})
    if int(row["user_id"]) != uid:
        return JSONResponse(status_code=403, content={"error": "只能编辑自己的评论"})
    cur.execute(
        "UPDATE resource_comments SET content = ? WHERE id = ?",
        (clean_content, cid),
    )
    conn.commit()
    updated = cur.execute(
        """
        SELECT rc.id, rc.resource_id, rc.user_id, rc.parent_id, rc.content, rc.created_at, rc.updated_at,
               u.name AS user_name, u.username AS user_username
        FROM resource_comments rc
        LEFT JOIN users u ON u.id = rc.user_id
        WHERE rc.id = ?
        """,
        (cid,),
    ).fetchone()
    if not updated:
        return JSONResponse(status_code=500, content={"error": "更新失败"})
    return {
        "item": {
            "id": int(updated["id"]),
            "resource_id": int(updated["resource_id"]),
            "user_id": int(updated["user_id"]),
            "parent_id": int(updated["parent_id"])
            if updated["parent_id"] is not None
            else None,
            "content": updated["content"],
            "created_at": updated["created_at"],
            "updated_at": updated["updated_at"],
            "user": {
                "id": int(updated["user_id"]),
                "name": updated["user_name"] or "",
                "username": updated["user_username"] or "",
            },
        }
    }


@router.delete("/api/comments/{cid}")
def delete_comment(request: Request, cid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, user_id FROM resource_comments WHERE id = ?",
        (cid,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "评论不存在"})
    if int(row["user_id"]) != uid:
        return JSONResponse(status_code=403, content={"error": "只能删除自己的评论"})
    cur.execute("DELETE FROM resource_comments WHERE id = ?", (cid,))
    conn.commit()
    return {"ok": True}


@router.post("/api/comments/{cid}/like")
def like_comment(request: Request, cid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM resource_comments WHERE id = ?", (cid,)
    ).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "评论不存在"})
    already_liked = cur.execute(
        "SELECT 1 FROM resource_comment_likes WHERE comment_id = ? AND user_id = ?",
        (cid, uid),
    ).fetchone()
    if not already_liked:
        cur.execute(
            "INSERT INTO resource_comment_likes (comment_id, user_id) VALUES (?, ?)",
            (cid, uid),
        )
        try:
            comment_row = cur.execute(
                "SELECT user_id, resource_id, content FROM resource_comments WHERE id = ?",
                (cid,),
            ).fetchone()
            if comment_row and comment_row["user_id"] is not None:
                create_notification(
                    user_id=int(comment_row["user_id"]),
                    actor_id=uid,
                    notif_type="comment_like",
                    resource_id=int(comment_row["resource_id"]),
                    comment_id=cid,
                    content=comment_row["content"],
                )
        except Exception:
            pass
        conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_comment_likes WHERE comment_id = ?",
        (cid,),
    ).fetchone()["c"]
    return {"liked": True, "likes": int(total)}


@router.delete("/api/comments/{cid}/like")
def unlike_comment(request: Request, cid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM resource_comments WHERE id = ?", (cid,)
    ).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "评论不存在"})
    cur.execute(
        "DELETE FROM resource_comment_likes WHERE comment_id = ? AND user_id = ?",
        (cid, uid),
    )
    conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_comment_likes WHERE comment_id = ?",
        (cid,),
    ).fetchone()["c"]
    return {"liked": False, "likes": int(total)}
