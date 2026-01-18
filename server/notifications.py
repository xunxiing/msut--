import logging
from typing import Dict, Optional

from .db import get_connection


logger = logging.getLogger("msut.notifications")


def _cleanup_old(conn, days: int = 30) -> None:
    try:
        conn.execute(
            "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
            (f"-{days} day",),
        )
    except Exception:
        pass


def create_notification(
    user_id: int,
    actor_id: int,
    notif_type: str,
    resource_id: Optional[int] = None,
    comment_id: Optional[int] = None,
    content: Optional[str] = None,
) -> None:
    if user_id == actor_id:
        return
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO notifications (user_id, actor_id, type, resource_id, comment_id, content)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, actor_id, notif_type, resource_id, comment_id, content),
        )
        _cleanup_old(conn)
        conn.commit()
    except Exception as ex:
        try:
            logger.exception("create_notification failed: %s", ex)
        except Exception:
            pass


def build_notification_payload(row: Dict) -> Dict:
    return {
        "id": int(row["id"]),
        "type": row["type"],
        "content": row.get("content"),
        "created_at": row["created_at"],
        "resource": {
            "id": int(row["resource_id"])
            if row.get("resource_id") is not None
            else None,
            "slug": row.get("resource_slug"),
            "title": row.get("resource_title"),
        },
        "comment": {
            "id": int(row["comment_id"]) if row.get("comment_id") is not None else None,
            "content": row.get("comment_content"),
        },
        "actor": {
            "id": int(row["actor_id"]),
            "name": row.get("actor_name") or "",
            "username": row.get("actor_username") or "",
        },
    }
