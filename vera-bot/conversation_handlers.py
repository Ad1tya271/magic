"""Rule-first classification and conversation state transitions.

Policy is rule-based and deterministic; the LLM path is an optional enrichment
for question/engaged/unclear turns within a hard latency budget.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Any

from vera.language import detect_message_language
from vera.prompts import REPLY_SCHEMA, build_reply_messages
from vera.validate import sanitize_body, validate_message, has_errors

@dataclass
class ConversationState:
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    trigger_id: str | None = None
    send_as: str = "vera"
    turns: list[dict] = field(default_factory=list)
    status: str = "active"
    mode: str = "pitch"
    auto_reply_count: int = 0
    unanswered_nudges: int = 0
    last_language: str = "english"
    topic: str = "business update"

_OPT_OUT = ("stop", "unsubscribe", "not interested", "don't message", "do not message", "band karo", "mat bhejo", "nahi chahiye")
_AUTO = ("thanks for reaching out", "thank you for contacting", "we are currently closed", "we'll get back to you", "we will get back to you", "office hours", "auto-reply", "automatic reply")
_HOSTILE = ("idiot", "stupid", "shut up", "fraud", "scam", "leave me alone")
_COMMIT = ("yes", "ok", "okay", "go ahead", "let's do it", "lets do it", "haan", "karo", "confirm", "join", "send it")
_LATER = ("later", "busy", "not now", "tomorrow", "next week", "baad mein", "kal")
_OFFTOPIC = ("gst", "income tax", "loan", "legal advice", "personal problem", "politics")

def classify_message(text: str, state: ConversationState | None = None, merchant_memory: dict | None = None) -> dict:
    raw = str(text or "").strip(); low = raw.lower()
    signals=[]
    previous = [str(t.get("body", "")).strip().lower() for t in (state.turns if state else []) if t.get("from") in ("merchant","customer")]
    repeated = bool(low and (low in previous or (merchant_memory and low in [str(x).lower() for x in merchant_memory.get("auto_reply_texts", [])])))
    if any(x in low for x in _OPT_OUT): label="opt_out"; signals.append("explicit_opt_out")
    elif repeated or any(x in low for x in _AUTO): label="auto_reply"; signals.append("canned_or_repeated")
    elif any(x in low for x in _HOSTILE): label="hostile"; signals.append("hostile_language")
    elif any(x in low for x in _COMMIT): label="commit"; signals.append("positive_intent")
    elif any(x in low for x in _LATER): label="later"; signals.append("asks_to_wait")
    elif any(x in low for x in _OFFTOPIC): label="off_topic"; signals.append("unrelated_topic")
    elif "?" in raw or low.startswith(("what ","how ","when ","where ","why ","can ","is ","do ")): label="question"; signals.append("question")
    elif len(raw.split()) <= 2 and low in {"no", "no thanks", "maybe", "not interested"}: label="decline_soft"; signals.append("soft_decline")
    elif len(raw.split()) > 2: label="engaged"; signals.append("engaged_text")
    else: label="unclear"
    return {"label":label,"lang":detect_message_language(raw),"signals":signals}

def _append(state, role, body):
    state.turns.append({"from":role,"body":body})

def _prior(state):
    return [str(t.get("body")) for t in state.turns if t.get("from") not in ("merchant","customer")]

def _lang_body(body: str, lang: str) -> str:
    """Adapt the body to match the merchant's detected language."""
    if lang not in {"hinglish", "hindi"}:
        return body
    # Natural Hinglish substitutions for common rule-based responses
    _SWAPS = (
        ("Thanks for the update.", "Update ke liye shukriya."),
        ("Thanks for the note.", "Message ke liye shukriya."),
        ("I'll flag this for the business owner.", "Main yeh business owner tak pahuncha dunga."),
        ("It looks like this is an automated reply.", "Yeh automated reply lag raha hai."),
        ("I can't help with that topic here.", "Main is topic mein yahan help nahi kar paunga."),
        ("I can help with", "Main help kar sakta hoon:"),
        ("Reply YES if you'd like us to follow up.", "Follow-up chahiye toh YES reply kijiye."),
        ("Reply CONFIRM to proceed.", "Aage badhne ke liye CONFIRM reply kijiye."),
        ("Sorry this was unwelcome.", "Sorry, yeh unwelcome tha."),
        ("Reply STOP and we'll end these messages.", "STOP reply kijiye aur hum messages band kar denge."),
        ("The merchant declined; ending politely.", "Merchant ne decline kiya; politely end kar rahe hain."),
        ("whenever you're ready.", "jab aap ready hon."),
    )
    for old, new in _SWAPS:
        body = body.replace(old, new)
    return body

