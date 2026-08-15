import os
import re
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, Body
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from .auth import get_current_user
from .db import get_connection
from .utils import nanoid, now_ms, slugify_str, parse_bool
from .llm2 import tags_from_json
from .label.watermark_indexer import (
    extract_sequence_from_melsave,
    canonicalize,
    fnv1a64,
)
from .notifications import create_notification
from . import storage as r2


router = APIRouter()
logger = logging.getLogger("msut.files")

PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5173")

# Keep for backward compat (temp file staging during uploads)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

TEMP_DIR = Path(tempfile.gettempdir()) / "msut_uploads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _share_url(slug: str) -> str:
    return f"{PUBLIC_BASE}/share/{slug}"


def _safe_ascii_filename(filename: str) -> str:
    if not filename:
        return "file"
    p = Path(filename)
    ext = "".join(p.suffixes)
    stem = p.name[: -len(ext)] if ext else p.name
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    if not safe_stem:
        safe_stem = "file"
    return f"{safe_stem}{ext}" if ext else safe_stem


def _u64_to_i64(u: int) -> int:
    """Map an unsigned 64-bit int to SQLite-compatible signed 64-bit range.
    Keeps two's complement representation so equality works on both sides.
    """
    u &= 0xFFFFFFFFFFFFFFFF
    return u - (1 << 64) if (u & (1 << 63)) else u


def _is_image_file(mime: Optional[str], name: Optional[str]) -> bool:
    """
    判定一个文件是否为图片文件（用于封面/展示图）：
    - MIME 以 image/ 开头，或
    - 文件名后缀为常见图片扩展名
    """
    mime_lc = (mime or "").lower()
    name_lc = (name or "").lower()
    if mime_lc.startswith("image/"):
        return True
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"):
        if name_lc.endswith(ext):
            return True
    return False


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        return int(payload["uid"])  # type: ignore[index]
    except Exception:
        return None


def _require_owner(
    request: Request, resource_id: int
) -> Tuple[Optional[int], Optional[str]]:
    """
    Ensure the current user is the owner of the given resource.
    Returns (user_id, error_message). When error_message is None, the check passed.
    """
    uid = _require_user_id(request)
    if uid is None:
        return None, "未登录"
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute(
        "SELECT id, created_by FROM resources WHERE id = ?", (resource_id,)
    ).fetchone()
    if not r:
        return uid, "资源不存在"
    if int(r["created_by"] or 0) != uid:
        return uid, "无法操作其他用户的资源"
    return uid, None


@router.post("/api/resources")
async def create_resource(
    request: Request,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    usage: Optional[str] = Form(None),
):
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
    try:
        from .llm2 import classify_resource, tags_to_json, tags_from_json
        tags = classify_resource(title, description or "")
        if tags:
            conn.execute("UPDATE resources SET tags = ? WHERE id = ?", (tags_to_json(tags), rid))
            conn.commit()
    except Exception:
        tags = []
    return {
        "id": rid,
        "slug": slug,
        "title": title,
        "description": description or "",
        "usage": usage or "",
        "tags": tags or [],
        "shareUrl": _share_url(slug),
    }


