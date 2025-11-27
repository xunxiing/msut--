import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from ..melsave import generate_melsave_bytes
from ..utils import nanoid


logger = logging.getLogger("msut.agent.langchain")


SERVER_DIR = Path(__file__).resolve().parent.parent
PROMPT_FILES = [
    SERVER_DIR / "agent" / "全自动生成.txt",
    SERVER_DIR / "agent" / "芯片教程.txt",
]
UPLOADS_DIR = SERVER_DIR / "uploads"

AGENT_API_BASE = (os.getenv("AGENT_API_BASE") or os.getenv("RAG_API_BASE") or "").strip().rstrip("/")
AGENT_API_KEY = (os.getenv("AGENT_API_KEY") or os.getenv("RAG_API_KEY") or "").strip()
AGENT_MODEL = (
    os.getenv("AGENT_MODEL")
    or os.getenv("AGENTMODEL")
    or os.getenv("AGENT_MODEL_NAME")
    or ""
).strip()

MAX_TOOL_LOOPS = 3


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


def _flatten_content(value) -> str:
    parts: List[str] = []
    if isinstance(value, str):
        parts.append(value)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)


class _AgentStreamCallback(BaseCallbackHandler):
    """LangChain 回调：把 LLM 产生的新 token 作为可见文本流式抛出。

    - 只处理内容 token，不尝试解析 reasoning_content，避免把“思维链”暴露给前端。
    - 内部做了简单节流，避免每个 token 都写 DB。
    """

    def __init__(self, on_visible: Callable[[str], None]) -> None:
        self._on_visible = on_visible
        self._buffer = ""
        self._last_sent_len = 0

    def on_llm_start(self, *args, **kwargs) -> None:  # type: ignore[override]
        self._buffer = ""
        self._last_sent_len = 0

    def on_llm_new_token(self, token: str, *args, **kwargs) -> None:  # type: ignore[override]
        try:
            if not isinstance(token, str):
                token = str(token)
            self._buffer += token
            # 每累计一小段内容再触发一次，减少 SQLite 写入次数
            if len(self._buffer) - self._last_sent_len < 8:
                return
            self._last_sent_len = len(self._buffer)
            self._on_visible(self._buffer)
        except Exception:
            # 流式更新失败不影响主推理流程
            pass

    def on_llm_end(self, *args, **kwargs) -> None:  # type: ignore[override]
        if self._buffer and len(self._buffer) != self._last_sent_len:
            try:
                self._on_visible(self._buffer)
            except Exception:
                pass


def _build_llm(on_stream_visible: Optional[Callable[[str], None]] = None) -> ChatOpenAI:
    if not AGENT_API_BASE or not AGENT_MODEL:
        raise RuntimeError("agent LLM 未配置")

    if AGENT_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", AGENT_API_KEY)
    os.environ.setdefault("OPENAI_API_BASE", AGENT_API_BASE)

    callbacks = []
    streaming = False
    if on_stream_visible is not None:
        callbacks.append(_AgentStreamCallback(on_stream_visible))
        streaming = True

    return ChatOpenAI(
        model=AGENT_MODEL,
        temperature=0.35,
        streaming=streaming,
        callbacks=callbacks,
    )


def _store_tool_file(dsl: str) -> dict:
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
            "url": f"/uploads/agent/{stored_name}",
        },
    }


@dataclass
class ToolCallRecord:
    id: str
    name: str
    arguments_json: str
    result: dict


@dataclass
class AgentRunResult:
    visible: str
    thinking: Optional[str]
    tool_calls: List[dict]
    tool_messages: List[ToolCallRecord]
    result_url: Optional[str]
    result_name: Optional[str]


def _openai_style_tool_call(tool_call_id: str, name: str, args_json: str) -> dict:
    return {
        "id": tool_call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": args_json,
        },
    }


def _guess_dsl_from_messages(messages: List[AIMessage]) -> Optional[str]:
    def _extract_from_text(text: str) -> Optional[str]:
        if not isinstance(text, str):
            return None
        text = text.strip()
        if not text:
            return None
        # 优先从 ``` 代码块中提取
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
        # 退化为“看起来像 DSL 的长文本”
        if len(text) > 50:
            keywords = ("INPUT(", "OUTPUT(", "ADD_FORCE(", "MULTIPLY(", "Constant(", "velocity_split[")
            if any(k in text for k in keywords):
                return text
            lines = [ln for ln in text.splitlines() if ln.strip()]
            code_like = sum(1 for ln in lines if "=" in ln and "(" in ln) >= 2
            if code_like:
                return text
        return None

    for m in reversed(messages):
        text = _flatten_content(m.content)
        dsl = _extract_from_text(text)
        if dsl:
            return dsl
    return None


