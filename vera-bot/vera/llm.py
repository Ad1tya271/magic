"""Thin async wrapper around the Anthropic Messages API that returns parsed JSON or None.

Design constraints (see SPEC.md):
- claude-opus-4-7 rejects temperature/top_p/top_k and assistant prefill, and runs without
  thinking when ``thinking`` is omitted, so none of those are sent.
- Determinism comes from memoising successful results by a hash of the exact request.
- Every call is bounded by a hard ``asyncio.wait_for`` deadline and never raises.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
from typing import Any

import anthropic

from vera.config import settings

log = logging.getLogger("vera.llm")

_MEMO_LIMIT = 4096
_FAILED_STOP_REASONS = {"refusal", "max_tokens", "model_context_window_exceeded"}
_FORMAT_ERROR_HINTS = ("output_config", "format", "json_schema", "schema")


def request_hash(*, model: str, effort: str, system: Any, messages: Any, schema: Any,
                 max_tokens: int) -> str:
    canonical = json.dumps(
        {"model": model, "effort": effort, "system": system, "messages": messages,
         "schema": schema, "max_tokens": max_tokens},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_json_object(text: str) -> dict | None:
    """Parse ``text`` as a JSON object, else return the first JSON object embedded in it."""
    if not text:
        return None
    stripped = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1)
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", stripped):
        try:
            parsed, _ = decoder.raw_decode(stripped, match.start())
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _system_blocks(system: Any) -> list[dict]:
    """Normalise ``system`` to text blocks with an ephemeral cache breakpoint on the last one."""
    if system is None or system == "" or system == []:
        return []
    if isinstance(system, str):
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    blocks = [dict(block) for block in system]
    if blocks and not any("cache_control" in block for block in blocks):
        blocks[-1]["cache_control"] = {"type": "ephemeral"}
    return blocks


def _with_json_instruction(messages: list, schema: dict) -> list:
    """Copy of ``messages`` whose final user turn also asks for bare JSON matching ``schema``.

    Only used when structured output was rejected; without it nothing forces the JSON shape.
    """
    instruction = ("Respond with only one JSON object (no prose, no code fences) that matches "
                   "this JSON schema:\n" + json.dumps(schema, ensure_ascii=False, sort_keys=True))
    copied = [dict(message) for message in messages]
    if not copied or copied[-1].get("role") != "user":
        return copied + [{"role": "user", "content": instruction}]
    last = copied[-1]
    content = last.get("content")
    if isinstance(content, str):
        last["content"] = [{"type": "text", "text": content}, {"type": "text", "text": instruction}]
    else:
        last["content"] = list(content or []) + [{"type": "text", "text": instruction}]
    return copied


def _response_text(response: Any) -> str:
    parts = []
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "".join(parts)


def _is_format_error(error: anthropic.BadRequestError) -> bool:
    message = f"{getattr(error, 'message', '')} {getattr(error, 'body', '')}".lower()
    return any(hint in message for hint in _FORMAT_ERROR_HINTS)


class LLMClient:
    """``complete_json`` returns a dict or None (disabled/timeout/refusal/parse or API error)."""

    def __init__(self, *, model: str | None = None, effort: str | None = None,
                 enabled: bool | None = None, client: Any | None = None) -> None:
        self.model = model or settings.model
        self.effort = effort or settings.effort
        self.enabled = settings.llm_enabled if enabled is None else enabled
        self._injected_client = client
        self._client: Any | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._memo: dict[str, dict] = {}
        self._inflight: dict[str, asyncio.Task] = {}
        self._schemas_without_format: set[str] = set()

    # -- client lifecycle --
    def _get_client(self) -> Any:
        if self._injected_client is not None:
            return self._injected_client
        # httpx connection pools are bound to the loop that created them; bot.compose() runs
        # each call in a fresh loop, so a client is only reused on the loop it was made on.
        loop = asyncio.get_running_loop()
        if self._client is None or self._client_loop is not loop:
            self._client = anthropic.AsyncAnthropic(max_retries=0)
            self._client_loop = loop
        return self._client

    async def aclose_loop_client(self) -> None:
        """Close the SDK client if it belongs to the running loop (used by one-shot runs)."""
        client, self._client, self._client_loop = self._client, None, None
        if client is not None:
            try:
                await client.close()
            except Exception:  # noqa: BLE001 - closing is best-effort
                log.debug("closing Anthropic client failed", exc_info=True)

    def clear_memo(self) -> None:
        self._memo.clear()

    def memo_size(self) -> int:
        return len(self._memo)

    # -- public API --
    async def complete_json(self, *, system: Any, messages: list, schema: dict, max_tokens: int,
                            timeout_s: float, cache_key: str | None = None) -> dict | None:
        if not self.enabled or timeout_s <= 0:
            return None
        try:
            key = cache_key or request_hash(
                model=self.model, effort=self.effort, system=system, messages=messages,
                schema=schema, max_tokens=max_tokens,
            )
            cached = self._memo.get(key)
            if cached is not None:
                return copy.deepcopy(cached)

            loop = asyncio.get_running_loop()
            task = self._inflight.get(key)
            if task is None or task.done() or task.get_loop() is not loop:
                task = loop.create_task(self._request(system, messages, schema, max_tokens,
                                                      timeout_s))
                self._inflight[key] = task
                task.add_done_callback(lambda t, k=key: self._finish(k, t))
            # shield: a caller with a shorter deadline must not cancel a request another
            # caller (e.g. a background precompute) is still waiting on.
            result = await asyncio.wait_for(asyncio.shield(task), timeout=timeout_s)
            return copy.deepcopy(result) if result is not None else None
        except TimeoutError:
            log.warning("LLM call exceeded %.1fs deadline", timeout_s)
            return None
        except Exception:  # noqa: BLE001 - contract: never raise
            log.exception("LLM call failed")
            return None

    # -- internals --
    def _finish(self, key: str, task: asyncio.Task) -> None:
        if self._inflight.get(key) is task:
            del self._inflight[key]
        if task.cancelled() or task.exception() is not None:
            return
        result = task.result()
        if result is not None:
            if len(self._memo) >= _MEMO_LIMIT:
                self._memo.pop(next(iter(self._memo)))
            self._memo[key] = result

    async def _request(self, system: Any, messages: list, schema: dict, max_tokens: int,
                       timeout_s: float) -> dict | None:
        try:
            return await self._request_with_format_retry(system, messages, schema, max_tokens,
                                                         timeout_s)
        except anthropic.APIStatusError as error:
            log.warning("LLM API error %s: %s", error.status_code, getattr(error, "message", error))
        except anthropic.APIConnectionError as error:
            log.warning("LLM connection error: %s", error)
        return None

    async def _request_with_format_retry(self, system: Any, messages: list, schema: dict,
                                         max_tokens: int, timeout_s: float) -> dict | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        client = self._get_client()
        schema_key = hashlib.sha256(
            json.dumps(schema, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        params: dict[str, Any] = {"model": self.model, "max_tokens": max_tokens, "messages": messages}
        blocks = _system_blocks(system)
        if blocks:
            params["system"] = blocks

        fallback_output_config: dict | None = {"effort": self.effort}
        if schema_key not in self._schemas_without_format:
            params["output_config"] = {
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": schema},
            }
            try:
                response = await client.messages.create(
                    **params, timeout=max(0.1, deadline - loop.time()))
                return self._parse(response)
            except anthropic.BadRequestError as error:
                if not _is_format_error(error):
                    raise
                log.warning("structured output rejected, retrying without format: %s",
                            getattr(error, "message", error))
                # Remembered per schema so later calls skip the doomed first attempt.
                self._schemas_without_format.add(schema_key)
                if "effort" in str(getattr(error, "message", "")).lower():
                    fallback_output_config = None

        params.pop("output_config", None)
        if fallback_output_config:
            params["output_config"] = fallback_output_config
        params["messages"] = _with_json_instruction(messages, schema)
        remaining = deadline - loop.time()
        if remaining <= 0:
            return None
        response = await client.messages.create(**params, timeout=max(0.1, remaining))
        return self._parse(response)

    @staticmethod
    def _parse(response: Any) -> dict | None:
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason in _FAILED_STOP_REASONS:
            log.warning("LLM stopped with %s", stop_reason)
            return None
        return extract_json_object(_response_text(response))


_llm: Any | None = None


def get_llm() -> Any:
    """Process-wide LLM client (anything with an async ``complete_json`` and ``enabled``)."""
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def set_llm(llm: Any | None) -> None:
    """Replace the process-wide client (tests inject fakes); ``None`` rebuilds lazily."""
    global _llm
    _llm = llm
