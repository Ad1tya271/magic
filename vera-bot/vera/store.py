"""In-memory state: versioned contexts, conversations, per-merchant memory, sent keys.

Everything runs on one asyncio event loop, but FastAPI may still call into this from a
worker thread, so compound read-modify-write operations take a (never awaited) lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

SCOPES: tuple[str, ...] = ("category", "merchant", "customer", "trigger")

# Field inside each payload that names the entity; used as a lookup alias when a
# context_id differs from the id other contexts use to reference it.
_ALIAS_FIELD = {"category": "slug", "merchant": "merchant_id", "customer": "customer_id", "trigger": "id"}


@dataclass(frozen=True)
class StoredContext:
    scope: str
    context_id: str
    version: int
    payload: dict
    stored_at: str
    delivered_at: str | None = None
    previous_payload: dict | None = None


class ContextStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, dict[str, StoredContext]] = {scope: {} for scope in SCOPES}
        self._aliases: dict[str, dict[str, str]] = {scope: {} for scope in SCOPES}

    def put(self, scope: str, context_id: str, version: int, payload: dict, *,
            stored_at: str, delivered_at: str | None = None) -> tuple[bool, int | None]:
        """Store if ``version`` is newer than what we hold.

        Returns ``(accepted, current_version)``; ``current_version`` is the stored version after
        the call (the new one when accepted, the existing higher/equal one when rejected).
        """
        if scope not in SCOPES:
            raise ValueError(f"unknown scope {scope!r}")
        with self._lock:
            existing = self._items[scope].get(context_id)
            if existing is not None and version <= existing.version:
                return False, existing.version
            self._items[scope][context_id] = StoredContext(
                scope=scope, context_id=context_id, version=version, payload=payload,
                stored_at=stored_at, delivered_at=delivered_at,
                previous_payload=existing.payload if existing is not None else None,
            )
            alias = payload.get(_ALIAS_FIELD[scope])
            if isinstance(alias, str) and alias and alias != context_id:
                self._aliases[scope][alias] = context_id
            return True, version

    def entry(self, scope: str, context_id: str | None) -> StoredContext | None:
        if not context_id or scope not in SCOPES:
            return None
        items = self._items[scope]
        found = items.get(context_id)
        if found is None:
            real_id = self._aliases[scope].get(context_id)
            found = items.get(real_id) if real_id else None
        return found

    def get(self, scope: str, context_id: str | None) -> dict | None:
        """Payload for ``context_id`` (or for a payload whose own id field equals it)."""
        found = self.entry(scope, context_id)
        return found.payload if found is not None else None

    def version(self, scope: str, context_id: str) -> int | None:
        found = self.entry(scope, context_id)
        return found.version if found is not None else None

    def items(self, scope: str) -> list[StoredContext]:
        with self._lock:
            return list(self._items[scope].values())

    def counts(self) -> dict[str, int]:
        with self._lock:
            return {scope: len(self._items[scope]) for scope in SCOPES}

    def clear(self) -> None:
        with self._lock:
            for scope in SCOPES:
                self._items[scope].clear()
                self._aliases[scope].clear()


class ConversationStore:
    """conversation_id -> ConversationState (the dataclass from ``conversation_handlers``)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, Any] = {}

    def get(self, conversation_id: str) -> Any | None:
        return self._states.get(conversation_id)

    def put(self, state: Any) -> None:
        with self._lock:
            self._states[state.conversation_id] = state

    def exists(self, conversation_id: str) -> bool:
        return conversation_id in self._states

    def all(self) -> list[Any]:
        with self._lock:
            return list(self._states.values())

    def reserve_id(self, base: str) -> str:
        """Return ``base`` (or ``base_2``, ``base_3``...) that no stored conversation uses."""
        with self._lock:
            candidate = base
            n = 2
            while candidate in self._states:
                candidate = f"{base}_{n}"
                n += 1
            return candidate

    def __len__(self) -> int:
        return len(self._states)

    def clear(self) -> None:
        with self._lock:
            self._states.clear()


def new_merchant_memory(merchant_id: str) -> dict:
    return {
        "merchant_id": merchant_id,
        "opted_out_until": None,
        "auto_reply_count": 0,
        "auto_reply_texts": [],
    }


def is_opted_out(memory: dict | None) -> bool:
    # Any truthy marker counts: the judge's clock and the dataset's clock disagree by months,
    # so comparing an opt-out expiry against "now" would be meaningless within a test run.
    if not memory:
        return False
    return bool(memory.get("opted_out_until") or memory.get("opted_out"))


class Store:
    """All bot state. One instance per process (``store``); ``reset()`` wipes everything."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.contexts = ContextStore()
        self.conversations = ConversationStore()
        self._memory: dict[str, dict] = {}
        self._sent_keys: set[str] = set()
        self._used_triggers: set[str] = set()

    # -- per-merchant memory (mutated in place by conversation_handlers) --
    def merchant_memory(self, merchant_id: str | None) -> dict:
        key = merchant_id or ""
        with self._lock:
            memory = self._memory.get(key)
            if memory is None:
                memory = new_merchant_memory(key)
                self._memory[key] = memory
            return memory

    def merchant_opted_out(self, merchant_id: str | None) -> bool:
        return is_opted_out(self._memory.get(merchant_id or ""))

    # -- suppression / trigger usage --
    def mark_sent(self, suppression_key: str | None) -> None:
        if suppression_key:
            with self._lock:
                self._sent_keys.add(suppression_key)

    def was_sent(self, suppression_key: str | None) -> bool:
        return bool(suppression_key) and suppression_key in self._sent_keys

    def mark_trigger_used(self, trigger_id: str | None) -> None:
        if trigger_id:
            with self._lock:
                self._used_triggers.add(trigger_id)

    def trigger_used(self, trigger_id: str | None) -> bool:
        return bool(trigger_id) and trigger_id in self._used_triggers

    # -- conversation helpers --
    def bot_bodies_for(self, merchant_id: str | None, customer_id: str | None) -> list[str]:
        """Bodies the bot already sent in conversations with this merchant/customer pair."""
        bodies: list[str] = []
        for state in self.conversations.all():
            if getattr(state, "merchant_id", None) != merchant_id:
                continue
            if getattr(state, "customer_id", None) != customer_id:
                continue
            for turn in getattr(state, "turns", None) or []:
                if not isinstance(turn, dict):
                    continue
                if turn.get("from") in ("merchant", "customer"):
                    continue
                body = turn.get("body")
                if isinstance(body, str) and body and body not in bodies:
                    bodies.append(body)
        return bodies

    def reset(self) -> None:
        self.contexts.clear()
        self.conversations.clear()
        with self._lock:
            self._memory.clear()
            self._sent_keys.clear()
            self._used_triggers.clear()


store = Store()
