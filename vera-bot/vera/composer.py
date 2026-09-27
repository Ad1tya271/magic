"""LLM composition with a verified deterministic fallback."""
from __future__ import annotations
import asyncio
import time
from typing import Any

from vera.config import settings
from vera.facts import derive_facts
from vera.fallback import compose_fallback
from vera.prompts import COMPOSE_SCHEMA, build_compose_messages
from vera.validate import has_errors, sanitize_body, validate_message

async def compose_message(bundle: dict, *, llm: Any, budget_s: float,
                          prior_bodies: list[str] | None = None) -> dict:
    started = time.monotonic()
    try:
        facts = derive_facts(bundle)
        if facts.get("blocked"):
            return {"skip":True,"reason":facts["blocked"]}
        result = None
        if getattr(llm, "enabled", False) and budget_s > 0.15:
            system, messages = build_compose_messages(bundle, facts, prior_bodies)
            try:
                result = await llm.complete_json(system=system, messages=messages, schema=COMPOSE_SCHEMA,
                    max_tokens=settings.max_tokens, timeout_s=max(0.05, budget_s - (time.monotonic()-started)))
            except Exception:
                result = None
        if isinstance(result, dict) and result.get("body"):
            msg = {"body":sanitize_body(result["body"]), "cta":result.get("cta", "open_ended"),
                "send_as":facts["send_as"],"suppression_key":facts["suppression_key"],
                "rationale":str(result.get("rationale") or "Uses the supplied context to offer a relevant next step."),
                "template_name":facts["template_name"],"template_params":[str(x) for x in (result.get("template_params") or [])[:5]],
                "_meta":{"composer":"llm","route":facts["route"],"issues":[]}}
            issues = validate_message(msg, bundle, facts, prior_bodies=prior_bodies, mode="compose")
            if has_errors(issues) and getattr(llm, "enabled", False) and budget_s-(time.monotonic()-started) > .25:
                system, messages = build_compose_messages(bundle, facts, prior_bodies, repair_notes=issues)
                try:
                    repair = await llm.complete_json(system=system,messages=messages,schema=COMPOSE_SCHEMA,
                        max_tokens=settings.max_tokens,timeout_s=max(.05,budget_s-(time.monotonic()-started)))
                    if isinstance(repair,dict) and repair.get("body"):
                        msg.update(body=sanitize_body(repair["body"]),cta=repair.get("cta",msg["cta"]),
                                   rationale=repair.get("rationale",msg["rationale"]),
                                   template_params=[str(x) for x in (repair.get("template_params") or [])[:5]])
                        issues=validate_message(msg,bundle,facts,prior_bodies=prior_bodies,mode="compose")
                except Exception: pass
            msg["_meta"]["issues"] = issues
            if not has_errors(issues): return msg
        msg = compose_fallback(bundle, facts)
        msg["body"] = sanitize_body(msg.get("body", ""))
        msg["_meta"]["issues"] = validate_message(msg,bundle,facts,prior_bodies=prior_bodies,mode="compose")
        return msg
    except Exception:
        # Contract: context edge cases must never take down a tick.
        return {"skip":True,"reason":"composition unavailable"}

async def precompute(bundle: dict, *, llm=None, budget_s: float | None = None) -> dict:
    if llm is None:
        from vera.llm import get_llm
        llm = get_llm()
    return await compose_message(bundle,llm=llm,budget_s=budget_s or settings.compose_budget_s)
