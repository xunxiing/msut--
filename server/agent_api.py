import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, Body, Query, Request
from fastapi.responses import JSONResponse

from .auth import get_current_user
from .db import get_connection
from .melsave import generate_melsave_bytes
from .utils import nanoid


router = APIRouter()
logger = logging.getLogger("msut.agent")

BASE_DIR = Path(__file__).resolve().parent
PROMPT_FILES = [
    BASE_DIR / "agent" / "全自动生成.txt",
    BASE_DIR / "agent" / "芯片教程.txt",
]
UPLOADS_DIR = BASE_DIR / "uploads"

AGENT_API_BASE = (os.getenv("AGENT_API_BASE") or os.getenv("RAG_API_BASE") or "").strip().rstrip("/")
AGENT_API_KEY = (os.getenv("AGENT_API_KEY") or os.getenv("RAG_API_KEY") or "").strip()
AGENT_MODEL = (
    os.getenv("AGENT_MODEL")
    or os.getenv("AGENTMODEL")
    or os.getenv("AGENT_MODEL_NAME")
    or ""
).strip()

TOOL_SCHEMA: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "generate_melsave",
            "description": "根据 DSL 代码生成 .melsave 存档文件。当用户需要产出芯片文件时必须调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dsl": {
                        "type": "string",
                        "description": "完整的 Python DSL 代码，符合芯片教程规范，生成后会打包为 .melsave 文件。",
                    }
                },
                "required": ["dsl"],
            },
        },
    }
]

MAX_TOOL_LOOPS = 3
HISTORY_LIMIT = 30


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        return int(payload["uid"])  # type: ignore[index]
    except Exception:
        return None


def _load_prompt() -> str:
    parts: List[str] = []
    for p in PROMPT_FILES:
        try:
            text = p.read_text(encoding="utf-8")
            if text.strip():
                parts.append(text.strip())
        except Exception:
            continue
    if parts:
        return "\n\n".join(parts)
    return "你是 MSUT 的自动化芯片生成代理，请用中文回答，并在需要生成 .melsave 时调用生成工具。"