async def _save_upload_to_r2(
    request: Request, file: UploadFile
) -> Optional[Tuple[str, str, int, Path]]:
    """Save an uploaded file to a temp path, upload to R2, and return
    (r2_key, url_path, size, temp_path) on success, or None on failure.
    The temp file is kept for optional watermark extraction and cleaned up by caller.
    Aborts and cleans up if client disconnects or file exceeds MAX_FILE_SIZE.
    """
    ext = Path(file.filename or "").suffix
    stored_name = f"{now_ms()}-{nanoid()}{ext}"
    r2_key = f"uploads/{stored_name}"
    temp_path = TEMP_DIR / stored_name
    size = 0
    try:
        with temp_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                size += len(chunk)
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
                    pass
        try:
            if await request.is_disconnected():
                temp_path.unlink(missing_ok=True)
                return None
        except Exception:
            pass
        # Upload to R2
        content_type = file.content_type or ""
        r2.upload_file(r2_key, temp_path, content_type)
        url_path = r2.build_public_url(r2_key)
        return (r2_key, url_path, size, temp_path)
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
    res = cur.execute(
        "SELECT id, created_by FROM resources WHERE id = ?", (resourceId,)
    ).fetchone()
    if not res:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(res["created_by"] or 0) != uid:
        return JSONResponse(
            status_code=403, content={"error": "无法操作其他用户的资源"}
        )
    if not files:
        return JSONResponse(status_code=400, content={"error": "没有文件"})
    saved = []
    do_wm = parse_bool(saveWatermark, False)
    # 使用 autocommit，每条语句独立事务，避免长时间持有写锁
    created_r2_keys: List[str] = []
    created_temp_paths: List[Path] = []
    first_uploaded_image_id: Optional[int] = None
    try:
        for uf in files[:10]:
            result = await _save_upload_to_r2(request, uf)
            if result is None:
                raise RuntimeError("upload_failed")
            r2_key, url_path, file_size, temp_path = result
            created_r2_keys.append(r2_key)
            created_temp_paths.append(temp_path)
            info = cur.execute(
                """
                INSERT INTO resource_files (resource_id, original_name, stored_name, mime, size, url_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    resourceId,
                    uf.filename or r2_key,
                    r2_key,
                    uf.content_type or None,
                    file_size,
                    url_path,
                ),
            )
            file_id = int(info.lastrowid)
            # Check if this is the first uploaded image and if no cover is set yet
            if _is_image_file(uf.content_type, uf.filename):
                if first_uploaded_image_id is None:
                    first_uploaded_image_id = file_id
            # Attempt watermark extraction for .melsave/.zip when requested
            try:
                suffix = Path(uf.filename or "").suffix.lower()
                if do_wm and suffix in {".melsave", ".zip"}:
                    logger.info(
                        "wm: extracting fileId=%s name=%s suffix=%s",
                        file_id,
                        uf.filename or r2_key,
                        suffix,
                    )
                    raw_seq, embedded = extract_sequence_from_melsave(str(temp_path))
                    seq_canon = canonicalize([str(x) for x in raw_seq])
                    wm_u64 = int(fnv1a64(seq_canon))
                    wm_i64 = _u64_to_i64(wm_u64)
                    emb_i64 = (
                        _u64_to_i64(int(embedded)) if embedded is not None else None
                    )
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO file_watermarks (file_id, watermark_u64, seq_len, embedded_watermark)
                        VALUES (?, ?, ?, ?)
                        """,
                        (file_id, wm_i64, int(len(seq_canon)), emb_i64),
                    )
                    logger.info(
                        "wm: saved fileId=%s watermark_u64=%s watermark_i64=%s length=%s embedded=%s embedded_i64=%s",
                        file_id,
                        wm_u64,
                        wm_i64,
                        int(len(seq_canon)),
                        embedded if embedded is not None else None,
                        emb_i64,
                    )
                else:
                    logger.info(
                        "wm: skipped (saveWatermark=%s suffix=%s) fileId=%s",
                        do_wm,
                        suffix,
                        file_id,
                    )
            except Exception as ex:
                # Do not fail the whole upload if watermark extraction fails
                try:
                    logger.exception(
                        "wm: extract failed fileId=%s error=%s", file_id, ex
                    )
                except Exception:
                    pass
            saved.append(
                {
                    "id": file_id,
                    "originalName": uf.filename or r2_key,
                    "size": file_size,
                    "mime": uf.content_type or None,
                    "urlPath": url_path,
                }
            )
        # After all files are uploaded, set the cover if it's the first image and no cover exists
        if first_uploaded_image_id is not None:
            current_cover = cur.execute(
                "SELECT cover_file_id FROM resources WHERE id = ?", (resourceId,)
            ).fetchone()
            if current_cover and current_cover["cover_file_id"] is None:
                cur.execute(
                    "UPDATE resources SET cover_file_id = ? WHERE id = ?",
                    (first_uploaded_image_id, resourceId),
                )
                logger.info(
                    "Auto-set cover for resource %s to file %s",
                    resourceId,
                    first_uploaded_image_id,
                )

        conn.commit()
    except Exception:
        # Roll back DB and delete any R2 objects uploaded during this request
        try:
            conn.rollback()
        except Exception:
            pass
        for key in created_r2_keys:
            try:
                r2.delete_object(key)
            except Exception:
                pass
        return JSONResponse(status_code=400, content={"error": "上传失败"})
    finally:
        for p in created_temp_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
    return {"ok": True, "files": saved}


