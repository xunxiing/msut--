import os
import tempfile
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .auth import get_current_user
from .db import get_connection
from .utils import nanoid, now_ms, slugify_str, parse_bool
from .label.watermark_indexer import (
    extract_sequence_from_melsave,
    canonicalize,
    fnv1a64,
)


router = APIRouter()
logger = logging.getLogger("msut.files")

PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5173")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _share_url(slug: str) -> str:
    return f"{PUBLIC_BASE}/share/{slug}"


def _u64_to_i64(u: int) -> int:
    """Map an unsigned 64-bit int to SQLite-compatible signed 64-bit range.
    Keeps two's complement representation so equality works on both sides.
    """
    u &= 0xFFFFFFFFFFFFFFFF
    return u - (1 << 64) if (u & (1 << 63)) else u


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        return int(payload["uid"])  # type: ignore[index]
    except Exception:
        return None


@router.post("/api/resources")
async def create_resource(request: Request, title: Optional[str] = Form(None), description: Optional[str] = Form(None), usage: Optional[str] = Form(None)):
    # Accept both JSON and form payloads for compatibility
    if title is None:
        try:
            data = await request.json()
        except Exception:
            data = {}
        if isinstance(data, dict):
            title = data.get("title")
            description = data.get("description")
            usage = data.get("usage")
    if not title or not isinstance(title, str):
        return JSONResponse(status_code=400, content={"error": "标题必填"})
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    base = slugify_str(title) or f"res-{nanoid()}"
    slug = base
    conn = get_connection()
    cur = conn.cursor()
    i = 1
    while cur.execute("SELECT 1 FROM resources WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base}-{i}"
        i += 1
    info = cur.execute(
        "INSERT INTO resources (slug, title, description, usage, created_by) VALUES (?, ?, ?, ?, ?)",
        (slug, title, description or "", usage or "", uid),
    )
    conn.commit()
    rid = int(info.lastrowid)
    return {"id": rid, "slug": slug, "title": title, "description": description or "", "usage": usage or "", "shareUrl": _share_url(slug)}


async def _save_upload_atomic(request: Request, file: UploadFile, dest_dir: Path) -> Optional[Path]:
    """Save an uploaded file via a temporary .part file and atomically rename.
    Returns final destination path on success, or None on failure.
    Aborts and cleans up if client disconnects or file exceeds MAX_FILE_SIZE.
    """
    ext = Path(file.filename or "").suffix
    stored_name = f"{now_ms()}-{nanoid()}{ext}"
    final_path = dest_dir / stored_name
    temp_path = dest_dir / (stored_name + ".part")
    size = 0
    try:
        with temp_path.open("wb") as f:
            while True:
                # Read in 1MB chunks
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                size += len(chunk)
                # Size limit per file
                if size > MAX_FILE_SIZE:
                    try:
                        f.flush()
                    except Exception:
                        pass
                    try:
                        f.close()
                    except Exception:
                        pass
                    temp_path.unlink(missing_ok=True)
                    return None
                # Check client disconnect mid-stream
                try:
                    if await request.is_disconnected():
                        try:
                            f.flush()
                        except Exception:
                            pass
                        try:
                            f.close()
                        except Exception:
                            pass
                        temp_path.unlink(missing_ok=True)
                        return None
                except Exception:
                    # If disconnect check fails, continue best-effort
                    pass
        # Final disconnect check after write complete
        try:
            if await request.is_disconnected():
                temp_path.unlink(missing_ok=True)
                return None
        except Exception:
            pass
        # Atomic replace to final name
        os.replace(str(temp_path), str(final_path))
        return final_path
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    finally:
        try:
            await file.close()
        except Exception:
            pass


@router.post("/api/files/upload")
async def upload_to_resource(
    request: Request,
    resourceId: int = Form(...),
    files: List[UploadFile] = File(default=[]),
    saveWatermark: Optional[str] = Form(None),
):
    # Debug logging for watermark persistence path
    try:
        import logging as _logging
        _logging.getLogger("msut.files").info(
            "upload_to_resource: resourceId=%s saveWatermark_raw=%s files_count=%s",
            resourceId,
            saveWatermark,
            len(files or []),
        )
    except Exception:
        pass
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    res = cur.execute("SELECT id, created_by FROM resources WHERE id = ?", (resourceId,)).fetchone()
    if not res:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(res["created_by"] or 0) != uid:
        return JSONResponse(status_code=403, content={"error": "无法操作其他用户的资源"})
    if not files:
        return JSONResponse(status_code=400, content={"error": "没有文件"})
    saved = []
    do_wm = parse_bool(saveWatermark, False)
    # Begin a transaction to ensure DB rollback on failure
    cur.execute("BEGIN")
    created_file_paths: List[Path] = []
    try:
        for uf in files[:10]:
            dest = await _save_upload_atomic(request, uf, UPLOAD_DIR)
            if dest is None:
                raise RuntimeError("upload_failed")
            created_file_paths.append(dest)
            url_path = f"/uploads/{dest.name}"
            info = cur.execute(
                """
                INSERT INTO resource_files (resource_id, original_name, stored_name, mime, size, url_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    resourceId,
                    uf.filename or dest.name,
                    dest.name,
                    uf.content_type or None,
                    dest.stat().st_size,
                    url_path,
                ),
            )
        # Attempt watermark extraction for .melsave/.zip when requested
            try:
                suffix = str(dest.suffix).lower()
                if do_wm and suffix in {".melsave", ".zip"}:
                    logger.info(
                        "wm: extracting fileId=%s name=%s suffix=%s",
                        int(info.lastrowid), uf.filename or dest.name, suffix,
                    )
                    raw_seq, embedded = extract_sequence_from_melsave(str(dest))
                    seq_canon = canonicalize([str(x) for x in raw_seq])
                    wm_u64 = int(fnv1a64(seq_canon))
                    wm_i64 = _u64_to_i64(wm_u64)
                    emb_i64 = _u64_to_i64(int(embedded)) if embedded is not None else None
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO file_watermarks (file_id, watermark_u64, seq_len, embedded_watermark)
                        VALUES (?, ?, ?, ?)
                        """,
                        (int(info.lastrowid), wm_i64, int(len(seq_canon)), emb_i64),
                    )
                    logger.info(
                        "wm: saved fileId=%s watermark_u64=%s watermark_i64=%s length=%s embedded=%s embedded_i64=%s",
                        int(info.lastrowid), wm_u64, wm_i64, int(len(seq_canon)),
                        embedded if embedded is not None else None,
                        emb_i64,
                    )
                else:
                    logger.info(
                        "wm: skipped (saveWatermark=%s suffix=%s) fileId=%s",
                        do_wm, suffix, int(info.lastrowid),
                    )
            except Exception as ex:
                # Do not fail the whole upload if watermark extraction fails
                try:
                    logger.exception("wm: extract failed fileId=%s error=%s", int(info.lastrowid), ex)
                except Exception:
                    pass
            saved.append(
                {
                    "id": int(info.lastrowid),
                    "originalName": uf.filename or dest.name,
                    "size": dest.stat().st_size,
                    "mime": uf.content_type or None,
                    "urlPath": url_path,
                }
            )
        conn.commit()
    except Exception:
        # Roll back DB and delete any files saved during this request
        try:
            conn.rollback()
        except Exception:
            pass
        for p in created_file_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        return JSONResponse(status_code=400, content={"error": "上传失败"})
    return {"ok": True, "files": saved}


@router.post("/api/watermark/check")
async def check_watermark(file: UploadFile = File(...)):
    # Accept one .melsave (or .zip) and return computed watermark and DB matches
    try:
        suffix = Path(file.filename or "").suffix.lower()
        try:
            logger.info("wm-check: received name=%s suffix=%s", file.filename, suffix)
        except Exception:
            pass
        if suffix not in {".melsave", ".zip"}:
            return JSONResponse(status_code=400, content={"error": "仅支持 .melsave 或 .zip"})
        # Save to a temp file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
            tmp_path = Path(tmp.name)
    except Exception:
        try:
            file.file.close()
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": "文件读取失败"})
    finally:
        try:
            file.file.close()
        except Exception:
            pass

    try:
        raw_seq, embedded = extract_sequence_from_melsave(str(tmp_path))
        seq_canon = canonicalize([str(x) for x in raw_seq])
        wm_u64 = int(fnv1a64(seq_canon))
        wm_i64 = _u64_to_i64(wm_u64)
        emb_i64 = _u64_to_i64(int(embedded)) if embedded is not None else None
        length = int(len(seq_canon))
        try:
            logger.info(
                "wm-check: computed watermark_u64=%s watermark_i64=%s length=%s embedded=%s embedded_i64=%s",
                wm_u64, wm_i64, length,
                embedded if embedded is not None else None,
                emb_i64,
            )
        except Exception:
            pass
    except Exception as e:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": f"提取失败: {e}"})

    # Query DB for matches
    try:
        conn = get_connection()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT rf.id AS file_id, rf.resource_id, rf.original_name, rf.url_path,
                   r.slug AS resource_slug, r.title AS resource_title
            FROM file_watermarks fw
            JOIN resource_files rf ON rf.id = fw.file_id
            LEFT JOIN resources r ON r.id = rf.resource_id
            WHERE fw.watermark_u64 = ?
            ORDER BY rf.id DESC
            """,
            (wm_i64,),
        ).fetchall()
        matches = [
            {
                "fileId": int(r["file_id"]),
                "resourceId": int(r["resource_id"]) if r["resource_id"] is not None else None,
                "resourceSlug": r["resource_slug"],
                "resourceTitle": r["resource_title"],
                "originalName": r["original_name"],
                "urlPath": r["url_path"],
            }
            for r in rows
        ]
        try:
            logger.info("wm-check: matches=%s fileIds=%s", len(matches), [m.get("fileId") for m in matches])
        except Exception:
            pass
    except Exception:
        matches = []
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "watermark": wm_u64,
        "length": length,
        "embedded": int(embedded) if embedded is not None else None,
        "matches": matches,
    }


@router.get("/api/my/resources")
def list_my_resources(request: Request):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    resources = cur.execute(
        """
        SELECT id, slug, title, description, usage, created_at
        FROM resources WHERE created_by = ? ORDER BY id DESC
        """,
        (uid,),
    ).fetchall()
    items = []
    for r in resources:
        files = cur.execute(
            """
            SELECT id, original_name, stored_name, mime, size, url_path, created_at
            FROM resource_files WHERE resource_id = ? ORDER BY id DESC
            """,
            (r["id"],),
        ).fetchall()
        items.append(
            {
                "id": int(r["id"]),
                "slug": r["slug"],
                "title": r["title"],
                "description": r["description"],
                "usage": r["usage"],
                "created_at": r["created_at"],
                "files": [dict(f) for f in files],
                "shareUrl": _share_url(r["slug"]),
            }
        )
    return {"items": items}


@router.patch("/api/resources/{rid}")
async def update_resource(request: Request, rid: int, description: Optional[str] = Form(None), usage: Optional[str] = Form(None)):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute("SELECT id, slug, created_by FROM resources WHERE id = ?", (rid,)).fetchone()
    if not r:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(r["created_by"] or 0) != uid:
        return JSONResponse(status_code=403, content={"error": "无法操作其他用户的资源"})
    # Accept JSON body as well as form fields
    if description is None and usage is None:
        try:
            data = await request.json()
        except Exception:
            data = {}
        if isinstance(data, dict):
            if "description" in data:
                description = data.get("description")
            if "usage" in data:
                usage = data.get("usage")
    updates = []
    params = []
    if isinstance(description, str):
        updates.append("description = ?")
        params.append(description)
    if isinstance(usage, str):
        updates.append("usage = ?")
        params.append(usage)
    if not updates:
        return JSONResponse(status_code=400, content={"error": "没有需要更新的字段"})
    params.append(rid)
    cur.execute(f"UPDATE resources SET {', '.join(updates)} WHERE id = ?", tuple(params))
    conn.commit()
    updated = cur.execute(
        "SELECT id, slug, title, description, usage, created_at FROM resources WHERE id = ?",
        (rid,),
    ).fetchone()
    return {**{k: updated[k] for k in updated.keys()}, "shareUrl": _share_url(updated["slug"]) }


@router.delete("/api/resources/{rid}")
def delete_resource(request: Request, rid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute("SELECT id, created_by FROM resources WHERE id = ?", (rid,)).fetchone()
    if not r:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(r["created_by"] or 0) != uid:
        return JSONResponse(status_code=403, content={"error": "无法操作其他用户的资源"})
    files = cur.execute("SELECT stored_name FROM resource_files WHERE resource_id = ?", (rid,)).fetchall()
    # Transaction-like operations
    cur.execute("DELETE FROM resource_files WHERE resource_id = ?", (rid,))
    cur.execute("DELETE FROM resources WHERE id = ?", (rid,))
    conn.commit()
    for f in files:
        path = UPLOAD_DIR / f["stored_name"]
        try:
            if path.exists():
                path.unlink()
        except Exception:
            # ignore individual file deletion errors
            pass
    return {"ok": True}


# Early alias to ensure static '/api/resources/likes' matches before dynamic '/api/resources/{slug}'.
# This delegates to the canonical handler defined later in this file.
@router.get("/api/resources/likes")
def _get_resource_likes_alias(request: Request, ids: str = Query(default="")):
    return get_resource_likes(request, ids)


@router.get("/api/files/likes")
def get_file_likes(request: Request, ids: str = Query(default="")):
    ids = (ids or "").strip()
    if not ids:
        return {"items": []}
    try:
        file_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    except Exception:
        return JSONResponse(status_code=400, content={"error": "参数错误"})
    if not file_ids:
        return {"items": []}
    conn = get_connection()
    cur = conn.cursor()
    # Build dynamic placeholders for IN clause
    ph = ",".join(["?"] * len(file_ids))
    counts = cur.execute(
        f"SELECT file_id, COUNT(1) AS c FROM resource_file_likes WHERE file_id IN ({ph}) GROUP BY file_id",
        tuple(file_ids),
    ).fetchall()
    count_map = {int(r["file_id"]): int(r["c"]) for r in counts}
    uid = _require_user_id(request)
    liked_set = set()
    if uid is not None:
        liked_rows = cur.execute(
            f"SELECT file_id FROM resource_file_likes WHERE user_id = ? AND file_id IN ({ph})",
            (uid, *file_ids),
        ).fetchall()
        liked_set = {int(r["file_id"]) for r in liked_rows}
    items = []
    for fid in file_ids:
        items.append({"id": fid, "likes": int(count_map.get(fid, 0)), "liked": fid in liked_set})
    return {"items": items}


@router.post("/api/files/{fid}/like")
def like_file(request: Request, fid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resource_files WHERE id = ?", (fid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    # idempotent like
    cur.execute("INSERT OR IGNORE INTO resource_file_likes (file_id, user_id) VALUES (?, ?)", (fid, uid))
    conn.commit()
    total = cur.execute("SELECT COUNT(1) as c FROM resource_file_likes WHERE file_id = ?", (fid,)).fetchone()["c"]
    return {"liked": True, "likes": int(total)}


@router.delete("/api/files/{fid}/like")
def unlike_file(request: Request, fid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resource_files WHERE id = ?", (fid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    cur.execute("DELETE FROM resource_file_likes WHERE file_id = ? AND user_id = ?", (fid, uid))
    conn.commit()
    total = cur.execute("SELECT COUNT(1) as c FROM resource_file_likes WHERE file_id = ?", (fid,)).fetchone()["c"]
    return {"liked": False, "likes": int(total)}


@router.get("/api/resources/{slug}")
def get_resource(slug: str):
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute(
        """
        SELECT r.*, u.name AS author_name, u.username AS author_username
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        WHERE r.slug = ?
        """,
        (slug,),
    ).fetchone()
    if not r:
        return JSONResponse(status_code=404, content={"error": "未找到资源"})
    files = cur.execute(
        "SELECT id, original_name, stored_name, mime, size, url_path, created_at FROM resource_files WHERE resource_id = ? ORDER BY id DESC",
        (r["id"],),
    ).fetchall()
    data = {**{k: r[k] for k in r.keys()}, "files": [dict(f) for f in files], "shareUrl": _share_url(r["slug"]) }
    return data


@router.get("/api/resources")
def list_resources(q: str = Query(default=""), page: int = Query(default=1), pageSize: int = Query(default=12)):
    q = (q or "").strip()
    page = max(1, int(page or 1))
    page_size = min(50, max(1, int(pageSize or 12)))
    offset = (page - 1) * page_size
    conn = get_connection()
    cur = conn.cursor()
    where = "WHERE r.title LIKE ? OR r.description LIKE ?" if q else ""
    args: List = [f"%{q}%", f"%{q}%"] if q else []
    # Use the same table alias as in the items query to avoid 'no such column: r.title'
    total = cur.execute(f"SELECT COUNT(1) as c FROM resources r {where}", tuple(args)).fetchone()["c"]
    items = cur.execute(
        f"""
        SELECT r.id, r.slug, r.title, r.description, r.created_at,
               u.name AS author_name, u.username AS author_username
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        {where}
        ORDER BY r.id DESC
        LIMIT ? OFFSET ?
        """,
        (*args, page_size, offset),
    ).fetchall()
    return {"items": [dict(i) for i in items], "page": page, "pageSize": page_size, "total": total}


# ----- Resource likes (collections) -----

@router.get("/api/resources/likes")
def get_resource_likes(request: Request, ids: str = Query(default="")):
    ids = (ids or "").strip()
    if not ids:
        return {"items": []}
    try:
        resource_ids = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    except Exception:
        return JSONResponse(status_code=400, content={"error": "参数错误"})
    if not resource_ids:
        return {"items": []}
    conn = get_connection()
    cur = conn.cursor()
    ph = ",".join(["?"] * len(resource_ids))
    counts = cur.execute(
        f"SELECT resource_id, COUNT(1) AS c FROM resource_likes WHERE resource_id IN ({ph}) GROUP BY resource_id",
        tuple(resource_ids),
    ).fetchall()
    count_map = {int(r["resource_id"]): int(r["c"]) for r in counts}
    uid = _require_user_id(request)
    liked_set = set()
    if uid is not None:
        liked_rows = cur.execute(
            f"SELECT resource_id FROM resource_likes WHERE user_id = ? AND resource_id IN ({ph})",
            (uid, *resource_ids),
        ).fetchall()
        liked_set = {int(r["resource_id"]) for r in liked_rows}
    items = []
    for rid in resource_ids:
        items.append({"id": rid, "likes": int(count_map.get(rid, 0)), "liked": rid in liked_set})
    return {"items": items}


@router.post("/api/resources/{rid}/like")
def like_resource(request: Request, rid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resources WHERE id = ?", (rid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    cur.execute("INSERT OR IGNORE INTO resource_likes (resource_id, user_id) VALUES (?, ?)", (rid, uid))
    conn.commit()
    total = cur.execute("SELECT COUNT(1) as c FROM resource_likes WHERE resource_id = ?", (rid,)).fetchone()["c"]
    return {"liked": True, "likes": int(total)}


@router.delete("/api/resources/{rid}/like")
def unlike_resource(request: Request, rid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute("SELECT id FROM resources WHERE id = ?", (rid,)).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    cur.execute("DELETE FROM resource_likes WHERE resource_id = ? AND user_id = ?", (rid, uid))
    conn.commit()
    total = cur.execute("SELECT COUNT(1) as c FROM resource_likes WHERE resource_id = ?", (rid,)).fetchone()["c"]
    return {"liked": False, "likes": int(total)}


@router.get("/api/files/{fid}/download")
def download_file(fid: int):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT original_name, stored_name FROM resource_files WHERE id = ?", (fid,)).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    path = UPLOAD_DIR / row["stored_name"]
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "文件丢了"})
    from urllib.parse import quote
    filename = row["original_name"]
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
    }
    # FastAPI's FileResponse sets correct headers and content-type
    return FileResponse(path, headers=headers)
