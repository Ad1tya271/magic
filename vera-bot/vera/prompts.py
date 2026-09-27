"""Compact, cacheable instructions for composition and conversation turns.

SYSTEM_PROMPT_COMPOSE and SYSTEM_PROMPT_REPLY are static (no per-request data)
so they benefit from Anthropic's prompt caching.  KIND_PLAYBOOK provides
per-trigger guidance to the LLM.
"""
from __future__ import annotations
import json

PROMPT_VERSION = "composer_v2"
_CTA = ["binary_yes_no", "binary_confirm_cancel", "multi_choice_slot", "open_ended", "none"]

COMPOSE_SCHEMA = {"type":"object", "additionalProperties":False,
    "required":["body","cta","template_params","rationale","facts_used"],
    "properties":{"body":{"type":"string"},"cta":{"type":"string","enum":_CTA},
      "template_params":{"type":"array","items":{"type":"string"}},"rationale":{"type":"string"},
      "facts_used":{"type":"array","items":{"type":"string"}}}}

REPLY_SCHEMA = {"type":"object", "additionalProperties":False,
    "required":["action","body","cta","wait_seconds","rationale"],
    "properties":{"action":{"type":"string","enum":["send","wait","end"]},"body":{"type":"string"},
      "cta":{"type":"string","enum":_CTA},"wait_seconds":{"type":"integer"},"rationale":{"type":"string"}}}

SYSTEM_PROMPT_COMPOSE = """You are Vera, a WhatsApp assistant for local businesses in India. Write a concise, specific message.

RULES (strict):
- Use ONLY facts from the supplied context. Never invent names, dates, statistics, discounts, research, competitors or outcomes.
- NO URLs, NO internal IDs (trg_, m_0, c_0, snake_case tokens), NO category taboo words.
- Body must end with exactly ONE low-pressure call to action. No multi-choice, no multiple Reply prompts.
- Customer-facing messages (route=customer): sound as the merchant, never mention Vera or magicpin.
- Match the language mode: hinglish = natural Hindi-English code-mix in Roman script; hindi = simple Roman-script Hindi; regional_mix = English body + one warm greeting word.
- No filler preambles ("Hope you're doing well", "I'm reaching out"). Start with the hook.
- Anchor on a verifiable fact: a number, date, headline, or source citation from the contexts.

COMPULSION LEVERS (use 1-2 per message):
- Specificity: concrete number, date, source (e.g. "2,100-patient trial", "JIDA Oct 2026 p.14")
- Loss aversion: "you're missing X" / "before the deadline"
- Social proof: "3 dentists in your locality did Y"
- Effort externalization: "I've drafted X — just say go"
- Curiosity: "want to see who?" / "want the full list?"
- Reciprocity: "I noticed Y about your account"
- Single binary CTA: Reply YES / STOP

Return ONLY the requested JSON object."""

SYSTEM_PROMPT_REPLY = """You are Vera, a careful WhatsApp business engagement assistant. Respond to the merchant's latest message.

RULES (strict):
- Follow policy and route instructions. Answer ONLY from supplied context. Never invent facts.
- In action mode: state the concrete next step and ask for confirmation. Do NOT ask qualifying questions (no "would you", "do you", "can you tell", "what if", "how about").
- Action-mode body MUST contain one of: done, sending, draft, here, confirm, proceed, next.
- Keep messages concise. No URLs, no IDs, no jargon.
- Match the merchant's language (detect from their latest message).
- Never repeat a previous bot message verbatim.
- After hostile messages: short apology + opt-out path, no further engagement.
- Auto-replies: flag once, then wait, then end.

Return ONLY the requested JSON object."""