@router.post("/api/resources/{rid}/images/upload")
async def upload_resource_images(
    request: Request,
    rid: int,
    files: List[UploadFile] = File(default=[]),
):
    """
    为指定资源上传图片文件（封面 / 展示图）。
    - 仅资源创建者可用
    - 仅允许图片类型，最多 10 个，单文件 50MB
    - 文件仍然写入 resource_files 表，后续可通过 /api/resources/{rid}/images 查询
    - 如果资源尚无封面，则自动将第一张上传的图片设为封面
    """
    uid, err = _require_owner(request, rid)
    if err is not None:
        if uid is None:
            return JSONResponse(status_code=401, content={"error": err})
        # 对于不存在或无权限统一返回 403，错误文案仍然由 err 提示
        return JSONResponse(status_code=403, content={"error": err})
    if not files:
        return JSONResponse(status_code=400, content={"error": "没有文件"})
    # 先整体校验类型，避免部分文件已落库又整体报错
    for uf in files[:10]:
        if not _is_image_file(uf.content_type, uf.filename or ""):
            return JSONResponse(status_code=400, content={"error": "仅支持图片文件"})
    conn = get_connection()
    cur = conn.cursor()
    saved = []
    created_r2_keys: List[str] = []
    created_temp_paths: List[Path] = []
    first_uploaded_image_id: Optional[int] = None
    try:
        for uf in files[:10]:
            result = await _save_upload_to_r2(request, uf)
            if result is None:
                raise RuntimeError("upload_failed")
            r2_key, url_path, file_size, temp_path = result
            created_r2_keys.append(r2_key)
            created_temp_paths.append(temp_path)
            info = cur.execute(
                """
                INSERT INTO resource_files (resource_id, original_name, stored_name, mime, size, url_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rid,
                    uf.filename or r2_key,
                    r2_key,
                    uf.content_type or None,
                    file_size,
                    url_path,
                ),
            )
            file_id = int(info.lastrowid)
            if first_uploaded_image_id is None:
                first_uploaded_image_id = file_id
            saved.append(
                {
                    "id": file_id,
                    "original_name": uf.filename or r2_key,
                    "stored_name": r2_key,
                    "size": file_size,
                    "mime": uf.content_type or None,
                    "url_path": url_path,
                }
            )
        # After all files are uploaded, set the cover if it's the first image and no cover exists
        if first_uploaded_image_id is not None:
            current_cover = cur.execute(
                "SELECT cover_file_id FROM resources WHERE id = ?", (rid,)
            ).fetchone()
            if current_cover and current_cover["cover_file_id"] is None:
                cur.execute(
                    "UPDATE resources SET cover_file_id = ? WHERE id = ?",
                    (first_uploaded_image_id, rid),
                )
                logger.info(
                    "Auto-set cover for resource %s to file %s",
                    rid,
                    first_uploaded_image_id,
                )

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        for key in created_r2_keys:
            try:
                r2.delete_object(key)
            except Exception:
                pass
        return JSONResponse(status_code=400, content={"error": "上传失败"})
    finally:
        for p in created_temp_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
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
            return JSONResponse(
                status_code=400, content={"error": "仅支持 .melsave 或 .zip"}
            )
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
                wm_u64,
                wm_i64,
                length,
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
                "resourceId": int(r["resource_id"])
                if r["resource_id"] is not None
                else None,
                "resourceSlug": r["resource_slug"],
                "resourceTitle": r["resource_title"],
                "originalName": r["original_name"],
                "urlPath": r["url_path"],
            }
            for r in rows
        ]
        try:
            logger.info(
                "wm-check: matches=%s fileIds=%s",
                len(matches),
                [m.get("fileId") for m in matches],
            )
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
        SELECT id, slug, title, description, usage, created_at, cover_file_id
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
        cover_file_id = r["cover_file_id"] if "cover_file_id" in r.keys() else None
        cover_url_path: Optional[str] = None
        if cover_file_id:
            try:
                cover_row = cur.execute(
                    """
                    SELECT url_path FROM resource_files
                    WHERE id = ? AND resource_id = ?
                    """,
                    (cover_file_id, r["id"]),
                ).fetchone()
                if cover_row:
                    cover_url_path = cover_row["url_path"]
            except Exception:
                cover_url_path = None
        files_out = []
        image_files_out = []
        for f in files:
            fd = dict(f)
            if _is_image_file(fd.get("mime"), fd.get("original_name")):
                image_files_out.append(fd)
            else:
                files_out.append(fd)
        items.append(
            {
                "id": int(r["id"]),
                "slug": r["slug"],
                "title": r["title"],
                "description": r["description"],
                "usage": r["usage"],
                "created_at": r["created_at"],
                "files": files_out,
                "imageFiles": image_files_out,
                "coverFileId": int(cover_file_id)
                if cover_file_id is not None
                else None,
                "coverUrlPath": cover_url_path,
                "shareUrl": _share_url(r["slug"]),
            }
        )
    return {"items": items}


@router.get("/api/resources/{rid}/images")
def list_resource_images(request: Request, rid: int):
    """
    列出指定资源下的所有图片文件（封面候选）。
    仅资源创建者可见，用于管理封面与展示图片。
    """
    uid, err = _require_owner(request, rid)
    if err is not None:
        if uid is None:
            return JSONResponse(status_code=401, content={"error": err})
        return JSONResponse(status_code=403, content={"error": err})
    conn = get_connection()
    cur = conn.cursor()
    res = cur.execute(
        "SELECT id, cover_file_id FROM resources WHERE id = ?",
        (rid,),
    ).fetchone()
    if not res:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    cover_file_id = res["cover_file_id"] if "cover_file_id" in res.keys() else None
    rows = cur.execute(
        """
        SELECT id, original_name, stored_name, mime, size, url_path, created_at
        FROM resource_files
        WHERE resource_id = ?
        ORDER BY id DESC
        """,
        (rid,),
    ).fetchall()
    items = []
    for r in rows:
        if not _is_image_file(r["mime"], r["original_name"]):
            continue
        items.append(
            {
                "id": int(r["id"]),
                "original_name": r["original_name"],
                "stored_name": r["stored_name"],
                "size": r["size"],
                "mime": r["mime"],
                "url_path": r["url_path"],
                "created_at": r["created_at"],
            }
        )
    return {
        "items": items,
        "coverFileId": int(cover_file_id) if cover_file_id is not None else None,
    }


@router.patch("/api/resources/{rid}")
async def update_resource(
    request: Request,
    rid: int,
    description: Optional[str] = Form(None),
    usage: Optional[str] = Form(None),
):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute(
        "SELECT id, slug, created_by FROM resources WHERE id = ?", (rid,)
    ).fetchone()
    if not r:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(r["created_by"] or 0) != uid:
        return JSONResponse(
            status_code=403, content={"error": "无法操作其他用户的资源"}
        )
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
    cur.execute(
        f"UPDATE resources SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )
    conn.commit()
    updated = cur.execute(
        "SELECT id, slug, title, description, usage, created_at FROM resources WHERE id = ?",
        (rid,),
    ).fetchone()
    return {
        **{k: updated[k] for k in updated.keys()},
        "shareUrl": _share_url(updated["slug"]),
    }


@router.delete("/api/resources/{rid}")
def delete_resource(request: Request, rid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute(
        "SELECT id, created_by FROM resources WHERE id = ?", (rid,)
    ).fetchone()
    if not r:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(r["created_by"] or 0) != uid:
        return JSONResponse(
            status_code=403, content={"error": "无法操作其他用户的资源"}
        )
    files = cur.execute(
        "SELECT stored_name FROM resource_files WHERE resource_id = ?", (rid,)
    ).fetchall()
    # Transaction-like operations
    cur.execute("DELETE FROM resource_files WHERE resource_id = ?", (rid,))
    cur.execute("DELETE FROM resources WHERE id = ?", (rid,))
    conn.commit()
    for f in files:
        stored = f["stored_name"]
        try:
            if "/" in stored:
                r2.delete_object(stored)
            else:
                path = UPLOAD_DIR / stored
                if path.exists():
                    path.unlink()
        except Exception:
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
        items.append(
            {"id": fid, "likes": int(count_map.get(fid, 0)), "liked": fid in liked_set}
        )
    return {"items": items}


@router.post("/api/files/{fid}/like")
def like_file(request: Request, fid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM resource_files WHERE id = ?", (fid,)
    ).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    # idempotent like
    cur.execute(
        "INSERT OR IGNORE INTO resource_file_likes (file_id, user_id) VALUES (?, ?)",
        (fid, uid),
    )
    conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_file_likes WHERE file_id = ?", (fid,)
    ).fetchone()["c"]
    return {"liked": True, "likes": int(total)}


@router.delete("/api/files/{fid}/like")
def unlike_file(request: Request, fid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id FROM resource_files WHERE id = ?", (fid,)
    ).fetchone()
    if not exists:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    cur.execute(
        "DELETE FROM resource_file_likes WHERE file_id = ? AND user_id = ?", (fid, uid)
    )
    conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_file_likes WHERE file_id = ?", (fid,)
    ).fetchone()["c"]
    return {"liked": False, "likes": int(total)}


@router.get("/api/resources/{slug}")
def get_resource(slug: str):
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute(
        """
        SELECT r.*, u.username AS author_username, u.avatar_url AS author_avatar
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
    cover_file_id = r["cover_file_id"] if "cover_file_id" in r.keys() else None
    cover_url_path = None
    files = list(files)
    files_out = []
    image_files_out = []
    for f in files:
        fd = dict(f)
        if _is_image_file(fd.get("mime"), fd.get("original_name")):
            image_files_out.append(fd)
        else:
            files_out.append(fd)
    if cover_file_id:
        try:
            for f in image_files_out:
                if int(f.get("id")) == int(cover_file_id):
                    cover_url_path = f.get("url_path")
                    break
        except Exception:
            cover_url_path = None
    data = {
        **{k: r[k] for k in r.keys()},
        "files": files_out,
        "imageFiles": image_files_out,
        "shareUrl": _share_url(r["slug"]),
        "coverFileId": int(cover_file_id) if cover_file_id is not None else None,
        "coverUrlPath": cover_url_path,
        "author_avatar": r["author_avatar"] or "",
        "tags": tags_from_json(r["tags"] if "tags" in r.keys() else None),
    }
    return data


@router.get("/api/resources")
def list_resources(
    q: str = Query(default=""),
    page: int = Query(default=1),
    pageSize: int = Query(default=12),
):
    q = (q or "").strip()
    page = max(1, int(page or 1))
    page_size = min(50, max(1, int(pageSize or 12)))
    offset = (page - 1) * page_size
    conn = get_connection()
    cur = conn.cursor()
    if q:
        where = "WHERE r.title LIKE ? OR r.description LIKE ? OR r.tags LIKE ? OR EXISTS (SELECT 1 FROM resource_files rf WHERE rf.resource_id = r.id AND rf.original_name LIKE ?)"
        args: List = [f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"]
    else:
        where = ""
        args = []
    # Use the same table alias as in the items query to avoid 'no such column: r.title'
    total = cur.execute(
        f"SELECT COUNT(1) as c FROM resources r {where}", tuple(args)
    ).fetchone()["c"]
    items = cur.execute(
        f"""
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
          u.avatar_url AS author_avatar,
          cf.url_path AS cover_url_path
        FROM resources r
        LEFT JOIN users u ON u.id = r.created_by
        LEFT JOIN resource_files cf ON cf.id = r.cover_file_id
        {where}
        ORDER BY r.id DESC
        LIMIT ? OFFSET ?
        """,
        (*args, page_size, offset),
    ).fetchall()
    items_out = []
    for row in items:
        d = dict(row)
        cover_file_id = d.pop("cover_file_id", None)
        cover_url_path = d.pop("cover_url_path", None)
        # Preserve existing fields; add camelCase cover metadata
        d["coverFileId"] = int(cover_file_id) if cover_file_id is not None else None
        d["coverUrlPath"] = cover_url_path
        d["author_avatar"] = d.pop("author_avatar", None) or ""
        d["tags"] = tags_from_json(d.pop("tags", None))
        items_out.append(d)
    return {"items": items_out, "page": page, "pageSize": page_size, "total": total}


@router.get("/api/creators/{username}/stats")
def get_creator_stats(username: str):
    conn = get_connection()
    cur = conn.cursor()
    user = cur.execute("SELECT id, username, avatar_url, signature FROM users WHERE username = ?", (username,)).fetchone()
    if not user:
        return JSONResponse(status_code=404, content={"error": "用户不存在"})
    row = cur.execute(
        """
        SELECT
          COUNT(r.id) AS resource_count,
          COALESCE(SUM(r.download_count), 0) AS total_downloads
        FROM resources r
        WHERE r.created_by = ?
        """,
        (user["id"],),
    ).fetchone()
    resources = cur.execute(
        """
        SELECT r.id, r.slug, r.title, r.download_count, r.created_at
        FROM resources r
        WHERE r.created_by = ?
        ORDER BY r.download_count DESC
        LIMIT 10
        """,
        (user["id"],),
    ).fetchall()
    return {
        "user": {
            "id": user["id"],
            "username": user["username"],
            "avatar_url": user["avatar_url"] or "",
            "signature": user["signature"] or "",
        },
        "resource_count": row["resource_count"],
        "total_downloads": row["total_downloads"],
        "top_resources": [dict(r) for r in resources],
    }


@router.post("/api/resources/optimize")
async def optimize_resource_content(request: Request):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "无效请求"})
    title = (body or {}).get("title", "").strip()
    description = (body or {}).get("description", "").strip()
    usage = (body or {}).get("usage", "").strip()
    resource_id = (body or {}).get("resourceId")
    if not title:
        return JSONResponse(status_code=400, content={"error": "标题不能为空"})
    from .llm2 import optimize_content, tags_to_json
    result = optimize_content(title, description, usage)
    if result.get("tags") and resource_id:
        try:
            rid = int(resource_id)
            conn = get_connection()
            conn.execute("UPDATE resources SET tags = ? WHERE id = ?", (tags_to_json(result["tags"]), rid))
            conn.commit()
        except Exception:
            pass
    return result


