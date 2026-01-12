from __future__ import annotations

from dataclasses import dataclass

import json

from novelja.core.ai.prompts import agent_change_list_prompt, next_preview_prompt, polish_prompt, summarize_prompt
from novelja.core.ai.providers import ChatRequest, ProviderName, chat
from novelja.core.security import load_ai_settings, load_api_key


@dataclass
class AiContext:
    provider: ProviderName
    model: str
    base_url: str
    api_key: str


def load_ai_context() -> AiContext | None:
    s = load_ai_settings()
    provider = str(s.provider or "deepseek").strip().lower()
    if provider not in ("deepseek", "zhipu"):
        return None
    key = load_api_key(provider)
    if not key:
        return None
    return AiContext(provider=provider, model=s.model, base_url=s.base_url, api_key=key)


def ai_polish(text: str) -> str:
    ctx = load_ai_context()
    if not ctx:
        raise RuntimeError("未配置AI：请先在“API密钥”页保存 key 和模型。")
    prompt = polish_prompt(text)
    return chat(
        ChatRequest(
            provider=ctx.provider,
            api_key=ctx.api_key,
            model=ctx.model,
            base_url=ctx.base_url,
            prompt=prompt,
            max_tokens=2048,
        )
    )


def ai_summarize(text: str) -> str:
    ctx = load_ai_context()
    if not ctx:
        raise RuntimeError("未配置AI：请先在“API密钥”页保存 key 和模型。")
    prompt = summarize_prompt(text)
    return chat(
        ChatRequest(
            provider=ctx.provider,
            api_key=ctx.api_key,
            model=ctx.model,
            base_url=ctx.base_url,
            prompt=prompt,
            max_tokens=1024,
        )
    )


def ai_next_preview(current_chapter_text: str, previous_summaries: str = "") -> str:
    ctx = load_ai_context()
    if not ctx:
        raise RuntimeError("未配置AI：请先在“API密钥”页保存 key 和模型。")
    prompt = next_preview_prompt(current_chapter_text, previous_summaries=previous_summaries)
    return chat(
        ChatRequest(
            provider=ctx.provider,
            api_key=ctx.api_key,
            model=ctx.model,
            base_url=ctx.base_url,
            prompt=prompt,
            max_tokens=1024,
        )
    )


def ai_agent_change_list(book_text: str) -> list[dict]:
    ctx = load_ai_context()
    if not ctx:
        raise RuntimeError("未配置AI：请先在“API密钥”页保存 key 和模型。")
    prompt = agent_change_list_prompt(book_text)
    raw = chat(
        ChatRequest(
            provider=ctx.provider,
            api_key=ctx.api_key,
            model=ctx.model,
            base_url=ctx.base_url,
            prompt=prompt,
            max_tokens=4096,
        )
    )
    # try strict JSON parse; if model wraps with text, extract outermost braces
    s = raw.strip()
    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start >= 0 and end > start:
            s = s[start : end + 1]
    data = json.loads(s)
    change_list = data.get("changeList") or []
    if not isinstance(change_list, list):
        raise ValueError("changeList 不是数组")
    return change_list

