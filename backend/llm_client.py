"""LLM 调用封装：所有 Agent 共享同一个客户端实例。"""
from __future__ import annotations

import json
import logging

from openai import OpenAI

from backend.config import get_settings

logger = logging.getLogger("weekend-agent.llm")

_client: OpenAI | None = None
_client_built: bool = False


def get_llm_client() -> OpenAI | None:
    global _client, _client_built
    settings = get_settings()
    if not settings.use_llm:
        return None
    if not _client_built:
        _client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        _client_built = True
    return _client


def get_model_name() -> str:
    return get_settings().openai_model


def chat(
    system: str,
    user: str,
    *,
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> str | None:
    """发送一次对话请求，返回 LLM 回复文本。失败返回 None。"""
    client = get_llm_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=get_model_name(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:
        logger.warning(f"LLM call failed: {exc}")
        return None


def chat_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> dict | list | None:
    """发送对话请求并解析 JSON 回复。失败返回 None。"""
    text = chat(system, user, temperature=temperature, max_tokens=max_tokens)
    if text is None:
        return None
    text = text.strip()
    # 去掉可能的 markdown 代码块包裹
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取第一个 JSON 对象/数组
        for brace in ("[{", "[{", "{", "["):
            if brace in text:
                start = text.index(brace)
                break
        else:
            logger.warning(f"LLM returned non-JSON: {text[:200]}")
            return None
        try:
            return json.loads(text[start:])
        except json.JSONDecodeError:
            logger.warning(f"LLM JSON parse failed: {text[:200]}")
            return None