@router.post("/api/resources/{rid}/classify")
async def classify_resource_endpoint(request: Request, rid: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id, title, description, created_by FROM resources WHERE id = ?", (rid,)
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "资源不存在"})
    if int(row["created_by"] or 0) != uid:
        return JSONResponse(status_code=403, content={"error": "无权操作"})
    from .llm2 import classify_resource, tags_to_json
    tags = classify_resource(row["title"], row["description"] or "")
    conn.execute("UPDATE resources SET tags = ? WHERE id = ?", (tags_to_json(tags), rid))
    conn.commit()
    return {"tags": tags}


@router.patch("/api/resources/{rid}/cover")
async def set_resource_cover(
    request: Request,
    rid: int,
    fileId: Optional[int] = Body(default=None, embed=True),
):
    """
    设置或清除资源封面图片。
    - 需要登录并且必须是资源创建者。
    - fileId 为 null 或省略时表示清除封面。
    """
    uid, err = _require_owner(request, rid)
    if err is not None:
        if uid is None:
            return JSONResponse(status_code=401, content={"error": err})
        status = 404 if "不存在" in err else 403
        return JSONResponse(status_code=status, content={"error": err})
    conn = get_connection()
    cur = conn.cursor()
    # If a fileId is provided, ensure it belongs to this resource
    if fileId is not None:
        row = cur.execute(
            "SELECT id FROM resource_files WHERE id = ? AND resource_id = ?",
            (fileId, rid),
        ).fetchone()
        if not row:
            return JSONResponse(status_code=400, content={"error": "文件不属于该资源"})
    try:
        cur.execute(
            "UPDATE resources SET cover_file_id = ? WHERE id = ?",
            (fileId, rid),
        )
        conn.commit()
    except Exception:
        return JSONResponse(status_code=500, content={"error": "更新封面失败"})
    # Return simple ack to keep payload small for this update route
    return {"ok": True, "coverFileId": fileId}


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
        items.append(
            {"id": rid, "likes": int(count_map.get(rid, 0)), "liked": rid in liked_set}
        )
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
    already_liked = cur.execute(
        "SELECT 1 FROM resource_likes WHERE resource_id = ? AND user_id = ?",
        (rid, uid),
    ).fetchone()
    if not already_liked:
        cur.execute(
            "INSERT INTO resource_likes (resource_id, user_id) VALUES (?, ?)",
            (rid, uid),
        )
        try:
            owner_row = cur.execute(
                "SELECT created_by, title FROM resources WHERE id = ?",
                (rid,),
            ).fetchone()
            if owner_row and owner_row["created_by"] is not None:
                create_notification(
                    user_id=int(owner_row["created_by"]),
                    actor_id=uid,
                    notif_type="resource_like",
                    resource_id=rid,
                    content=owner_row["title"],
                )
        except Exception:
            pass
        conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_likes WHERE resource_id = ?", (rid,)
    ).fetchone()["c"]
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
    cur.execute(
        "DELETE FROM resource_likes WHERE resource_id = ? AND user_id = ?", (rid, uid)
    )
    conn.commit()
    total = cur.execute(
        "SELECT COUNT(1) as c FROM resource_likes WHERE resource_id = ?", (rid,)
    ).fetchone()["c"]
    return {"liked": False, "likes": int(total)}


