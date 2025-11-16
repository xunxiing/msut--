import logging
import math
import time
from typing import List, Optional, Sequence

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse

from .auth import get_current_user
from .db import get_connection
from .rag_client import chat_answer, get_embedding, is_rag_configured
from .utils import nanoid, slugify_str


router = APIRouter()
logger = logging.getLogger("msut.tutorials")


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        return int(payload["uid"])  # type: ignore[index]
    except Exception:
        return None


def _make_slug(title: str) -> str:
    base = slugify_str(title) or f"tutorial-{nanoid()}"
    conn = get_connection()
    cur = conn.cursor()
    slug = base
    i = 1
    while cur.execute("SELECT 1 FROM tutorials WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _chunk_content(content: str, max_len: int = 500) -> List[str]:
    """Naive character-based chunking for RAG.

    This keeps dependencies minimal and works reasonably for中文/英文混排。
    """
    text = (content or "").strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_len, length)
        # try to break on a newline or punctuation near the boundary
        window = text[start:end]
        split_at = window.rfind("\n")
        if split_at == -1:
            for sep in ("。", "！", "？", ".", "!", "?"):
                pos = window.rfind(sep)
                if pos != -1:
                    split_at = pos + 1
                    break
        if split_at != -1 and split_at > 0:
            end = start + split_at
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    la = len(a)
    lb = len(b)
    if la != lb:
        n = min(la, lb)
        a = a[:n]
        b = b[:n]
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / math.sqrt(na * nb)


@router.post("/api/tutorials")
async def create_tutorial(
    request: Request,
    body: dict = Body(...),
):
    title = (body.get("title") or "").strip() if isinstance(body, dict) else ""
    description = (body.get("description") or "").strip() if isinstance(body, dict) else ""
    content = (body.get("content") or "").strip() if isinstance(body, dict) else ""
    if not title:
        return JSONResponse(status_code=400, content={"error": "标题必填"})
    if not content:
        return JSONResponse(status_code=400, content={"error": "内容不能为空"})
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    slug = _make_slug(title)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tutorials (slug, title, description, content, created_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (slug, title, description, content, uid),
    )
    tid = int(cur.lastrowid)

    # Prepare embeddings (best-effort; failure should not block basic文档功能)
    chunks = _chunk_content(content)
    if chunks:
        try:
            for idx, chunk in enumerate(chunks):
                vec = get_embedding(chunk) or []
                cur.execute(
                    """
                    INSERT INTO tutorial_embeddings (tutorial_id, chunk_index, chunk_text, embedding_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (tid, idx, chunk, json_dumps(vec)),
                )
        except Exception as e:
            try:
                logger.exception("tutorials: embedding index failed tid=%s error=%s", tid, e)
            except Exception:
                pass
    conn.commit()

    return {
        "id": tid,
        "slug": slug,
        "title": title,
        "description": description,
    }


@router.get("/api/tutorials")
def list_tutorials(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=50),
):
    conn = get_connection()
    cur = conn.cursor()
    where = ""
    params: List[object] = []
    if q:
        where = "WHERE title LIKE ? OR description LIKE ? OR content LIKE ?"
        like = f"%{q}%"
        params.extend([like, like, like])
    count_sql = f"SELECT COUNT(1) AS c FROM tutorials {where}"
    total_row = cur.execute(count_sql, params).fetchone()
    total = int(total_row["c"] if total_row else 0)
    offset = (page - 1) * pageSize
    list_sql = f"""
        SELECT id, slug, title, description, created_at
        FROM tutorials
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ? OFFSET ?
    """
    params_with_limit = params + [pageSize, offset]
    rows = cur.execute(list_sql, params_with_limit).fetchall()
    items = []
    for r in rows or []:
        items.append(
            {
                "id": int(r["id"]),
                "slug": r["slug"],
                "title": r["title"],
                "description": r["description"] or "",
                "created_at": r["created_at"],
            }
        )
    return {"items": items, "total": total, "page": page, "pageSize": pageSize}


@router.get("/api/tutorials/{tid}")
def get_tutorial(tid: int):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, slug, title, description, content, created_at, updated_at FROM tutorials WHERE id = ?",
        (tid,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "教程不存在"})
    return {
        "id": int(row["id"]),
        "slug": row["slug"],
        "title": row["title"],
        "description": row["description"] or "",
        "content": row["content"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _load_all_embeddings(conn) -> List[dict]:
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT e.tutorial_id, e.chunk_index, e.chunk_text, e.embedding_json,
               t.slug AS tutorial_slug, t.title AS tutorial_title
        FROM tutorial_embeddings e
        JOIN tutorials t ON t.id = e.tutorial_id
        """
    ).fetchall()
    items: List[dict] = []
    import json  # local import to keep module-level deps minimal

    for r in rows or []:
        try:
            vec = json.loads(r["embedding_json"] or "[]")
            vec = [float(x) for x in vec]
        except Exception:
            vec = []
        items.append(
            {
                "tutorial_id": int(r["tutorial_id"]),
                "tutorial_slug": r["tutorial_slug"],
                "tutorial_title": r["tutorial_title"],
                "chunk_index": int(r["chunk_index"]),
                "chunk_text": r["chunk_text"],
                "embedding": vec,
            }
        )
    return items


