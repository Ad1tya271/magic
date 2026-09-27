"""Resolve context into a conservative, human-readable evidence sheet."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from vera.language import resolve_customer_language, resolve_merchant_language
from vera.planner import suppression_key_for, trigger_customer_id, trigger_merchant_id
from vera.validate import normalize_number
from vera.retrieval import retrieve


def _human(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float) and abs(value) < 1:
        return f"{value * 100:+.1f}%".replace(".0%", "%")
    if isinstance(value, (int, float)):
        return f"{value:,}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_human(x) for x in value)
    return str(value).replace("_", " ").strip()


def resolve_digest_item(category: dict, trigger: dict) -> dict | None:
    digest = category.get("digest") or []
    if not isinstance(digest, list):
        return None
    payload = trigger.get("payload") or {}
    for key in ("top_item_id", "digest_item_id", "alert_id", "item_id"):
        wanted = payload.get(key)
        if wanted:
            for item in digest:
                if isinstance(item, dict) and item.get("id") == wanted:
                    return item
    if isinstance(payload.get("top_item"), dict):
        return payload["top_item"]
    kind = str(trigger.get("kind", ""))
    hints = {"research_digest": ("research",), "regulation_change": ("compliance", "regulation"),
             "cde_opportunity": ("cde", "webinar"), "supply_alert": ("alert", "recall", "compliance"),
             "category_trend_movement": ("trend",)}.get(kind, ())
    return next((x for x in digest if isinstance(x, dict) and any(h in str(x.get("kind", "")).lower() for h in hints)), None)


def derive_facts(bundle: dict) -> dict:
    bundle = bundle or {}
    category = bundle.get("category") or {}
    merchant = bundle.get("merchant") or {}
    trigger = bundle.get("trigger") or {}
    customer = bundle.get("customer")
    identity = merchant.get("identity") or {}
    payload = trigger.get("payload") or {}
    kind = str(trigger.get("kind") or "unknown")
    cid, mid = trigger_customer_id(trigger), trigger_merchant_id(trigger) or merchant.get("merchant_id")
    customer_scope = trigger.get("scope") == "customer" or bool(cid)
    consent = customer.get("consent") or {} if isinstance(customer, dict) else {}
    prefs = customer.get("preferences") or {} if isinstance(customer, dict) else {}
    consent_ok = bool(customer) and prefs.get("reminder_opt_in", True) is not False and bool(consent.get("scope", ["promotional_offers"]))
    route = "merchant_approval" if customer_scope and not consent_ok else ("customer" if customer_scope else "merchant")
    language = resolve_customer_language(customer or {}) if route == "customer" else resolve_merchant_language(merchant)
    owner = identity.get("owner_first_name")
    name = str(identity.get("name") or merchant.get("business_name") or "your business")
    category_name = str(category.get("display_name") or category.get("slug") or "").lower()
    salutation = f"Dr. {owner}" if owner and "dent" in category_name else (owner or name)
    cname = (customer or {}).get("identity", {}).get("name") if isinstance(customer, dict) else None
    if cname and "parent:" in str(cname).lower():
        cname = str(cname).split("parent:", 1)[1].strip(" )")
    facts: dict[str, str] = {}
    values: dict[str, Any] = {}

    def add(key: str, label: str, value: Any, *, pct: bool = False) -> None:
        if value is None or value == "":
            return
        rendered = _human(value)
        if pct and isinstance(value, (int, float)) and abs(value) < 1:
            rendered = f"{value * 100:+.1f}%".replace(".0%", "%")
        facts[key] = f"{label}: {rendered}"
        values[key] = value

    for key, label in (("festival", "Festival"), ("match", "Match"), ("venue", "Venue"),
                       ("service_due", "Service due"), ("metric", "Metric"), ("theme", "Review theme"),
                       ("ask_template", "Open question"), ("product", "Product"), ("medicine", "Medicine")):
        if key in payload:
            add("trigger_" + key, label, payload[key])
    for key in ("intent_topic", "merchant_last_message", "competitor_name", "competitor", "locality",
                "patient_segment", "recipient_name", "service", "service_name", "topic",
                "their_offer", "opened_date", "category_relevance", "season", "likely_driver",
                "window", "previous_focus"):
        if payload.get(key):
            add("trigger_" + key, key.replace("_", " ").capitalize(), payload[key])
    if payload.get("fee"):
        fee_str = str(payload["fee"]).replace("_", " ").capitalize()
        add("trigger_fee", "Fee", fee_str)
    if isinstance(payload.get("trends"), list):
        clean_trends = [str(t).replace("_demand_", " demand ").replace("_", " ") for t in payload["trends"]]
        add("trigger_trends", "Seasonal trends", ", ".join(clean_trends[:3]))
    if isinstance(payload.get("molecule_list"), list):
        clean_mols = [str(m).capitalize() for m in payload["molecule_list"]]
        add("trigger_molecule_list", "Prescriptions", ", ".join(clean_mols))
    for key in ("days_until", "days_to_wedding", "days_remaining", "days_since_expiry",
                "days_since_last_visit", "previous_membership_months", "vs_baseline",
                "occurrences_30d", "trial_n", "credits", "milestone_value", "value_now",
                "delta_pct", "perf_dip_pct", "distance_km", "estimated_uplift_pct",
                "lapsed_customers_added_since_expiry"):
        if key in payload:
            add("trigger_" + key, key.replace("_", " ").capitalize(), payload[key], pct="pct" in key)
    for key in ("due_date", "deadline", "deadline_iso", "match_time_iso", "date", "last_refill", "stock_runs_out_iso"):
        if payload.get(key):
            raw_val = str(payload[key])
            clean_date = raw_val.split("T")[0] if "T" in raw_val else raw_val
            add("trigger_" + key, key.replace("_iso", "").replace("_", " ").capitalize(), clean_date)
            if "T" in raw_val:
                time_part = raw_val.split("T")[1].split("+")[0][:5]
                add("trigger_" + key + "_time", "Time", time_part)
    for key in ("summary", "actionable", "common_quote", "next_step_window_open"):
        if payload.get(key): add("trigger_" + key, key.replace("_", " ").capitalize(), payload[key])

    retrieved = retrieve(bundle, k=6)
    item = resolve_digest_item(category, trigger)
    if item is None and retrieved:
        match = next((d for d in retrieved if d["type"] == "digest"), None)
        if match:
            item = next((x for x in category.get("digest", []) if isinstance(x, dict) and x.get("id") == match["id"]), None)
    if item:
        for key in ("title", "source", "summary", "actionable", "trial_n", "patient_segment", "date", "credits"):
            if item.get(key) is not None: add("digest_" + key, "Research" if key in ("title", "summary") else key.replace("_", " ").capitalize(), item[key])
    perf = merchant.get("performance") or {}
    for key in ("views", "calls", "directions", "leads", "ctr"):
        if key in perf: add("performance_" + key, key.upper() if key == "ctr" else key.capitalize(), perf[key], pct=key == "ctr")
    for key, value in (perf.get("delta_7d") or {}).items(): add("delta_" + key, "7 day " + key.replace("_pct", "").replace("_", " ") + " change", value, pct=True)
    previous_perf = ((bundle.get("previous_merchant") or {}).get("performance") or {})
    for key in ("views", "calls", "directions", "leads"):
        old, new = previous_perf.get(key), perf.get(key)
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and old != new:
            add("performance_change_" + key, key.capitalize() + " since last snapshot", f"{_human(old)} to {_human(new)}")
    sub = merchant.get("subscription") or {}
    for key in ("status", "plan", "days_remaining"):
        if key in sub: add("subscription_" + key, "Subscription " + key.replace("_", " "), sub[key])
    agg = merchant.get("customer_aggregate") or {}
    for key, value in agg.items(): add("aggregate_" + key, key.replace("_", " ").capitalize(), value, pct="pct" in key)
    offers = [str(o.get("title")) for o in merchant.get("offers") or [] if isinstance(o, dict) and o.get("status", "active") == "active" and o.get("title")]
    catalog = [str(o.get("title")) for o in category.get("offer_catalog") or [] if isinstance(o, dict) and o.get("title")]
    history = merchant.get("conversation_history") or []
    if history:
        last = history[-1]
        if isinstance(last, dict): add("last_conversation", "Recent conversation", f"{last.get('from','')} said {last.get('body','')}")
    reviews = merchant.get("review_themes") or []
    for i, rt in enumerate(reviews[:3]):
        if isinstance(rt, dict):
            theme = rt.get("theme", "")
            add(f"review_theme_{i}", "Review theme", theme.replace("_", " "))
            if rt.get("common_quote"): add(f"review_quote_{i}", "Customer quote", rt["common_quote"])
            if rt.get("occurrences_30d"): add(f"review_count_{i}", "Mentions (30d)", rt["occurrences_30d"])
    signals = [str(s).replace("_", " ") for s in merchant.get("signals") or []]
    if kind == "perf_dip" and not any(k.startswith("delta_") for k in facts):
        # Trigger-specific evidence remains the fallback when no performance snapshot exists.
        add("why_now", "Current signal", payload.get("metric") or (signals[0] if signals else None))
    customer_facts = customer or {}
    rel = customer_facts.get("relationship") or {}
    for key, label in (("last_visit", "Last visit"), ("last_visit_date", "Last visit"), ("visits_total", "Visits"), ("visit_count", "Visits"), ("services_received", "Services"), ("services", "Services"), ("state", "Relationship"), ("preferred_slots", "Preferred times")):
        if rel.get(key) is not None: add("customer_" + key, label, rel[key])
    for key, value in payload.items():
        if key.endswith("slots") and isinstance(value, list): add("available_slots", "Available times", ", ".join(str(x.get("label") or x.get("iso")) for x in value if isinstance(x, dict)))

    placeholder = payload.get("placeholder") is True
    suppression = suppression_key_for(trigger, mid, cid)
    allowed = sorted({normalize_number(n) for n in facts.values() if normalize_number(n)} | {normalize_number(v) for v in values.values() if normalize_number(v)})
    template = "vera_" + kind + "_v1" if route != "customer" else "merchant_" + kind + "_v1"
    return {"kind":kind,"scope":"customer" if customer_scope else "merchant","route":route,
        "route_reason":"Customer context missing or messaging consent absent" if route == "merchant_approval" else None,
        "send_as":"merchant_on_behalf" if route == "customer" else "vera","merchant_id":mid,
        "customer_id":cid,"business_name":name,"owner_first_name":owner,"salutation":salutation,
        "customer_name":cname,"customer_salutation":cname,"locality":identity.get("locality"),"city":identity.get("city"),
        "language":language,"digest_item":item,"active_offers":offers,"catalog_offers":catalog,
        "facts":facts,"values":values,"allowed_numbers":allowed,"placeholder_trigger":placeholder,
        "blocked":None if not merchant.get("messaging_opt_out") else "merchant opted out",
        "suppression_key":suppression,"template_name":template,"signals":signals,
        "retrieved":retrieved}