@router.get("/api/files/{fid}/download")
def download_file(fid: int):
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT original_name, stored_name, resource_id FROM resource_files WHERE id = ?", (fid,)
    ).fetchone()
    if not row:
        return JSONResponse(status_code=404, content={"error": "文件不存在"})
    # Increment download count on the parent resource
    try:
        if row["resource_id"]:
            cur.execute("UPDATE resources SET download_count = download_count + 1 WHERE id = ?", (row["resource_id"],))
            conn.commit()
    except Exception:
        pass
    stored = row["stored_name"]
    filename = row["original_name"]
    # If stored_name looks like an R2 key (contains /), generate presigned URL
    if "/" in stored:
        try:
            presigned = r2.get_presigned_download_url(stored, filename)
            return RedirectResponse(url=presigned, status_code=302)
        except Exception:
            return JSONResponse(status_code=500, content={"error": "下载失败"})
    # Legacy: file still on local disk
    path = UPLOAD_DIR / stored
    if not path.exists():
        return JSONResponse(status_code=404, content={"error": "文件丢了"})
    from urllib.parse import quote

    safe_name = _safe_ascii_filename(filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{safe_name}\"; filename*=UTF-8''{quote(filename)}",
        "X-Content-Type-Options": "nosniff",
    }
    return FileResponse(path, headers=headers, media_type="application/octet-stream")
