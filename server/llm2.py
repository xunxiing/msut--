import json
import os
from typing import List, Optional

import requests

_LLM2_BASE = os.getenv("LLM2_API_BASE", "").rstrip("/")
_LLM2_KEY = os.getenv("LLM2_API_KEY", "")
_LLM2_MODEL = os.getenv("LLM2_MODEL", "gptoss-120b")

_SYSTEM_PROMPT = """你是一个甜瓜游乐场模组分类助手。根据用户提供的模组标题和描述，生成 1-5 个简短的中文标签。

规则：
1. 标签必须简洁（2-6个字），中文为主
2. 从这些维度考虑：类型（如 飞机/坦克/建筑/角色/武器/载具）、风格（如 写实/Q版/科幻）、功能（如 物理机关/场景/特效）
3. 返回 JSON 数组，如 ["飞机","科幻","军事"]
4. 不要解释，只返回 JSON 数组"""

_PRESET_TAGS = [
    "飞机", "坦克", "汽车", "舰船", "建筑", "角色", "武器", "载具",
    "场景", "物理机关", "特效", "军事", "科幻", "写实", "Q版",
    "自然", "动物", "植物", "工具", "机械",
]


def _chat(messages: list, max_tokens: int = 256) -> Optional[str]:
    if not _LLM2_BASE or not _LLM2_KEY:
        return None
    try:
        r = requests.post(
            f"{_LLM2_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {_LLM2_KEY}"},
            json={
                "model": _LLM2_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        return None


def classify_resource(title: str, description: str = "") -> List[str]:
    if not title:
        return []
    user_msg = f"标题：{title}\n描述：{description or '无'}"
    raw = _chat([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ])
    if not raw:
        return []
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        tags = json.loads(text)
        if isinstance(tags, list):
            return [str(t).strip() for t in tags if str(t).strip()][:5]
    except (json.JSONDecodeError, IndexError):
        pass
    return []


def tags_to_json(tags: List[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def tags_from_json(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        tags = json.loads(raw)
        if isinstance(tags, list):
            return [str(t) for t in tags if str(t).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return []
