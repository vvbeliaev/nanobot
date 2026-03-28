"""Anthropic OAuth Provider — Bearer token (sk-ant-oat01-) auth.

OAuth flow (discovered from OpenClaw source):
  Send sk-ant-oat01-* token directly to /v1/messages with:
    Authorization: Bearer <token>
    anthropic-beta: oauth-2025-04-20
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, AsyncGenerator

import httpx
from loguru import logger

from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# Beta headers required for OAuth sk-ant-oat01- tokens (discovered from OpenClaw source)
ANTHROPIC_OAUTH_BETAS = "claude-code-20250219,oauth-2025-04-20,fine-grained-tool-streaming-2025-05-14,interleaved-thinking-2025-05-14"

# OAuth requires the system prompt to begin with one of these prefixes (Anthropic server-side check)
OAUTH_SYSTEM_PREFIX = "You are Claude Code, Anthropic's official CLI for Claude.\n\n"


class AnthropicOAuthProvider(LLMProvider):
    """Anthropic provider using OAuth Bearer token (sk-ant-oat01-).

    Sends the token directly via Authorization: Bearer + anthropic-beta: oauth-2025-04-20.
    No token exchange needed.
    """

    def __init__(self, token: str, default_model: str = "claude-opus-4-6"):
        super().__init__(api_key=None, api_base=None)
        self.token = token
        self.default_model = default_model

    async def _call_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str | None,
        max_tokens: int,
        temperature: float,
        reasoning_effort: str | None,
        tool_choice: str | dict[str, Any] | None,
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        model = _strip_model_prefix(model or self.default_model)
        system_prompt, converted_messages = _convert_messages(messages)
        headers = _build_headers(self.token)

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "stream": True,
            "messages": converted_messages,
        }
        # OAuth validates the system prompt server-side — exact string required for the prefix.
        # Try passing system as an array of blocks: validation may only check the first block.
        if system_prompt:
            body["system"] = [
                {"type": "text", "text": OAUTH_SYSTEM_PREFIX.rstrip()},
                {"type": "text", "text": system_prompt},
            ]
        else:
            body["system"] = OAUTH_SYSTEM_PREFIX.rstrip()
        if tools:
            body["tools"] = _convert_tools(tools)
            body["tool_choice"] = _convert_tool_choice(tool_choice)
        if temperature != 1.0:
            body["temperature"] = temperature

        logger.debug("Anthropic OAuth model: {}, max_tokens: {}, msg_count: {}, tool_count: {}", body["model"], body["max_tokens"], len(body["messages"]), len(body.get("tools") or []))

        try:
            try:
                content, tool_calls, finish_reason, usage = await _request_anthropic(
                    MESSAGES_URL, headers, body, verify=True,
                    on_content_delta=on_content_delta,
                )
            except Exception as e:
                if "CERTIFICATE_VERIFY_FAILED" not in str(e):
                    raise
                logger.warning("SSL verification failed; retrying with verify=False")
                content, tool_calls, finish_reason, usage = await _request_anthropic(
                    MESSAGES_URL, headers, body, verify=False,
                    on_content_delta=on_content_delta,
                )
            return LLMResponse(content=content, tool_calls=tool_calls, finish_reason=finish_reason, usage=usage)
        except Exception as e:
            return LLMResponse(content=f"Error calling Anthropic OAuth: {e}", finish_reason="error")

    async def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
        model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        return await self._call_anthropic(
            messages, tools, model, max_tokens, temperature, reasoning_effort, tool_choice,
        )

    async def chat_stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
        model: str | None = None, max_tokens: int = 4096, temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        on_content_delta: Callable[[str], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        return await self._call_anthropic(
            messages, tools, model, max_tokens, temperature, reasoning_effort, tool_choice,
            on_content_delta,
        )

    def get_default_model(self) -> str:
        return self.default_model


def _strip_model_prefix(model: str) -> str:
    if model.startswith("anthropic-oauth/") or model.startswith("anthropic_oauth/"):
        return model.split("/", 1)[1]
    return model


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "anthropic-version": ANTHROPIC_VERSION,
        "anthropic-beta": ANTHROPIC_OAUTH_BETAS,
        "accept": "text/event-stream",
        "content-type": "application/json",
    }


async def _request_anthropic(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    verify: bool,
    on_content_delta: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[str, list[ToolCallRequest], str, dict[str, int]]:
    async with httpx.AsyncClient(timeout=60.0, verify=verify) as client:
        async with client.stream("POST", url, headers=headers, json=body) as response:
            if response.status_code != 200:
                text = await response.aread()
                raise RuntimeError(_friendly_error(response.status_code, text.decode("utf-8", "ignore")))
            return await _consume_sse(response, on_content_delta)


def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function schema to Anthropic tool format (input_schema)."""
    converted: list[dict[str, Any]] = []
    for tool in tools:
        fn = (tool.get("function") or {}) if tool.get("type") == "function" else tool
        name = fn.get("name")
        if not name:
            continue
        params = fn.get("parameters") or {}
        converted.append({
            "name": name,
            "description": fn.get("description") or "",
            "input_schema": params if isinstance(params, dict) else {"type": "object", "properties": {}},
        })
    return converted


def _convert_tool_choice(tc: str | dict[str, Any] | None) -> dict[str, Any]:
    if tc is None or tc == "auto":
        return {"type": "auto"}
    if isinstance(tc, str):
        if tc == "required":
            return {"type": "any"}
        if tc == "none":
            return {"type": "auto"}
        return {"type": "auto"}
    if isinstance(tc, dict) and tc.get("type") == "function":
        fn = tc.get("function") or {}
        return {"type": "tool", "name": fn.get("name", "")}
    return {"type": "auto"}


