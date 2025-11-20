import asyncio
import logging
import math
import time
from typing import List, Optional, Sequence

from fastapi import APIRouter, BackgroundTasks, Body, Query, Request
from fastapi.responses import JSONResponse

from .auth import get_current_user
from .db import get_connection
from .rag_client import chat_answer, get_embedding, is_rag_configured, optimize_chunk_text, name_chunk_title
from .utils import nanoid, slugify_str


router = APIRouter()
logger = logging.getLogger("msut.tutorials")

# Limit concurrent LLM optimization tasks for tutorial chunks
_CHUNK_OPT_SEMAPHORE = asyncio.Semaphore(2)


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
    try:
        cur = conn.cursor()
        slug = base
        i = 1
        while cur.execute("SELECT 1 FROM tutorials WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base}-{i}"
            i += 1
        return slug
    finally:
        try:
            conn.close()
        except Exception:
            pass


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
    background_tasks: BackgroundTasks = None,
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

    # Schedule background LLM optimization of new chunks (best-effort, low concurrency)
    try:
        if background_tasks is not None and chunks and is_rag_configured():
            background_tasks.add_task(_optimize_tutorial_chunks_async, tid)
    except Exception:
        # Do not block main flow on background scheduling issues
        pass

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


@router.get("/api/my/tutorials")
def list_my_tutorials(request: Request):
    """List tutorials created by the current user for management."""
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, slug, title, description, created_at, updated_at
        FROM tutorials
        WHERE created_by = ?
        ORDER BY id DESC
        """,
        (uid,),
    ).fetchall()
    items: List[dict] = []
    for r in rows or []:
        items.append(
            {
                "id": int(r["id"]),
                "slug": r["slug"],
                "title": r["title"],
                "description": r["description"] or "",
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
        )
    return {"items": items}


@router.patch("/api/tutorials/{tid}")
async def update_tutorial(
    request: Request,
    tid: int,
    body: dict = Body(...),
    background_tasks: BackgroundTasks = None,
):
    """Update a tutorial owned by the current user and refresh embeddings when content changes."""
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "请求格式错误"})

    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, slug, title, description, content, created_by FROM tutorials WHERE id = ?",
        (tid,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "教程不存在"})
    try:
        owner_id = int(row["created_by"]) if row["created_by"] is not None else None
    except Exception:
        owner_id = None
    if owner_id is None or owner_id != uid:
        return JSONResponse(status_code=403, content={"error": "无法操作其他用户的教程"})

    title = body.get("title")
    description = body.get("description")
    content = body.get("content")

    updates: List[str] = []
    params: List[object] = []

    if title is not None:
        if not isinstance(title, str) or not title.strip():
            return JSONResponse(status_code=400, content={"error": "标题必填"})
        title = title.strip()
        updates.append("title = ?")
        params.append(title)
    else:
        title = row["title"]

    if description is not None:
        if not isinstance(description, str):
            description = ""
        description = str(description).strip()
        updates.append("description = ?")
        params.append(description)
    else:
        description = row["description"]

    content_changed = False
    if content is not None:
        if not isinstance(content, str) or not content.strip():
            return JSONResponse(status_code=400, content={"error": "内容不能为空"})
        content = content.strip()
        updates.append("content = ?")
        params.append(content)
        old_content = row["content"] or ""
        content_changed = content != old_content

    if not updates:
        return JSONResponse(status_code=400, content={"error": "没有需要更新的字段"})

    params.append(tid)
    cur.execute(f"UPDATE tutorials SET {', '.join(updates)} WHERE id = ?", tuple(params))

    chunks: List[str] = []
    if content_changed:
        # Rebuild chunk embeddings for RAG search
        cur.execute("DELETE FROM tutorial_embeddings WHERE tutorial_id = ?", (tid,))
        chunks = _chunk_content(content or "")
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
                    logger.exception("tutorials: reindex embeddings failed tid=%s error=%s", tid, e)
                except Exception:
                    pass

    try:
        conn.commit()
    except Exception:
        pass

    # Schedule background optimization of updated chunks
    try:
        if background_tasks is not None and content_changed and chunks and is_rag_configured():
            background_tasks.add_task(_optimize_tutorial_chunks_async, tid)
    except Exception:
        pass

    updated = cur.execute(
        "SELECT id, slug, title, description, content, created_at, updated_at FROM tutorials WHERE id = ?",
        (tid,),
    ).fetchone()
    if not updated:
        return JSONResponse(status_code=404, content={"error": "教程不存在"})
    return {
        "id": int(updated["id"]),
        "slug": updated["slug"],
        "title": updated["title"],
        "description": updated["description"] or "",
        "content": updated["content"],
        "created_at": updated["created_at"],
        "updated_at": updated["updated_at"],
    }


@router.delete("/api/tutorials/{tid}")
async def delete_tutorial(request: Request, tid: int):
    """Delete a tutorial owned by the current user."""
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, created_by FROM tutorials WHERE id = ?",
        (tid,),
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "教程不存在"})
    try:
        owner_id = int(row["created_by"]) if row["created_by"] is not None else None
    except Exception:
        owner_id = None
    if owner_id is None or owner_id != uid:
        return JSONResponse(status_code=403, content={"error": "无法操作其他用户的教程"})

    cur.execute("DELETE FROM tutorials WHERE id = ?", (tid,))
    try:
        conn.commit()
    except Exception:
        pass
    return {"ok": True}


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


@router.get("/api/tutorials/{tid}/chunks")
def list_tutorial_chunks(tid: int):
    """Return the chunk structure for a given tutorial for visualization/navigation."""
    conn = get_connection()
    cur = conn.cursor()
    trow = cur.execute(
        "SELECT id, slug, title FROM tutorials WHERE id = ?",
        (tid,),
    ).fetchone()
    if not trow:
        return JSONResponse(status_code=404, content={"error": "教程不存在"})

    rows = cur.execute(
        """
        SELECT id,
               chunk_index,
               COALESCE(chunk_title, '') AS chunk_title,
               COALESCE(optimized_chunk_text, chunk_text) AS text
        FROM tutorial_embeddings
        WHERE tutorial_id = ?
        ORDER BY chunk_index
        """,
        (tid,),
    ).fetchall()

    chunks = []
    for r in rows or []:
        idx = int(r["chunk_index"])
        title = (r["chunk_title"] or "").strip()
        text = (r["text"] or "").strip()
        if not title:
            # Fallback: use the first line/words as a temporary title
            first_line = text.splitlines()[0] if text else ""
            title = first_line[:24] or f"片段 {idx + 1}"
        preview = text[:80]
        chunks.append(
            {
                "id": int(r["id"]),
                "index": idx,
                "title": title,
                "preview": preview,
            }
        )

    return {
        "tutorialId": int(trow["id"]),
        "slug": trow["slug"],
        "title": trow["title"],
        "chunks": chunks,
    }


def _load_all_embeddings(conn) -> List[dict]:
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT e.tutorial_id,
               e.chunk_index,
               COALESCE(e.optimized_chunk_text, e.chunk_text) AS chunk_text,
               e.embedding_json,
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


async def _optimize_tutorial_chunks_async(tutorial_id: int) -> None:
    """Background job: use LLM to optimize newly created chunks for a tutorial.

    - Runs with a global semaphore to limit concurrency.
    - Best-effort: all errors are logged and do not affect main flows.
    """
    # If RAG is not configured, skip silently
    if not is_rag_configured():
        return

    async with _CHUNK_OPT_SEMAPHORE:
        conn = get_connection()
        try:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT e.id,
                       e.chunk_text,
                       e.optimized_chunk_text,
                       e.embedding_json,
                       e.chunk_title,
                       t.title AS tutorial_title
                FROM tutorial_embeddings e
                JOIN tutorials t ON t.id = e.tutorial_id
                WHERE e.tutorial_id = ?
                ORDER BY e.chunk_index
                """,
                (tutorial_id,),
            ).fetchall()
            if not rows:
                return

            for r in rows or []:
                try:
                    emb_id = int(r["id"])
                    existing_opt = (r["optimized_chunk_text"] or "").strip()
                    existing_title = (r["chunk_title"] or "").strip()
                    raw_text = (r["chunk_text"] or "").strip()
                    tutorial_title = (r["tutorial_title"] or "").strip()
                except Exception:
                    continue

                if not raw_text:
                    continue

                optimized: Optional[str] = None
                # Only call LLM for optimization if not done yet
                if not existing_opt:
                    try:
                        # Run blocking LLM call in a thread to avoid blocking the event loop
                        optimized = await asyncio.to_thread(optimize_chunk_text, raw_text)
                    except Exception:
                        optimized = None
                else:
                    optimized = existing_opt

                # Generate a chunk title if missing
                title_value: Optional[str] = None
                if not existing_title:
                    try:
                        title_value = await asyncio.to_thread(name_chunk_title, raw_text, tutorial_title or None)
                    except Exception:
                        title_value = None

                if not optimized and not title_value:
                    # Nothing to update
                    continue

                # Optionally re-embed the optimized text; fall back to old embedding on failure
                emb_json = None
                if optimized and not existing_opt:
                    try:
                        new_vec = get_embedding(optimized) or None
                    except Exception:
                        new_vec = None
                    if new_vec is not None:
                        emb_json = json_dumps(new_vec)

                try:
                    cur.execute(
                        """
                        UPDATE tutorial_embeddings
                        SET optimized_chunk_text = COALESCE(?, optimized_chunk_text),
                            optimized_at = CASE
                                WHEN ? IS NOT NULL THEN datetime('now')
                                ELSE optimized_at
                            END,
                            embedding_json = COALESCE(?, embedding_json),
                            chunk_title = COALESCE(?, chunk_title)
                        WHERE id = ?
                        """,
                        (optimized, optimized, emb_json, title_value, emb_id),
                    )
                except Exception as e:
                    try:
                        logger.exception(
                            "tutorials: optimize/naming chunk update failed tutorial_id=%s chunk_id=%s error=%s",
                            tutorial_id,
                            emb_id,
                            e,
                        )
                    except Exception:
                        pass
            try:
                conn.commit()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass


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

