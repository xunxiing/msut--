import json
import logging
import os
import requests
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Query, Request
from fastapi.responses import JSONResponse

from .agent.langchain_agent import AgentRunResult, run_agent_with_langchain, _load_prompt
from .auth import get_current_user
from .db import get_connection
from .melsave import generate_melsave_bytes
from .utils import nanoid


# 从环境变量中读取 Agent 配置
AGENT_MODEL = os.environ.get("AGENT_MODEL")
AGENT_API_BASE = (os.getenv("AGENT_API_BASE") or os.getenv("RAG_API_BASE") or "").strip().rstrip("/")
AGENT_API_KEY = (os.getenv("AGENT_API_KEY") or os.getenv("RAG_API_KEY") or "").strip()

# 服务器目录和上传目录
SERVER_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = SERVER_DIR / "uploads"

# Agent 工具配置
TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_melsave",
            "description": "生成 melsave 文件并保存到服务器。参数为 DSL 字符串。返回包含文件信息的字典。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dsl": {
                        "type": "string",
                        "description": "DSL 代码字符串"
                    }
                },
                "required": ["dsl"]
            }
        }
    }
]

MAX_TOOL_LOOPS = 3

router = APIRouter()
logger = logging.getLogger("msut.agent")

HISTORY_LIMIT = 30


def _require_user_id(request: Request) -> Optional[int]:
    payload = get_current_user(request)
    if not payload:
        return None
    try:
        return int(payload["uid"])  # type: ignore[index]
    except Exception:
        return None


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
    raw_content = row["content"] or ""
    content = raw_content
    payload = None
    try:
        payload = json.loads(raw_content)
    except Exception:
        payload = None

    # For assistant messages stored as JSON, map the visible text
    # back into the `content` field while keeping the full object
    # in `payload` so the frontend can optionally inspect thinking / tool_calls.
    if isinstance(payload, dict) and row["role"] == "assistant":
        visible = payload.get("visible")
        if isinstance(visible, str):
            content = visible

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
        raw_content = r["content"] or ""
        content = raw_content
        # Decode assistant messages that were stored as JSON with a
        # `visible` field so that the LLM history only sees the user-facing text.
        if r["role"] == "assistant" and raw_content.lstrip().startswith("{"):
            try:
                obj = json.loads(raw_content)
                if isinstance(obj, dict):
                    visible = obj.get("visible")
                    if isinstance(visible, str):
                        content = visible
            except Exception:
                content = raw_content
        item = {
            "role": r["role"],
            "content": content,
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


def _flatten_content(value) -> str:
    """Extract plain text from an OpenAI-style content field."""
    parts: List[str] = []
    if isinstance(value, str):
        parts.append(value)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


def _extract_delta_text(delta: dict) -> str:
    """Extract visible assistant text from a streaming delta payload.

    对于带 thinking 的模型（Kimi / DeepSeek 等），我们只显示最终内容（content），
    reasoning_content 仅用于内部思考，不直接暴露给前端，避免“思维链”和答案混在一起。
    """
    if not isinstance(delta, dict):
        return ""
    return _flatten_content(delta.get("content"))


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


def _call_llm_v2(messages: List[dict]) -> dict:
    """Call the agent LLM with SiliconFlow/OpenAI-compatible payload."""
    if not AGENT_API_BASE or not AGENT_MODEL:
        raise RuntimeError("agent LLM 未配置")

    # SiliconFlow /chat/completions 要求 messages 长度在 1-10 之间
    max_messages = 10
    trimmed = messages
    if len(trimmed) > max_messages:
        # 保留第一个（通常是 system），只截取最后若干条历史，避免超限
        trimmed = [trimmed[0]] + trimmed[-(max_messages - 1) :]

    body = {
        "model": AGENT_MODEL,
        "messages": trimmed,
        "tools": TOOL_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.35,
    }

    # deepseek-ai/DeepSeek-V3.1 系列在使用 function calling 时需要关闭 thinking
    model_lower = AGENT_MODEL.lower()
    if "deepseek-v3.1" in model_lower:
        body["enable_thinking"] = False

    url = f"{AGENT_API_BASE}/chat/completions"
    resp = None
    try:
        resp = requests.post(
            url,
            headers=_agent_headers(),
            data=json.dumps(body, ensure_ascii=False),
            timeout=120,
        )
        resp.raise_for_status()
    except Exception as e:
        err_text = ""
        if resp is not None:
            try:
                err_text = resp.text
            except Exception:
                err_text = ""
        try:
            logger.error("agent LLM request failed: %s %s", e, err_text)
        except Exception:
            pass
        raise

    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 无返回")
    msg = choices[0].get("message") or {}
    return msg


def _store_tool_file(dsl: str) -> dict:
    """Generate a .melsave file and persist it under uploads/agent."""
    try:
        logger.info("agent tool generate_melsave: dsl length=%s", len(dsl or ""))
    except Exception:
        pass
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
            "url": f"/api/uploads/agent/{stored_name}",
        },
    }


