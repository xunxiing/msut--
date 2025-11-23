import json
import os

import requests


def main() -> None:
    base = (os.getenv("AGENT_API_BASE") or os.getenv("RAG_API_BASE") or "").strip().rstrip("/")
    key = (os.getenv("AGENT_API_KEY") or os.getenv("RAG_API_KEY") or "").strip()
    model = (os.getenv("AGENT_MODEL") or "").strip()
    if not base or not key or not model:
        print("missing config")
        return

    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是一个测试代理，请调用 generate_melsave 工具，并把我给你的 DSL 原样放到 dsl 字段里。",
            },
            {
                "role": "user",
                "content": "帮我为一个简单的阻尼芯片生成 DSL，直接调用工具，不要解释。",
            },
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "generate_melsave",
                    "description": "测试工具，参数是 dsl 字符串。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dsl": {"type": "string"},
                        },
                        "required": ["dsl"],
                    },
                },
            }
        ],
        "tool_choice": "auto",
        "temperature": 0.1,
        # 尝试保留默认 thinking 行为，观察返回结构
        "stream": True,
    }

    print("POST", url, "model=", model)
    with requests.post(url, headers=headers, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), stream=True, timeout=60) as resp:
        print("status", resp.status_code)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        for i, raw_line in enumerate(resp.iter_lines(decode_unicode=False), start=1):
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line or line == "[DONE]":
                print("LINE", i, "END", line)
                break
            try:
                payload = json.loads(line)
            except Exception:
                print("LINE", i, "RAW", line[:200])
                continue
            # 只打印精简后的关键信息，避免刷屏
            choices = payload.get("choices") or []
            if not choices:
                print("LINE", i, "NO_CHOICES", payload)
                continue
            delta = (choices[0] or {}).get("delta") or {}
            info = {
                "has_content": bool(delta.get("content")),
                "has_reasoning": bool(delta.get("reasoning_content")),
                "tool_calls": delta.get("tool_calls"),
            }
            print("LINE", i, "DELTA", json.dumps(info, ensure_ascii=False))
            if i > 40:
                print("... truncated after 40 lines")
                break


if __name__ == "__main__":
    main()