def _session_owned(conn, session_id: int, user_id: int) -> bool:
    cur = conn.cursor()
    row = cur.execute(
        "SELECT 1 FROM agent_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    return bool(row)


def _insert_message(
    conn,
    session_id: int,
    role: str,
    content: str,
    *,
    tool_name: Optional[str] = None,
    tool_args: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    run_id: Optional[int] = None,
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO agent_messages (session_id, run_id, role, content, tool_name, tool_args, tool_call_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, run_id, role, content, tool_name, tool_args, tool_call_id),
    )
    return int(cur.lastrowid)


def _serialize_message_row(row) -> dict:
    content = row["content"] or ""
    payload = None
    try:
        payload = json.loads(content)
    except Exception:
        payload = None
    return {
        "id": int(row["id"]),
        "runId": int(row["run_id"]) if row["run_id"] is not None else None,
        "role": row["role"],
        "content": content,
        "payload": payload,
        "toolName": row["tool_name"],
        "toolArgs": row["tool_args"],
        "toolCallId": row["tool_call_id"],
        "created_at": row["created_at"],
    }


def _history_messages(conn, session_id: int) -> List[dict]:
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT id, role, content, tool_name, tool_args, tool_call_id, run_id, created_at
        FROM agent_messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()
    messages: List[dict] = []
    for r in rows or []:
        item = {
            "role": r["role"],
            "content": r["content"] or "",
        }
        if r["role"] == "tool" and r["tool_call_id"]:
            item["tool_call_id"] = r["tool_call_id"]
        messages.append(item)
    if len(messages) > HISTORY_LIMIT:
        return messages[-HISTORY_LIMIT:]
    return messages


def _agent_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if AGENT_API_KEY:
        headers["Authorization"] = f"Bearer {AGENT_API_KEY}"
    return headers


def _call_llm(messages: List[dict]) -> dict:
    if not AGENT_API_BASE or not AGENT_MODEL:
        raise RuntimeError("agent LLM 未配置")
    body = {
        "model": AGENT_MODEL,
        "messages": messages,
        "tools": TOOL_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.35,
        # moonshot 兼容接口支持启用思维链，但为兼容其他实现使用布尔控制
        "enable_thinking": True,
    }
    url = f"{AGENT_API_BASE}/chat/completions"
    resp = requests.post(url, headers=_agent_headers(), data=json.dumps(body, ensure_ascii=False), timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 无返回")
    msg = choices[0].get("message") or {}
    return msg


def _store_tool_file(dsl: str) -> dict:
    """Generate a .melsave file and persist it under uploads/agent."""
    result = generate_melsave_bytes(dsl)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    agent_dir = UPLOADS_DIR / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"agent_{nanoid(6)}_{result.filename}"
    dest = agent_dir / stored_name
    dest.write_bytes(result.data)
    return {
        "ok": True,
        "type": "melsave",
        "message": "已生成 .melsave 文件",
        "file": {
            "filename": result.filename,
            "storedName": stored_name,
            "size": len(result.data),
            "url": f"/uploads/agent/{stored_name}",
        },
    }


def _run_agent_once(conn, session_id: int, run_id: int) -> Dict[str, Optional[str]]:
    cur = conn.cursor()
    prompt = _load_prompt()
    history = _history_messages(conn, session_id)
    messages = [{"role": "system", "content": prompt}] + history

    result_url: Optional[str] = None
    result_name: Optional[str] = None

    loop = 0
    while loop < MAX_TOOL_LOOPS:
        loop += 1
        msg = _call_llm(messages)
        tool_calls = msg.get("tool_calls") or []
        content = msg.get("content") or ""
        _insert_message(
            conn,
            session_id,
            "assistant",
            content,
            tool_name=None,
            tool_args=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            run_id=run_id,
        )
        messages.append(msg)

        if not tool_calls:
            break

        for call in tool_calls:
            fn = (call.get("function") or {}).get("name") or ""
            args_raw = (call.get("function") or {}).get("arguments") or "{}"
            try:
                args_obj = json.loads(args_raw)
            except Exception:
                args_obj = {}
            call_id = call.get("id") or f"call_{loop}_{nanoid(4)}"

            if fn == "generate_melsave":
                dsl = args_obj.get("dsl") or ""
                try:
                    tool_res = _store_tool_file(str(dsl))
                    file_info = tool_res.get("file") or {}
                    result_url = file_info.get("url") or result_url
                    result_name = file_info.get("filename") or result_name
                except Exception as e:
                    tool_res = {"ok": False, "error": f"生成失败: {e}"}
            else:
                tool_res = {"ok": False, "error": f"未知工具: {fn}"}

            tool_content = json.dumps(tool_res, ensure_ascii=False)
            _insert_message(
                conn,
                session_id,
                "tool",
                tool_content,
                tool_name=fn,
                tool_args=args_raw,
                tool_call_id=call_id,
                run_id=run_id,
            )
            messages.append({"role": "tool", "tool_call_id": call_id, "content": tool_content})
    return {"url": result_url, "name": result_name}


def _mark_run_status(conn, run_id: int, status: str, *, session_id: int, result: Optional[dict] = None, error: Optional[str] = None):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE agent_runs
        SET status = ?, result_path = ?, result_name = ?, error = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            status,
            (result or {}).get("url") if result else None,
            (result or {}).get("name") if result else None,
            error,
            run_id,
        ),
    )
    cur.execute(
        """
        UPDATE agent_sessions
        SET last_status = ?, last_error = ?
        WHERE id = ?
        """,
        (status, error, session_id),
    )
    conn.commit()


def _process_agent_run(run_id: int):
    conn = get_connection()
    cur = conn.cursor()
    run_row = cur.execute(
        """
        SELECT id, session_id, user_id, status
        FROM agent_runs
        WHERE id = ?
        """,
        (run_id,),
    ).fetchone()
    if not run_row:
        return
    session_id = int(run_row["session_id"])

    try:
        cur.execute(
            "UPDATE agent_runs SET status = 'running', updated_at = datetime('now') WHERE id = ?",
            (run_id,),
        )
        cur.execute(
            "UPDATE agent_sessions SET last_status = 'running', last_error = NULL WHERE id = ?",
            (session_id,),
        )
        conn.commit()

        result = _run_agent_once(conn, session_id, run_id)
        _mark_run_status(conn, run_id, "succeeded", session_id=session_id, result=result)
    except Exception as e:
        err = str(e)
        try:
            logger.exception("agent run failed run_id=%s error=%s", run_id, err)
        except Exception:
            pass
        _mark_run_status(conn, run_id, "failed", session_id=session_id, error=err)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/api/agent/sessions")