def _call_llm_stream(
    conn,
    session_id: int,
    run_id: int,
    messages: List[dict],
) -> dict:
    """Call the agent LLM with SiliconFlow streaming, updating DB incrementally."""
    if not AGENT_API_BASE or not AGENT_MODEL:
        raise RuntimeError("agent LLM 未配置")

    # SiliconFlow /chat/completions 要求 messages 长度�?1-10 之间
    max_messages = 10
    trimmed = messages
    if len(trimmed) > max_messages:
        # 保留第一个（通常�?system），只截取最后若干条历史，避免超�?
        trimmed = [trimmed[0]] + trimmed[-(max_messages - 1) :]

    body: Dict[str, object] = {
        "model": AGENT_MODEL,
        "messages": trimmed,
        "tools": TOOL_SCHEMA,
        "tool_choice": "auto",
        "temperature": 0.35,
        "stream": True,
        # 默认打开 thinking，让支持思维链的模型返回 reasoning_content；
        # 个别模型（如 DeepSeek-V3.1）在 function calling 模式下会与该参数冲突，下面再做特判关闭。
        
    }

    # deepseek-ai/DeepSeek-V3.1 系列在使用 function calling 时需要关闭 thinking
    model_lower = AGENT_MODEL.lower()
    if "deepseek-v3.1" in model_lower:
        body["enable_thinking"] = False

    url = f"{AGENT_API_BASE}/chat/completions"
    resp = None

    role = "assistant"
    full_content: str = ""
    full_thinking: str = ""
    assistant_msg_id: Optional[int] = None

    # 累积流式 function calling 的 tool_calls 片段
    tool_calls_acc: List[dict] = []

    def _assistant_content_json() -> str:
        obj: Dict[str, object] = {"visible": full_content}
        if full_thinking:
            obj["thinking"] = full_thinking
        if tool_calls_acc:
            obj["tool_calls"] = tool_calls_acc
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            # Fallback to the plain text content if JSON encoding fails.
            return full_content

    def _ensure_assistant_row() -> int:
        nonlocal assistant_msg_id
        if assistant_msg_id is None:
            assistant_msg_id = _insert_message(
                conn,
                session_id,
                "assistant",
                _assistant_content_json(),
                tool_name=None,
                tool_args=None,
                tool_call_id=None,
                run_id=run_id,
            )
            conn.commit()
        return assistant_msg_id

    try:
        resp = requests.post(
            url,
            headers=_agent_headers(),
            data=json.dumps(body, ensure_ascii=False),
            stream=True,
            timeout=120,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"

        for raw_line in resp.iter_lines(decode_unicode=False):
            if not raw_line:
                continue
            try:
                line = raw_line.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line or line == "[DONE]":
                if line == "[DONE]":
                    break
                continue
            try:
                payload = json.loads(line)
            except Exception:
                continue

            choices = payload.get("choices") or []
            if not choices:
                continue
            choice = choices[0] or {}
            delta = choice.get("delta") or {}
            if not isinstance(delta, dict):
                continue

            r = delta.get("role")
            if isinstance(r, str) and r:
                role = r

            chunk_text = _extract_delta_text(delta)
            reasoning_part = _flatten_content(delta.get("reasoning_content"))

            delta_tool_calls = delta.get("tool_calls") or []
            has_tool_delta = bool(delta_tool_calls)

            if delta_tool_calls:
                for tc in delta_tool_calls:
                    if not isinstance(tc, dict):
                        continue
                    idx = tc.get("index", 0) or 0
                    if not isinstance(idx, int) or idx < 0:
                        idx = 0
                    while len(tool_calls_acc) <= idx:
                        tool_calls_acc.append(
                            {
                                "id": None,
                                "type": None,
                                "function": {"name": None, "arguments": ""},
                            }
                        )
                    acc = tool_calls_acc[idx]
                    if not isinstance(acc, dict):
                        continue
                    tc_id = tc.get("id")
                    if isinstance(tc_id, str) and tc_id:
                        acc["id"] = tc_id
                    tc_type = tc.get("type")
                    if isinstance(tc_type, str) and tc_type:
                        acc["type"] = tc_type
                    fn_delta = tc.get("function") or {}
                    if isinstance(fn_delta, dict):
                        fn_name = fn_delta.get("name")
                        if isinstance(fn_name, str) and fn_name:
                            acc_fn = acc.get("function") or {}
                            if not isinstance(acc_fn, dict):
                                acc_fn = {"name": None, "arguments": ""}
                            acc_fn["name"] = fn_name
                            args_part = fn_delta.get("arguments")
                            if isinstance(args_part, str):
                                prev = acc_fn.get("arguments") or ""
                                acc_fn["arguments"] = f"{prev}{args_part}"
                            elif args_part is not None:
                                prev = acc_fn.get("arguments") or ""
                                acc_fn["arguments"] = f"{prev}{json.dumps(args_part, ensure_ascii=False)}"
                            acc["function"] = acc_fn

            updated = False
            if chunk_text:
                full_content += chunk_text
                updated = True
            if reasoning_part:
                full_thinking += reasoning_part
                updated = True

            if updated or has_tool_delta:
                msg_id = _ensure_assistant_row()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE agent_messages SET content = ? WHERE id = ?",
                    (_assistant_content_json(), msg_id),
                )
                conn.commit()

    except Exception as e:
        err_text = ""
        if resp is not None:
            try:
                err_text = resp.text
            except Exception:
                err_text = ""
        try:
            logger.error("agent LLM stream request failed: %s %s", e, err_text)
        except Exception:
            pass
        raise

    msg_id = _ensure_assistant_row()

    tool_calls: List[dict] = []
    for acc in tool_calls_acc:
        if not isinstance(acc, dict):
            continue
        fn_info = acc.get("function") or {}
        if not isinstance(fn_info, dict):
            continue
        fn_name = fn_info.get("name")
        if not isinstance(fn_name, str) or not fn_name:
            continue
        args_str = fn_info.get("arguments") or ""
        if not isinstance(args_str, str):
            args_str = str(args_str)
        tc = {
            "id": acc.get("id") or f"call_{nanoid(6)}",
            "type": acc.get("type") or "function",
            "function": {
                "name": fn_name,
                "arguments": args_str,
            },
        }
        tool_calls.append(tc)

    tool_args_json: Optional[str] = None
    if tool_calls:
        try:
            tool_args_json = json.dumps(tool_calls, ensure_ascii=False)
        except Exception:
            tool_args_json = None

    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_messages SET tool_args = ? WHERE id = ?",
        (tool_args_json, msg_id),
    )
    conn.commit()

    # 在日志中记录一次思维链长度，便于调试是否拿到了 reasoning_content。
    try:
        if full_thinking:
            logger.info("agent stream run_id=%s thinking_length=%s", run_id, len(full_thinking))
    except Exception:
        pass

    msg: dict = {
        "role": role,
        "content": full_content,
    }
    if full_thinking:
        # 保留完整的思考内容，便于后续在需要时从中提取 DSL 等信息。
        msg["reasoning_content"] = full_thinking
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _guess_dsl_from_messages(messages: List[dict]) -> Optional[str]:
    """Best-effort extraction of DSL code from previous assistant messages.

    在部分思维链模型（如 Kimi / DeepSeek 等）下，DSL 代码有时会只出现在
    reasoning_content（思考过程）里，而不会出现在最终 content 或工具参数中。
    这里做一个尽力而为的回溯提取：优先从代码块，其次从看起来像 DSL 的长文本中获取。
    """

    def _extract_from_text(text: str) -> Optional[str]:
        if not isinstance(text, str):
            return None
        text = text.strip()
        if not text:
            return None
        # Prefer fenced code blocks if present.
        start = text.find("```")
        if start != -1:
            end = text.rfind("```")
            if end > start:
                block = text[start + 3 : end]
                if "\n" in block:
                    first_line, rest = block.split("\n", 1)
                    if first_line.strip().lower().startswith("python"):
                        block = rest
                block = block.strip()
                if block:
                    return block
        # Fallback: if the text looks code-like, treat the whole content as DSL.
        if len(text) > 50:
            keywords = ("INPUT(", "OUTPUT(", "ADD_FORCE(", "MULTIPLY(", "Constant(", "velocity_split[")
            if any(k in text for k in keywords):
                return text
            # Generic heuristic: multiple assignment lines with parentheses.
            lines = [ln for ln in text.splitlines() if ln.strip()]
            code_like = sum(1 for ln in lines if "=" in ln and "(" in ln) >= 2
            if code_like:
                return text
        return None

    for m in reversed(messages):
        if m.get("role") != "assistant":
            continue
        # 同时尝试 content / reasoning_content / thinking 字段，兼容不同模型返回格式。
        for key in ("content", "reasoning_content", "thinking"):
            raw = m.get(key)
            if not isinstance(raw, str):
                continue
            dsl = _extract_from_text(raw)
            if dsl:
                return dsl
    return None


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
        # 优先使用流式接口，这样前端轮询消息时可以看到逐步生成的内容；
        # 如果网关或模型不支持流式 function calling，则回退到非流式调用。
        try:
            msg = _call_llm_stream(conn, session_id, run_id, messages)
        except Exception:
            try:
                logger.exception("agent: streaming call failed, falling back to non-streaming")
            except Exception:
                pass
            msg = _call_llm_v2(messages)
            tool_calls_for_row = msg.get("tool_calls") or []
            content_for_row = msg.get("content") or ""
            _insert_message(
                conn,
                session_id,
                "assistant",
                content_for_row,
                tool_name=None,
                tool_args=json.dumps(tool_calls_for_row, ensure_ascii=False) if tool_calls_for_row else None,
                run_id=run_id,
            )

        tool_calls = msg.get("tool_calls") or []
        messages.append(msg)

        if tool_calls:
            try:
                logger.debug("agent run_id=%s tool_calls=%s", run_id, json.dumps(tool_calls, ensure_ascii=False))
            except Exception:
                pass
        else:
            try:
                logger.debug("agent run_id=%s tool_calls empty", run_id)
            except Exception:
                pass

        if not tool_calls:
            break

        for call in tool_calls:
            fn = (call.get("function") or {}).get("name") or ""
            fn_payload = call.get("function") or {}
            args_raw = fn_payload.get("arguments") or "{}"
            try:
                args_obj = json.loads(args_raw)
            except Exception:
                args_obj = {}
            call_id = call.get("id") or f"call_{loop}_{nanoid(4)}"

            try:
                logger.debug("agent tool call fn=%s raw_args=%s", fn, args_raw)
            except Exception:
                pass

            if fn == "generate_melsave":
                dsl = args_obj.get("dsl")
                if isinstance(dsl, str):
                    dsl_str = dsl
                elif dsl is None:
                    dsl_str = ""
                else:
                    dsl_str = str(dsl)
                if not dsl_str.strip():
                    fallback_dsl = _guess_dsl_from_messages(messages)
                    if fallback_dsl:
                        try:
                            logger.warning(
                                "agent run_id=%s generate_melsave: empty dsl in tool args, using fallback from history (len=%s)",
                                run_id,
                                len(fallback_dsl),
                            )
                        except Exception:
                            pass
                        dsl_str = fallback_dsl
                        # 同步回写到工具参数里，确保前端“工具输入”展示到实际用于调用的 DSL，
                        # 而不是 `{}` 或空字串。这不会影响上游 LLM，只是用于记录和调试。
                        try:
                            args_obj = {"dsl": dsl_str}
                            args_raw = json.dumps(args_obj, ensure_ascii=False)
                            # 同时更新当前 call 对象，便于后续调试 / 日志观察
                            fn_payload["arguments"] = args_raw
                            call["function"] = fn_payload
                        except Exception:
                            # 即便序列化失败，也不影响真实的工具执行（直接用 dsl_str）
                            args_raw = dsl_str
                try:
                    tool_res = _store_tool_file(dsl_str)
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
            # OpenAI / SiliconFlow 等 function calling 协议要求在 tool 消息中同时携带
            # tool_call_id 和 name，模型才能正确将结果与对应的工具调用对齐；
            # 之前缺少 name 字段，可能导致模型拿不到工具结果又重复发起调用。
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": fn,
                    "content": tool_content,
                }
            )
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