def run_agent_with_langchain(
    history: List[dict],
    on_stream_visible: Optional[Callable[[str], None]] = None,
) -> AgentRunResult:
    """执行一次多轮 Agent 调用。

    - history：来自 SQLite 的历史消息（已按 role/内容整理）。
    - on_stream_visible：可选回调，每当 LLM 产生可见文本增量时触发，参数为“当前累计的完整可见文本”。
      agent_api 会利用这个回调把同一条 assistant 消息在 DB 中做增量更新，从而实现前端轮询下的“伪流式”效果。
    """

    prompt = _load_prompt()
    llm = _build_llm(on_stream_visible)

    system_msg = SystemMessage(content=prompt)
    chat_history: List = []
    for item in history:
        role = item.get("role")
        content = str(item.get("content") or "")
        if not content and role != "tool":
            continue
        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_history.append(AIMessage(content=content))
        elif role == "tool":
            tool_call_id = str(item.get("tool_call_id") or "")
            chat_history.append(ToolMessage(content=content, tool_call_id=tool_call_id))

    messages: List = [system_msg] + chat_history

    tool_messages: List[ToolCallRecord] = []
    result_url: Optional[str] = None
    result_name: Optional[str] = None
    assistant_messages: List[AIMessage] = []

    @tool("generate_melsave")
    def generate_melsave_tool(dsl: str) -> dict:
        """生成 melsave 文件并保存到服务器。参数为 DSL 字符串。返回包含文件信息的字典。"""
        nonlocal result_url, result_name
        dsl_str = dsl if isinstance(dsl, str) else str(dsl)
        if not dsl_str.strip():
            fallback = _guess_dsl_from_messages(assistant_messages)
            if fallback:
                try:
                    logger.warning(
                        "agent generate_melsave: empty dsl in tool args, using fallback from history (len=%s)",
                        len(fallback),
                    )
                except Exception:
                    pass
                dsl_str = fallback
        try:
            res = _store_tool_file(dsl_str)
            file_info = res.get("file") or {}
            result_url = file_info.get("url") or result_url
            result_name = file_info.get("filename") or result_name
            return res
        except Exception as e:
            return {"ok": False, "error": f"生成失败: {e}"}

    llm_with_tools = llm.bind_tools([generate_melsave_tool])

    loop = 0
    current_ai: Optional[AIMessage] = None
    while loop < MAX_TOOL_LOOPS:
        loop += 1
        ai_msg = llm_with_tools.invoke(messages)
        assistant_messages.append(ai_msg)
        current_ai = ai_msg

        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        if not tool_calls:
            break

        for call in tool_calls:
            if not isinstance(call, dict):
                # langchain-openai 当前返回 dict 风格的 tool_calls，这里做一层防御
                try:
                    call = dict(call)  # type: ignore[arg-type]
                except Exception:
                    continue
            name = call.get("name") or ""
            args = call.get("args") or {}
            if not isinstance(args, dict):
                try:
                    args = json.loads(str(args))
                except Exception:
                    args = {}
            call_id = call.get("id") or f"call_{loop}_{nanoid(4)}"
            try:
                args_json = json.dumps(args, ensure_ascii=False)
            except Exception:
                args_json = "{}"

            if name == "generate_melsave":
                tool_result = generate_melsave_tool.invoke({"dsl": args.get("dsl", "")})
            else:
                tool_result = {"ok": False, "error": f"未知工具: {name}"}

            tool_messages.append(
                ToolCallRecord(
                    id=str(call_id),
                    name=name,
                    arguments_json=args_json,
                    result=tool_result,
                )
            )

            tool_json = json.dumps(tool_result, ensure_ascii=False)
            messages.append(
                ToolMessage(
                    content=tool_json,
                    tool_call_id=str(call_id),
                )
            )

    if current_ai is None:
        raise RuntimeError("agent LLM 无返回")

    visible = _flatten_content(current_ai.content).strip()
    thinking: Optional[str] = None
    try:
        extra = getattr(current_ai, "additional_kwargs", {}) or {}
        thinking_raw = extra.get("reasoning_content") or extra.get("thinking")
        if thinking_raw:
            thinking = _flatten_content(thinking_raw)
    except Exception:
        thinking = None

    openai_tool_calls: List[dict] = []
    for record in tool_messages:
        tc = _openai_style_tool_call(record.id, record.name, record.arguments_json)
        openai_tool_calls.append(tc)

    return AgentRunResult(
        visible=visible,
        thinking=thinking,
        tool_calls=openai_tool_calls,
        tool_messages=tool_messages,
        result_url=result_url,
        result_name=result_name,
    )
