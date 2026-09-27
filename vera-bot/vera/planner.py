"""Tick planning: which of the judge's available triggers become messages this tick."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from vera.config import settings
from vera.store import Store

log = logging.getLogger("vera.planner")

_FAR_FUTURE = datetime.max


def parse_iso(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp to a naive UTC datetime; None if absent or unparseable."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    offset = parsed.utcoffset()
    if offset is not None:
        parsed = (parsed - offset).replace(tzinfo=None)
    return parsed


def suppression_key_for(trigger: dict, merchant_id: str | None, customer_id: str | None) -> str:
    key = trigger.get("suppression_key")
    if isinstance(key, str) and key:
        return key
    return f"{trigger.get('kind') or 'unknown'}:{merchant_id or '-'}:{customer_id or '-'}"


def trigger_merchant_id(trigger: dict) -> str | None:
    payload = trigger.get("payload") if isinstance(trigger.get("payload"), dict) else {}
    value = trigger.get("merchant_id") or payload.get("merchant_id")
    return value if isinstance(value, str) and value else None


def trigger_customer_id(trigger: dict) -> str | None:
    payload = trigger.get("payload") if isinstance(trigger.get("payload"), dict) else {}
    value = trigger.get("customer_id") or payload.get("customer_id")
    return value if isinstance(value, str) and value else None


def build_bundle(store: Store, trigger_id: str, now: str | None) -> dict | None:
    """The 4-context bundle for a stored trigger, or None if trigger/merchant/category is missing.

    A customer context that belongs to a different merchant is treated as missing.
    """
    trigger_entry = store.contexts.entry("trigger", trigger_id)
    trigger = trigger_entry.payload if trigger_entry else None
    if not isinstance(trigger, dict):
        return None
    merchant_id = trigger_merchant_id(trigger)
    merchant_entry = store.contexts.entry("merchant", merchant_id)
    merchant = merchant_entry.payload if merchant_entry else None
    if not isinstance(merchant, dict):
        return None
    category_entry = store.contexts.entry("category", merchant.get("category_slug"))
    category = category_entry.payload if category_entry else None
    if not isinstance(category, dict):
        return None
    customer_id = trigger_customer_id(trigger)
    customer = store.contexts.get("customer", customer_id) if customer_id else None
    if isinstance(customer, dict):
        owner = customer.get("merchant_id")
        if owner and merchant_id and owner != merchant_id:
            customer = None
    else:
        customer = None
    old_items = (category_entry.previous_payload or {}).get("digest", []) if category_entry else []
    old_ids = {x.get("id") for x in old_items if isinstance(x, dict)}
    novel = [x.get("id") for x in category.get("digest", []) if isinstance(x, dict)
             and x.get("id") and x.get("id") not in old_ids]
    return {"category": category, "merchant": merchant, "trigger": trigger,
            "customer": customer, "now": now,
            "previous_merchant": merchant_entry.previous_payload if merchant_entry else None,
            "novel_digest_ids": novel}


def _urgency(trigger: dict) -> int:
    try:
        return int(trigger.get("urgency") or 0)
    except (TypeError, ValueError):
        return 0


def select_candidates(store: Store, available_trigger_ids: list, now: str | None, *,
                      max_actions: int | None = None) -> list[dict]:
    """Candidates for this tick, best first.

    Each candidate: ``{"trigger_id", "merchant_id", "customer_id", "kind", "urgency",
    "expires_at", "suppression_key", "audience", "bundle"}`` where ``audience`` is
    ``"customer"`` when the trigger targets a stored customer, else ``"merchant"``.
    """
    limit = settings.max_actions_per_tick if max_actions is None else max_actions
    now_dt = parse_iso(now)
    seen_ids: set[str] = set()
    pool: list[dict] = []
    for trigger_id in available_trigger_ids or []:
        if not isinstance(trigger_id, str) or not trigger_id or trigger_id in seen_ids:
            continue
        seen_ids.add(trigger_id)
        bundle = build_bundle(store, trigger_id, now)
        if bundle is None:
            log.debug("skip %s: trigger, merchant or category not loaded", trigger_id)
            continue
        trigger = bundle["trigger"]
        merchant_id = bundle["merchant"].get("merchant_id") or trigger_merchant_id(trigger)
        customer_id = trigger_customer_id(trigger)
        key = suppression_key_for(trigger, merchant_id, customer_id)
        if store.was_sent(key) or store.trigger_used(trigger_id):
            continue
        if store.merchant_opted_out(merchant_id):
            continue
        expires_dt = parse_iso(trigger.get("expires_at"))
        if settings.strict_expiry and now_dt and expires_dt and expires_dt < now_dt:
            continue
        pool.append({
            "trigger_id": trigger_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "kind": trigger.get("kind") or "unknown",
            "urgency": _urgency(trigger),
            "expires_at": trigger.get("expires_at"),
            "suppression_key": key,
            "audience": "customer" if bundle["customer"] is not None else "merchant",
            "bundle": bundle,
            "_expires_dt": expires_dt or _FAR_FUTURE,
        })

    pool.sort(key=lambda c: (-c["urgency"], c["_expires_dt"], c["trigger_id"]))
    selected: list[dict] = []
    audiences: set[tuple[str, str | None]] = set()
    keys: set[str] = set()
    for candidate in pool:
        audience = audience_key(candidate["audience"], candidate["merchant_id"],
                                candidate["customer_id"])
        if audience in audiences or candidate["suppression_key"] in keys:
            continue
        audiences.add(audience)
        keys.add(candidate["suppression_key"])
        del candidate["_expires_dt"]
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def audience_key(audience: str, merchant_id: str | None, customer_id: str | None
                 ) -> tuple[str, str | None]:
    """At most one message per key per tick: the merchant, or one specific customer."""
    if audience == "customer" and customer_id:
        return ("customer", customer_id)
    return ("merchant", merchant_id)