def _run_agent_once_langchain(conn, session_id: int, run_id: int) -> Dict[str, Optional[str]]:
    history = _history_messages(conn, session_id)

    assistant_msg_id: Optional[int] = None

    def _upsert_assistant_visible(visible: str) -> None:
        """在 LangChain 流式回调中增量更新 assistant 消息。

        这里只写入 `visible` 字段，最终完整结果会在 LLM 结束后再补充 thinking / tool_calls。
        """
        nonlocal assistant_msg_id
        if not visible:
            return
        payload_obj: Dict[str, object] = {"visible": visible}
        try:
            content = json.dumps(payload_obj, ensure_ascii=False)
        except Exception:
            content = visible

        if assistant_msg_id is None:
            assistant_msg_id = _insert_message(
                conn,
                session_id,
                "assistant",
                content,
                tool_name=None,
                tool_args=None,
                run_id=run_id,
            )
        else:
            cur = conn.cursor()
            cur.execute(
                "UPDATE agent_messages SET content = ? WHERE id = ?",
                (content, assistant_msg_id),
            )
        conn.commit()

    # 使用 LangChain 版本的 Agent，并通过 on_stream_visible 回调实现“伪流式”更新
    result: AgentRunResult = run_agent_with_langchain(history, on_stream_visible=_upsert_assistant_visible)

    # LLM 完成后，用完整 payload 覆盖一次，补齐 thinking / tool_calls 等信息
    payload_obj: Dict[str, object] = {"visible": result.visible}
    if result.thinking:
        payload_obj["thinking"] = result.thinking
    if result.tool_calls:
        payload_obj["tool_calls"] = result.tool_calls

    try:
        assistant_content = json.dumps(payload_obj, ensure_ascii=False)
    except Exception:
        assistant_content = result.visible or ""

    if assistant_msg_id is None:
        assistant_msg_id = _insert_message(
            conn,
            session_id,
            "assistant",
            assistant_content,
            tool_name=None,
            tool_args=None,
            run_id=run_id,
        )
        conn.commit()
    else:
        cur = conn.cursor()
        cur.execute(
            "UPDATE agent_messages SET content = ? WHERE id = ?",
            (assistant_content, assistant_msg_id),
        )
        conn.commit()

    for record in result.tool_messages:
        try:
            tool_content = json.dumps(record.result, ensure_ascii=False)
        except Exception:
            tool_content = ""
        _insert_message(
            conn,
            session_id,
            "tool",
            tool_content,
            tool_name=record.name,
            tool_args=record.arguments_json,
            tool_call_id=record.id,
            run_id=run_id,
        )

    return {"url": result.result_url, "name": result.result_name}


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

        # 使用直连 SiliconFlow 的流式实现，以获得完整的 reasoning_content，
        # 并在 _call_llm_stream 中把思维链累积到 payload.thinking，前端可折叠查看。
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