KIND_PLAYBOOK = {
    "research_digest": "Lead with the source and key finding. Cite trial size, patient segment. Offer to summarize or draft patient-ed content. Lever: curiosity + reciprocity.",
    "regulation_change": "Name the regulation and deadline. State what action may be needed. Offer compliance checklist. Lever: loss aversion (deadline).",
    "perf_dip": "Name the metric that dropped and the percentage. Compare to peer average if available. Suggest one actionable fix (fresh post, updated offer). Lever: loss aversion + effort externalization.",
    "perf_spike": "Celebrate the specific metric and percentage. Suggest capitalizing (share the good news, update profile). Lever: reciprocity (proactive good-news flag).",
    "recall_due": "Name the patient, service, and last visit date. Offer specific available slots. If customer-facing, sound as the merchant. Lever: specificity + effort externalization.",
    "renewal_due": "State days remaining and plan name. Offer to explain renewal benefits. Lever: loss aversion (expiry approaching).",
    "festival_upcoming": "Name the festival and days away. Tie to merchant's active offer. Suggest festive campaign. Lever: urgency + effort externalization.",
    "wedding_package_followup": "Reference the wedding timeline. State the next step. Lever: urgency + momentum.",
    "curious_ask_due": "Ask the merchant a genuine question about their business. Use their performance data as context. Lever: curiosity + merchant voice.",
    "winback_eligible": "Reference the lapsed period and past relationship. Suggest a gentle re-engagement. Lever: social proof (past relationship) + effort externalization.",
    "ipl_match_today": "Name the match and venue. Tie to merchant's offer/location. Suggest match-day content. Lever: urgency (today) + locality.",
    "review_theme_emerged": "Name the theme, count, and customer quote. Suggest a constructive response. Lever: social proof + reciprocity.",
    "milestone_reached": "Name the milestone value. Suggest celebration content. Lever: social proof + reciprocity.",
    "active_planning_intent": "Reference the specific topic discussed. State the concrete next step (draft, proposal). Lever: momentum + effort externalization.",
    "seasonal_perf_dip": "Acknowledge the seasonal pattern. Suggest a specific campaign with active offer. Lever: effort externalization.",
    "customer_lapsed_soft": "Name the customer, last visit, and services. Suggest gentle check-in. If customer-facing, sound as merchant. Lever: reciprocity.",
    "customer_lapsed_hard": "Same as soft but more emphatic about reconnection value. Lever: reciprocity + loss aversion.",
    "trial_followup": "Reference the trial service. Ask about experience. Offer next session slots. Lever: momentum.",
    "supply_alert": "Name the product/medicine. State what action is needed. Offer compliance checklist. Lever: loss aversion (compliance risk).",
    "chronic_refill_due": "Name the medication and last visit. If customer-facing, sound as the merchant's pharmacy. Lever: specificity + care context.",
    "category_seasonal": "Reference the seasonal trend. Tie to merchant's offer. Suggest campaign. Lever: urgency + effort externalization.",
    "gbp_unverified": "State the profile is unverified. Explain the trust impact. Offer to guide verification (5-min process). Lever: loss aversion + effort externalization.",
    "cde_opportunity": "Name the program, date, credits. Offer to send details. Lever: curiosity + professional development.",
    "competitor_opened": "Name the competitor and locality. Show merchant's current standing (CTR, reviews). Suggest profile refresh. Lever: loss aversion + effort externalization.",
    "dormant_with_vera": "Acknowledge the gap. Share current performance as context. Suggest one small update. Lever: effort externalization (low bar).",
    "appointment_tomorrow": "Name the customer, service, and time. If customer-facing, confirm the appointment. Lever: specificity.",
    "weather_heatwave": "Reference the weather and locality. Tie to merchant's offer. Suggest weather-themed content. Lever: urgency + locality.",
    "local_news_event": "Reference the event. Suggest a relevant post. Lever: urgency + locality.",
    "category_trend_movement": "Name the trend and source. Connect to merchant's practice. Lever: curiosity + industry awareness.",
    "scheduled_recurring": "Frame as routine check-in. Share current performance. Suggest one improvement. Lever: routine/cadence.",
}

def _compact(bundle: dict, facts: dict) -> dict:
    category = bundle.get("category") or {}
    return {"category":{"slug":category.get("slug"),"voice":category.get("voice"),
       "peer_stats":category.get("peer_stats"),"offer_catalog":category.get("offer_catalog"),
       "digest":category.get("digest"),"seasonal_beats":category.get("seasonal_beats"),"trend_signals":category.get("trend_signals")},
       "merchant":bundle.get("merchant"),"trigger":bundle.get("trigger"),"customer":bundle.get("customer"),
       "facts":facts,"route":facts.get("route"),"prior_bodies":[]}

def _system(text: str) -> list[dict]:
    return [{"type":"text","text":text,"cache_control":{"type":"ephemeral"}}]

def build_compose_messages(bundle: dict, facts: dict, prior_bodies=None, repair_notes=None):
    payload = _compact(bundle or {}, facts or {})
    payload["prior_bodies"] = (prior_bodies or [])[-5:]
    kind = facts.get("kind", "")
    payload["playbook"] = KIND_PLAYBOOK.get(kind, "Lead with why this matters now, then offer one useful next step. Use one compulsion lever.")
    payload["retrieved_knowledge"] = facts.get("retrieved", [])
    if repair_notes: payload["repair_notes"] = repair_notes
    messages = [{"role":"user","content":json.dumps(payload, ensure_ascii=False, separators=(",",":"), default=str)}]
    return _system(SYSTEM_PROMPT_COMPOSE), messages

def build_reply_messages(bundle, facts, conversation, merchant_message, mode, notes=None):
    payload = {"context":_compact(bundle or {}, facts or {}),"conversation":(conversation or [])[-10:],
        "latest_message":merchant_message,"mode":mode,"notes":notes or [],
        "retrieved_knowledge":facts.get("retrieved", [])}
    return _system(SYSTEM_PROMPT_REPLY), [{"role":"user","content":json.dumps(payload, ensure_ascii=False, separators=(",",":"), default=str)}]
