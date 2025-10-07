import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .auth import get_current_user
from .db import get_connection
from .utils import nanoid, now_ms, slugify_str


router = APIRouter()

PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5173")

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def _share_url(slug: str) -> str:
    return f"{PUBLIC_BASE}/share/{slug}"


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


def _save_upload(file: UploadFile, dest_dir: Path) -> Optional[Path]:
    ext = Path(file.filename or "").suffix
    stored_name = f"{now_ms()}-{nanoid()}{ext}"
    dest = dest_dir / stored_name
    size = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    try:
                        f.flush()
                    except Exception:
                        pass
                    f.close()
                    dest.unlink(missing_ok=True)
                    return None
        return dest
    except Exception:
        # Any filesystem error (e.g. PermissionError, disk full) should not crash
        # the request handler. Return None so caller can respond with { error }.
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    finally:
        try:
            file.file.close()
        except Exception:
            pass


@router.post("/api/files/upload")
def upload_to_resource(request: Request, resourceId: int = Form(...), files: List[UploadFile] = File(default=[])):
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
    for uf in files[:10]:
        dest = _save_upload(uf, UPLOAD_DIR)
        if dest is None:
            return JSONResponse(status_code=400, content={"error": "上传失败"})
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
    return {"ok": True, "files": saved}


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


@router.get("/api/resources/{slug}")
def get_resource(slug: str):
    conn = get_connection()
    cur = conn.cursor()
    r = cur.execute("SELECT * FROM resources WHERE slug = ?", (slug,)).fetchone()
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
    where = "WHERE title LIKE ? OR description LIKE ?" if q else ""
    args: List = [f"%{q}%", f"%{q}%"] if q else []
    total = cur.execute(f"SELECT COUNT(1) as c FROM resources {where}", tuple(args)).fetchone()["c"]
    items = cur.execute(
        f"""
        SELECT id, slug, title, description, created_at
        FROM resources {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (*args, page_size, offset),
    ).fetchall()
    return {"items": [dict(i) for i in items], "page": page, "pageSize": page_size, "total": total}


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