def _rule_response(state, text, classification, merchant_memory):
    label = classification["label"]
    topic = state.topic or "business update"

    if label == "opt_out":
        merchant_memory["opted_out_until"] = "explicit"
        state.status = "ended"
        return {"action": "end", "rationale": "Honored the explicit opt-out."}

    if label == "auto_reply":
        count = int(merchant_memory.get("auto_reply_count", 0)) + 1
        merchant_memory["auto_reply_count"] = count
        merchant_memory.setdefault("auto_reply_texts", []).append(text)
        if count == 1:
            return {
                "action": "send",
                "body": f"It looks like this is an automated reply. I had reached out about {topic}. Reply YES if you'd like us to follow up.",
                "cta": "binary_yes_no",
                "rationale": f"First automated reply detected; flagged for the owner with topic context ({topic}).",
            }
        if count == 2:
            return {"action": "wait", "wait_seconds": 86400, "rationale": "A second automated response arrived; pausing for a day."}
        state.status = "ended"
        return {"action": "end", "rationale": "Further automated replies received; ending this thread."}

    if label == "hostile":
        state.status = "ended"
        return {
            "action": "send",
            "body": "Sorry this was unwelcome. Reply STOP and we'll end these messages.",
            "cta": "none",
            "rationale": "Apologized and provided a clear opt-out path.",
        }

    if label == "later":
        m = re.search(r"(\d+)\s*(hour|hr|day)", text, re.I)
        wait = int(m.group(1)) * ({"hour": 3600, "hr": 3600, "day": 86400}[m.group(2).lower()]) if m else 3600
        return {"action": "wait", "wait_seconds": min(wait, 604800), "rationale": "The merchant asked to continue later."}

    if label == "decline_soft":
        state.status = "ended"
        return {"action": "end", "rationale": "The merchant declined; ending politely."}

    if label == "off_topic":
        return {
            "action": "send",
            "body": f"I can't help with that topic here. I can help with {topic} — want to continue?",
            "cta": "open_ended",
            "rationale": f"Redirected from off-topic request to the active thread ({topic}).",
        }

    if label == "commit":
        state.mode = "action"
        return {
            "action": "send",
            "body": f"Done — sending the {topic} draft for your review now. Reply CONFIRM to proceed.",
            "cta": "binary_confirm_cancel",
            "rationale": f"Confirmed intent and stated the concrete next step ({topic}). No qualifying questions.",
        }

    if len(_prior(state)) >= 5 or state.unanswered_nudges >= 3:
        state.status = "ended"
        return {"action": "end", "rationale": "Conversation limit reached."}

    if label == "question":
        # Try to provide a fact-based answer from the topic context
        return {
            "action": "send",
            "body": f"Checking the details for {topic} — I will share a concise answer from what is available.",
            "cta": "none",
            "rationale": f"Acknowledged the question and committed to answering from available {topic} context.",
        }

    # engaged / unclear
    return {
        "action": "send",
        "body": f"Thanks for the update. Ready to move forward on {topic} whenever you are.",
        "cta": "open_ended",
        "rationale": f"Acknowledged the reply and kept the thread focused on {topic}.",
    }

def respond(state: ConversationState, merchant_message: str) -> dict:
    """Synchronous deterministic response for callers without a running async loop."""
    cls = classify_message(merchant_message, state)
    result = _rule_response(state, merchant_message, cls, {})
    if result.get("action") == "send":
        _append(state, "merchant", merchant_message)
        _append(state, "vera", result["body"])
    return result

async def respond_async(state: ConversationState, merchant_message: str, *, bundle: dict | None,
                        facts: dict | None, llm: Any, budget_s: float, merchant_memory: dict) -> dict:
    try:
        cls = classify_message(merchant_message, state, merchant_memory)
        state.last_language = cls["lang"]
        result = _rule_response(state, merchant_message, cls, merchant_memory)
        if result.get("action") == "send" and cls["label"] in {"question", "engaged", "unclear"} and getattr(llm, "enabled", False) and budget_s > .2:
            system, messages = build_reply_messages(bundle or {}, facts or {}, state.turns, merchant_message, state.mode,
                                                   notes=[f"Reply language for this turn: {cls['lang']}.",
                                                          f"Active topic: {state.topic}."])
            try:
                answer = await llm.complete_json(system=system, messages=messages, schema=REPLY_SCHEMA, max_tokens=700, timeout_s=budget_s)
                if isinstance(answer, dict) and answer.get("action") == "send" and answer.get("body"):
                    candidate = {"action": "send", "body": sanitize_body(answer["body"]), "cta": answer.get("cta", "none"), "rationale": answer.get("rationale", "")}
                    issues = validate_message(candidate, bundle or {}, facts or {}, prior_bodies=_prior(state), mode="reply_action" if state.mode == "action" else "reply")
                    if not has_errors(issues):
                        result = candidate
            except Exception:
                pass
        if result.get("action") == "send":
            body = _lang_body(result.get("body", ""), cls["lang"])
            result["body"] = body
            if body in _prior(state):
                result = {"action": "end", "rationale": "Avoided repeating a previous message."}
                state.status = "ended"
            else:
                _append(state, "merchant", merchant_message)
                _append(state, "vera", body)
        return result
    except Exception:
        return {"action": "end", "rationale": "Unable to continue safely."}