def _convert_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Convert OpenAI-format messages to Anthropic format.
    System messages are extracted; tool results are grouped into user messages.
    """
    system_prompt = ""
    result: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            system_prompt = content if isinstance(content, str) else ""
            continue

        if role == "user":
            user_msg = _make_user_message(content)
            # Anthropic requires alternating roles — merge consecutive user messages
            if result and result[-1]["role"] == "user":
                prev = result[-1]
                prev_content = prev["content"]
                new_content = user_msg["content"]
                # Normalize both to lists of blocks
                if isinstance(prev_content, str):
                    prev_content = [{"type": "text", "text": prev_content}]
                if isinstance(new_content, str):
                    new_content = [{"type": "text", "text": new_content}]
                result[-1] = {"role": "user", "content": prev_content + new_content}
            else:
                result.append(user_msg)
            continue

        if role == "assistant":
            blocks: list[dict[str, Any]] = []
            if isinstance(content, str) and content:
                blocks.append({"type": "text", "text": content})
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function") or {}
                raw_args = fn.get("arguments") or "{}"
                try:
                    input_data = json.loads(raw_args)
                except Exception:
                    input_data = {}
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or "toolu_0",
                    "name": fn.get("name") or "",
                    "input": input_data,
                })
            if blocks:
                result.append({"role": "assistant", "content": blocks})
            continue

        if role == "tool":
            tool_result = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id") or "toolu_0",
                "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
            }
            # Merge consecutive tool results into one user message
            if (
                result
                and result[-1]["role"] == "user"
                and isinstance(result[-1]["content"], list)
                and result[-1]["content"]
                and all(b.get("type") == "tool_result" for b in result[-1]["content"])
            ):
                result[-1]["content"].append(tool_result)
            else:
                result.append({"role": "user", "content": [tool_result]})

    return system_prompt, result


def _make_user_message(content: Any) -> dict[str, Any]:
    if isinstance(content, str):
        return {"role": "user", "content": content}
    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                blocks.append({"type": "text", "text": item.get("text", "")})
            elif item.get("type") == "image_url":
                url = (item.get("image_url") or {}).get("url", "")
                if url.startswith("data:"):
                    media_type = url.split(";")[0].split(":")[1]
                    b64 = url.split(",", 1)[1]
                    blocks.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    })
                elif url:
                    blocks.append({"type": "image", "source": {"type": "url", "url": url}})
        if blocks:
            return {"role": "user", "content": blocks}
    return {"role": "user", "content": content or ""}


async def _iter_sse(response: httpx.Response) -> AsyncGenerator[dict[str, Any], None]:
    buffer: list[str] = []
    async for line in response.aiter_lines():
        if line == "":
            if buffer:
                data_lines = [ln[5:].strip() for ln in buffer if ln.startswith("data:")]
                buffer = []
                if not data_lines:
                    continue
                data = "\n".join(data_lines).strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    yield json.loads(data)
                except Exception:
                    continue
            continue
        buffer.append(line)


async def _consume_sse(
    response: httpx.Response,
    on_content_delta: Callable[[str], Awaitable[None]] | None = None,
) -> tuple[str, list[ToolCallRequest], str, dict[str, int]]:
    content = ""
    tool_calls: list[ToolCallRequest] = []
    tool_buffers: dict[int, dict[str, Any]] = {}
    finish_reason = "stop"
    input_tokens = 0
    output_tokens = 0

    async for event in _iter_sse(response):
        event_type = event.get("type")

        if event_type == "message_start":
            msg_usage = (event.get("message") or {}).get("usage") or {}
            input_tokens = int(msg_usage.get("input_tokens") or 0)

        elif event_type == "content_block_start":
            block = event.get("content_block") or {}
            idx = event.get("index", 0)
            if block.get("type") == "tool_use":
                tool_buffers[idx] = {
                    "id": block.get("id") or f"toolu_{idx}",
                    "name": block.get("name") or "",
                    "input_json": "",
                }

        elif event_type == "content_block_delta":
            idx = event.get("index", 0)
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta":
                text = delta.get("text") or ""
                content += text
                if on_content_delta and text:
                    await on_content_delta(text)
            elif delta.get("type") == "input_json_delta":
                if idx in tool_buffers:
                    tool_buffers[idx]["input_json"] += delta.get("partial_json") or ""

        elif event_type == "content_block_stop":
            idx = event.get("index", 0)
            if idx in tool_buffers:
                buf = tool_buffers.pop(idx)
                try:
                    input_data = json.loads(buf["input_json"]) if buf["input_json"] else {}
                except Exception:
                    input_data = {"raw": buf["input_json"]}
                tool_calls.append(ToolCallRequest(
                    id=buf["id"],
                    name=buf["name"],
                    arguments=input_data,
                ))

        elif event_type == "message_delta":
            delta = event.get("delta") or {}
            stop_reason = delta.get("stop_reason")
            if stop_reason:
                finish_reason = _map_finish_reason(stop_reason)
            delta_usage = event.get("usage") or {}
            if delta_usage.get("output_tokens"):
                output_tokens = int(delta_usage["output_tokens"])

        elif event_type == "error":
            raise RuntimeError(f"Anthropic stream error: {event.get('error')}")

    return content, tool_calls, finish_reason, {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}


_FINISH_REASON_MAP = {
    "end_turn": "stop",
    "max_tokens": "length",
    "tool_use": "tool_calls",
    "stop_sequence": "stop",
}


def _map_finish_reason(reason: str | None) -> str:
    return _FINISH_REASON_MAP.get(reason or "end_turn", "stop")


def _friendly_error(status_code: int, raw: str) -> str:
    return f"HTTP {status_code}: {raw}"
