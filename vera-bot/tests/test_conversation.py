"""Test conversation handlers: classification, transitions, policy, and language matching."""
from __future__ import annotations
import pytest

from conversation_handlers import (
    ConversationState,
    classify_message,
    respond,
    respond_async,
)


def test_classify_opt_out():
    for phrase in ["STOP", "unsubscribe", "not interested", "band karo", "mat bhejo", "nahi chahiye"]:
        res = classify_message(phrase)
        assert res["label"] == "opt_out", f"Expected opt_out for '{phrase}', got '{res['label']}'"


def test_classify_commit():
    for phrase in ["yes", "ok lets do it", "Ok lets do it. Whats next?", "haan karo", "confirm", "go ahead"]:
        res = classify_message(phrase)
        assert res["label"] == "commit", f"Expected commit for '{phrase}', got '{res['label']}'"


def test_classify_hostile():
    for phrase in ["idiot", "shut up", "this is a scam", "fraud"]:
        res = classify_message(phrase)
        assert res["label"] == "hostile", f"Expected hostile for '{phrase}', got '{res['label']}'"


def test_classify_auto_reply():
    for phrase in [
        "Thank you for contacting us! Our team will respond shortly.",
        "We are currently closed. Office hours are 9am to 6pm.",
        "Automatic reply: Out of office",
    ]:
        res = classify_message(phrase)
        assert res["label"] == "auto_reply", f"Expected auto_reply for '{phrase}', got '{res['label']}'"


def test_intent_transition_action_mode():
    state = ConversationState(
        conversation_id="conv_intent_test",
        merchant_id="m_001",
        topic="research digest",
    )
    res = respond(state, "Ok lets do it. Whats next?")
    assert res["action"] == "send"
    assert state.mode == "action"

    body_lower = res["body"].lower()
    actioning = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
    qualifying = ["would you", "do you", "can you tell", "what if", "how about"]

    assert any(w in body_lower for w in actioning), f"Expected actioning words in: {res['body']}"
    assert not any(w in body_lower for w in qualifying), f"Unexpected qualifying words in: {res['body']}"


def test_hostile_handling():
    state = ConversationState(
        conversation_id="conv_hostile_test",
        merchant_id="m_001",
    )
    # 1. Hostile with opt-out
    res1 = respond(state, "Stop messaging me. This is useless spam.")
    assert res1["action"] == "end"
    assert state.status == "ended"

    # 2. Hostile without explicit opt-out
    state2 = ConversationState(conversation_id="conv_hostile_2", merchant_id="m_002")
    res2 = respond(state2, "shut up idiot")
    assert res2["action"] == "send"
    assert "sorry" in res2["body"].lower()
    assert state2.status == "ended"


def test_auto_reply_sequence():
    merchant_memory = {}
    mid = "m_auto_test"

    # Turn 1: Flags for owner, sends 1 message
    s1 = ConversationState(conversation_id="conv_1", merchant_id=mid)
    msg = "Thank you for contacting us! We will get back to you."
    cls1 = classify_message(msg, s1, merchant_memory)
    r1 = respond_async
    # test synchronous logic directly
    from conversation_handlers import _rule_response
    res1 = _rule_response(s1, msg, cls1, merchant_memory)
    assert res1["action"] == "send"

    # Turn 2: Waits 86400
    s2 = ConversationState(conversation_id="conv_2", merchant_id=mid)
    cls2 = classify_message(msg, s2, merchant_memory)
    res2 = _rule_response(s2, msg, cls2, merchant_memory)
    assert res2["action"] == "wait"
    assert res2["wait_seconds"] == 86400

    # Turn 3: Ends
    s3 = ConversationState(conversation_id="conv_3", merchant_id=mid)
    cls3 = classify_message(msg, s3, merchant_memory)
    res3 = _rule_response(s3, msg, cls3, merchant_memory)
    assert res3["action"] == "end"


def test_off_topic_redirect():
    state = ConversationState(
        conversation_id="conv_offtopic",
        merchant_id="m_001",
        topic="Diwali campaign",
    )
    res = respond(state, "Can you help me file my GST return?")
    assert res["action"] == "send"
    assert "Diwali campaign" in res["body"]


def test_later_wait():
    state = ConversationState(
        conversation_id="conv_later",
        merchant_id="m_001",
    )
    res = respond(state, "busy right now, message me in 2 hours")
    assert res["action"] == "wait"
    assert res["wait_seconds"] == 7200
