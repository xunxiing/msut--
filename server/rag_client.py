import json
import logging
import os
from typing import List, Optional, Sequence

import requests


logger = logging.getLogger("msut.rag")


RAG_API_BASE = (os.getenv("RAG_API_BASE") or os.getenv("RAG_APIBASE") or "").strip().rstrip("/")
RAG_API_KEY = (os.getenv("RAG_API_KEY") or os.getenv("RAG_APIKEY") or "").strip()
# 独立的 LLM 模型与 Embedding 模型，保持对旧变量 RAG_MODEL 的兼容
RAG_LLM_MODEL = (
    os.getenv("RAG_LLM_MODEL")
    or os.getenv("RAG_MODEL")
    or os.getenv("RAG_MODEL_NAME")
    or ""
).strip()
RAG_EMBED_MODEL = (
    os.getenv("RAG_EMBED_MODEL")
    or os.getenv("RAG_EMBED_MODEL_NAME")
    or ""
).strip()

try:
    _dim_raw = os.getenv("RAG_EMBED_DIM") or os.getenv("RAG_DIM") or ""
    RAG_EMBED_DIM: Optional[int] = int(_dim_raw) if _dim_raw.strip() else None
except Exception:
    RAG_EMBED_DIM = None


def is_rag_configured() -> bool:
    """Return True if basic RAG configuration is present."""
    return bool(RAG_API_BASE and RAG_API_KEY and RAG_LLM_MODEL and RAG_EMBED_MODEL)


def _auth_headers() -> dict:
    headers = {
        "Authorization": f"Bearer {RAG_API_KEY}",
        "Content-Type": "application/json",
    }
    return headers


def get_embedding(text: str) -> Optional[List[float]]:
    """Call an OpenAI-compatible embeddings endpoint and return the vector.

    This assumes the provider exposes POST {base}/embeddings with the usual schema:
      { "model": "...", "input": "..." }
    and responds with:
      { "data": [{ "embedding": [...] }] }
    """
    if not is_rag_configured():
        return None
    if not text.strip():
        return None
    url = f"{RAG_API_BASE}/embeddings"
    try:
        resp = requests.post(
            url,
            headers=_auth_headers(),
            data=json.dumps({"model": RAG_EMBED_MODEL, "input": text}),
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or []
        if not data:
            return None
        emb = data[0].get("embedding")
        if not isinstance(emb, Sequence):
            return None
        vec = [float(x) for x in emb]
        if RAG_EMBED_DIM and len(vec) != RAG_EMBED_DIM:
            # Do not hard-fail; log and continue best-effort
            try:
                logger.warning(
                    "rag: embedding dim mismatch expected=%s got=%s",
                    RAG_EMBED_DIM,
                    len(vec),
                )
            except Exception:
                pass
        return vec
    except Exception as e:
        try:
            logger.exception("rag: embedding request failed: %s", e)
        except Exception:
            pass
        return None


def chat_answer(question: str, contexts: Sequence[str]) -> Optional[str]:
    """Call an OpenAI-compatible chat completion endpoint with RAG contexts.

    Expects POST {base}/chat/completions with:
      { "model": "...", "messages": [...] }
    """
    if not is_rag_configured():
        return None
    q = (question or "").strip()
    if not q:
        return None
    system_prompt = (
        "你是一个基于教程文档回答问题的中文助手。"
        "请严格依赖给定的教程内容进行回答，如果资料中没有相关信息，直接说明“文档里没有明确说明”。"
    )
    ctx_text = ""
    for i, chunk in enumerate(contexts):
        if not chunk:
            continue
        ctx_text += f"\n[片段 {i + 1}]\n{chunk}\n"
    user_prompt = f"用户问题：{q}\n\n以下是与问题相关的教程片段，仅供参考：\n{ctx_text}\n请用简体中文回答。"
    body = {
        "model": RAG_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    url = f"{RAG_API_BASE}/chat/completions"
    try:
        resp = requests.post(url, headers=_auth_headers(), data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        return str(content).strip() or None
    except Exception as e:
        try:
            logger.exception("rag: chat request failed: %s", e)
        except Exception:
            pass
        return None


def optimize_chunk_text(raw_chunk: str) -> Optional[str]:
    """Use the LLM to lightly rewrite a tutorial chunk for better retrieval.

    The goal is to keep semantics but make the text cleaner and more structured,
    so it works better as a knowledge block in RAG.
    """
    if not is_rag_configured():
        return None
    text = (raw_chunk or "").strip()
    if not text:
        return None
    system_prompt = (
        "你是一个帮助整理技术教程文档的助手。"
        "在保持技术含义不变的前提下，对给定片段进行适度改写："
        "让结构更清晰、表述更规范，便于后续检索和问答。"
        "不要凭空编造新的内容，也不要输出解释说明，只返回改写后的文本。"
    )
    user_prompt = (
        "请对下面这一段教程内容做改写优化，使其更适合作为知识块：\n\n"
        f"{text}"
    )
    body = {
        "model": RAG_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }
    url = f"{RAG_API_BASE}/chat/completions"
    try:
        resp = requests.post(url, headers=_auth_headers(), data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        cleaned = str(content).strip()
        return cleaned or None
    except Exception as e:
        try:
            logger.exception("rag: optimize_chunk_text failed: %s", e)
        except Exception:
            pass
        return None


def name_chunk_title(raw_chunk: str, tutorial_title: Optional[str] = None) -> Optional[str]:
    """Generate a short, human-friendly title for a chunk using the LLM.

    The title is intended for navigation UI (类似目录的小节标题), not for search.
    """
    if not is_rag_configured():
        return None
    text = (raw_chunk or "").strip()
    if not text:
        return None
    system_prompt = (
        "你是一个文档结构整理助手，负责为教程内容片段生成简短的小节标题。"
        "要求：1）标题为简体中文；2）尽量不超过 16 个字；3）能概括该片段的主题；"
        "4）不要添加序号或引号，不要输出解释说明，只返回标题本身。"
    )
    if tutorial_title:
        user_prefix = f"整篇教程标题为「{tutorial_title}」。"
    else:
        user_prefix = ""
    user_prompt = (
        f"{user_prefix}下面是一段教程内容，请为这一段生成一个合适的小节标题：\n\n"
        f"{text}"
    )
    body = {
        "model": RAG_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }
    url = f"{RAG_API_BASE}/chat/completions"
    try:
        resp = requests.post(url, headers=_auth_headers(), data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        title = str(content).strip()
        # Best-effort length trim
        if len(title) > 20:
            title = title[:20].rstrip()
        return title or None
    except Exception as e:
        try:
            logger.exception("rag: name_chunk_title failed: %s", e)
        except Exception:
            pass
        return None