def json_dumps(obj) -> str:
    import json

    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return "[]"


@router.post("/api/tutorials/search-and-ask")
async def search_and_ask(body: dict = Body(...)):
    """Unified endpoint for traditional-like search + RAG QA."""
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "请求格式错误"})
    raw_query = (body.get("query") or "").strip()
    if not raw_query:
        return JSONResponse(status_code=400, content={"error": "查询内容不能为空"})
    mode = (body.get("mode") or "both").strip().lower()
    if mode not in {"search", "qa", "both"}:
        mode = "both"
    limit = body.get("limit")
    try:
        k = int(limit) if limit is not None else 5
    except Exception:
        k = 5
    if k <= 0:
        k = 5
    if k > 10:
        k = 10

    conn = get_connection()
    start = time.time()

    # If RAG not configured, fall back to simple LIKE search only
    if not is_rag_configured():
        cur = conn.cursor()
        like = f"%{raw_query}%"
        rows = cur.execute(
            """
            SELECT id, slug, title, description, substr(content, 1, 400) AS excerpt
            FROM tutorials
            WHERE title LIKE ? OR description LIKE ? OR content LIKE ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (like, like, like, k),
        ).fetchall()
        results = []
        for r in rows or []:
            results.append(
                {
                    "tutorialId": int(r["id"]),
                    "slug": r["slug"],
                    "title": r["title"],
                    "excerpt": r["excerpt"],
                    "score": None,
                }
            )
        took_ms = int((time.time() - start) * 1000)
        return {
            "query": raw_query,
            "mode": "search",
            "search": {"items": results, "tookMs": took_ms},
            "answer": None,
            "ragEnabled": False,
        }

    # Vector-based semantic search
    q_vec = get_embedding(raw_query)
    if not q_vec:
        return JSONResponse(status_code=500, content={"error": "向量检索失败，请稍后重试"})
    all_items = _load_all_embeddings(conn)
    scored: List[dict] = []
    for item in all_items:
        score = _cosine(q_vec, item.get("embedding") or [])
        scored.append({**item, "score": float(score)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:k]
    search_items = []
    for it in top:
        search_items.append(
            {
                "tutorialId": it["tutorial_id"],
                "slug": it["tutorial_slug"],
                "title": it["tutorial_title"],
                "excerpt": it["chunk_text"],
                "score": it["score"],
            }
        )

    took_ms = int((time.time() - start) * 1000)

    answer_payload = None
    if mode in {"qa", "both"} and top:
        contexts: List[str] = [it["chunk_text"] for it in top]
        answer = chat_answer(raw_query, contexts) or ""
        if answer:
            answer_payload = {
                "text": answer,
                "sources": search_items,
            }

    effective_mode = mode
    if effective_mode in {"qa", "both"} and not answer_payload:
        effective_mode = "search"

    return {
        "query": raw_query,
        "mode": effective_mode,
        "search": {"items": search_items, "tookMs": took_ms},
        "answer": answer_payload,
        "ragEnabled": True,
    }

