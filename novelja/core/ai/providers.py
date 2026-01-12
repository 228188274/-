from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import requests


ProviderName = Literal["deepseek", "zhipu"]


class AiError(RuntimeError):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass
class ChatRequest:
    provider: ProviderName
    api_key: str
    model: str
    prompt: str
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout_seconds: int = 60


def _openai_like_chat_completion(
    *,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int,
) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
    except requests.RequestException as e:
        raise AiError("NETWORK", f"网络错误：{e}") from e

    if resp.status_code in (401, 403):
        raise AiError("AUTH", "鉴权失败：请检查 API Key")
    if resp.status_code == 429:
        raise AiError("RATE_LIMIT", "请求过于频繁/触发限流，请稍后重试")
    if resp.status_code >= 400:
        raise AiError("UNKNOWN", f"请求失败：HTTP {resp.status_code} {resp.text[:300]}")

    try:
        data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception as e:
        raise AiError("UNKNOWN", f"响应解析失败：{e}，原始响应：{resp.text[:300]}") from e


def chat(req: ChatRequest) -> str:
    provider = req.provider
    base = (req.base_url or "").strip()

    if provider == "deepseek":
        # DeepSeek: OpenAI compatible
        url = base or "https://api.deepseek.com/v1/chat/completions"
        model = req.model or "deepseek-chat"
        return _openai_like_chat_completion(
            url=url,
            api_key=req.api_key,
            model=model,
            prompt=req.prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            timeout_seconds=req.timeout_seconds,
        )

    if provider == "zhipu":
        # 智谱：新版本也提供 openai-like chat/completions
        url = base or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        model = req.model or "glm-4-flash"
        return _openai_like_chat_completion(
            url=url,
            api_key=req.api_key,
            model=model,
            prompt=req.prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            timeout_seconds=req.timeout_seconds,
        )

    raise AiError("UNKNOWN", f"不支持的提供方：{provider}")


def test_connection(provider: ProviderName, api_key: str, base_url: str = "", model: str = "") -> str:
    prompt = "请只回复：OK"
    out = chat(ChatRequest(provider=provider, api_key=api_key, base_url=base_url, model=model, prompt=prompt, max_tokens=16))
    return out