def create_session(request: Request, body: dict = Body(default={})):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    title = ""
    if isinstance(body, dict):
        title = str(body.get("title") or "").strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO agent_sessions (user_id, title, last_status)
            VALUES (?, ?, 'idle')
            """,
            (uid, title or None),
        )
        sid = int(cur.lastrowid)
        conn.commit()
        return {
            "id": sid,
            "title": title,
            "last_status": "idle",
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/api/agent/sessions")
def list_sessions(request: Request):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
              s.id, s.title, s.last_status, s.last_error, s.created_at, s.updated_at,
              (SELECT content FROM agent_messages m WHERE m.session_id = s.id ORDER BY m.id DESC LIMIT 1) AS last_content
            FROM agent_sessions s
            WHERE s.user_id = ?
            ORDER BY s.updated_at DESC, s.id DESC
            """,
            (uid,),
        ).fetchall()
        items: List[dict] = []
        for r in rows or []:
            items.append(
                {
                    "id": int(r["id"]),
                    "title": r["title"] or "",
                    "last_status": r["last_status"] or "",
                    "last_error": r["last_error"],
                    "last_message": r["last_content"] or "",
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                }
            )
        return {"items": items}
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/api/agent/sessions/{session_id}/messages")
def list_session_messages(request: Request, session_id: int, limit: int = Query(50, ge=1, le=200)):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    try:
        if not _session_owned(conn, session_id, uid):
            return JSONResponse(status_code=404, content={"error": "会话不存在"})
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT id, role, content, tool_name, tool_args, tool_call_id, run_id, created_at
            FROM agent_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        items = [_serialize_message_row(r) for r in (rows or [])]
        items.reverse()
        return {"items": items}
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.post("/api/agent/ask")
def agent_ask(
    request: Request,
    background_tasks: BackgroundTasks,
    body: dict = Body(...),
):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "请求格式错误"})
    message = str(body.get("message") or "").strip()
    if not message:
        return JSONResponse(status_code=400, content={"error": "提问内容不能为空"})

    session_id = body.get("sessionId")
    conn = get_connection()
    try:
        cur = conn.cursor()
        created_new = False
        sid: Optional[int]
        try:
            sid = int(session_id)
        except Exception:
            sid = None
        if sid is not None:
            if not _session_owned(conn, sid, uid):
                return JSONResponse(status_code=404, content={"error": "会话不存在"})
        else:
            cur.execute(
                "INSERT INTO agent_sessions (user_id, title, last_status) VALUES (?, ?, 'idle')",
                (uid, message[:40] or None),
            )
            sid = int(cur.lastrowid)
            created_new = True

        cur.execute(
            """
            INSERT INTO agent_runs (session_id, user_id, status, model)
            VALUES (?, ?, 'pending', ?)
            """,
            (sid, uid, AGENT_MODEL or None),
        )
        run_id = int(cur.lastrowid)
        _insert_message(conn, sid, "user", message, run_id=run_id)
        cur.execute(
            "UPDATE agent_sessions SET last_status = 'pending', last_error = NULL WHERE id = ?",
            (sid,),
        )
        conn.commit()

        background_tasks.add_task(_process_agent_run, run_id)

        return {"sessionId": sid, "runId": run_id, "created": created_new, "status": "pending"}
    finally:
        try:
            conn.close()
        except Exception:
            pass


@router.get("/api/agent/runs/{run_id}")
def get_run_status(request: Request, run_id: int):
    uid = _require_user_id(request)
    if uid is None:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT r.id, r.session_id, r.status, r.result_path, r.result_name, r.error, r.created_at, r.updated_at, s.user_id
            FROM agent_runs r
            JOIN agent_sessions s ON s.id = r.session_id
            WHERE r.id = ?
            """,
            (run_id,),
        ).fetchone()
        if not row or int(row["user_id"]) != uid:
            return JSONResponse(status_code=404, content={"error": "任务不存在"})
        return {
            "runId": int(row["id"]),
            "sessionId": int(row["session_id"]),
            "status": row["status"],
            "resultUrl": row["result_path"],
            "resultName": row["result_name"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
