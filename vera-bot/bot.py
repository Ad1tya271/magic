"""FastAPI entry point for the Vera challenge API."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import re
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from vera.config import settings
from vera.composer import compose_message
from conversation_handlers import ConversationState, respond_async
from vera.llm import get_llm
from vera.planner import build_bundle, select_candidates
from vera.store import SCOPES, store
from vera.ui import DASHBOARD_HTML

app = FastAPI(title="Vera Bot", version=settings.version)
_STARTED=time.monotonic()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

def _preload_dataset_if_empty():
    if store.contexts.counts().get("category", 0) > 0:
        return
    from pathlib import Path
    import json
    now_ts = _now()
    base = Path(__file__).resolve().parent
    data_dirs = [base / "data" / "expanded", base.parent / "magicpin-ai-challenge" / "dataset"]
    for data_dir in data_dirs:
        if not data_dir.exists():
            continue
        cat_dir = data_dir / "categories"
        if cat_dir.exists():
            for p in cat_dir.glob("*.json"):
                try:
                    store.contexts.put("category", p.stem, 0, json.loads(p.read_text(encoding="utf-8")), stored_at=now_ts)
                except Exception:
                    pass
        m_dir = data_dir / "merchants"
        if m_dir.exists():
            for p in m_dir.glob("*.json"):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    mid = d.get("merchant_id") or d.get("id") or p.stem
                    store.contexts.put("merchant", mid, 0, d, stored_at=now_ts)
                except Exception:
                    pass
        t_dir = data_dir / "triggers"
        if t_dir.exists():
            for p in t_dir.glob("*.json"):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    tid = d.get("id") or d.get("trigger_id") or p.stem
                    store.contexts.put("trigger", tid, 0, d, stored_at=now_ts)
                except Exception:
                    pass
        c_dir = data_dir / "customers"
        if c_dir.exists():
            for p in c_dir.glob("*.json"):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    cid = d.get("customer_id") or d.get("id") or p.stem
                    store.contexts.put("customer", cid, 0, d, stored_at=now_ts)
                except Exception:
                    pass
        if store.contexts.counts().get("category", 0) > 0:
            break

_preload_dataset_if_empty()

@app.get("/", response_class=HTMLResponse)
async def index():
    _preload_dataset_if_empty()
    return HTMLResponse(DASHBOARD_HTML)

class ContextRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: dict[str, Any]
    delivered_at: str | None = None

class TickRequest(BaseModel):
    now: str | None = None
    available_triggers: list[str] = []

class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: str | None = None
    customer_id: str | None = None
    from_role: str = "merchant"
    message: str
    received_at: str | None = None
    turn_number: int | None = None


@app.post("/v1/context")
async def context_push(req: ContextRequest):
    if req.scope not in SCOPES:
        raise HTTPException(400,detail={"accepted":False,"reason":"invalid_scope","details":f"scope must be one of {SCOPES}"})
    if not req.context_id or req.version < 0:
        raise HTTPException(400,detail={"accepted":False,"reason":"invalid_context","details":"context_id and non-negative version required"})
    stored_at=_now()
    accepted,current=store.contexts.put(req.scope,req.context_id,req.version,req.payload,stored_at=stored_at,delivered_at=req.delivered_at)
    if not accepted:
        return {"accepted":False,"reason":"stale_version","current_version":current}
    ack=hashlib.sha256(f"{req.context_id}:{req.version}".encode()).hexdigest()[:12]
    return {"accepted":True,"ack_id":f"ack_{ack}","stored_at":stored_at}

@app.post("/v1/tick")
async def tick(req: TickRequest):
    now=req.now or settings.default_now
    available = req.available_triggers or [ctx.context_id for ctx in store.contexts.items("trigger")]
    candidates=select_candidates(store,available,now)
    actions=[]
    llm=get_llm()
    for candidate in candidates:
        bundle=candidate["bundle"]
        prior=store.bot_bodies_for(candidate["merchant_id"],candidate["customer_id"])
        msg=await compose_message(bundle,llm=llm,budget_s=settings.tick_budget_s,prior_bodies=prior)
        if msg.get("skip"):
            continue
        cid=store.conversations.reserve_id("conv_"+uuid.uuid4().hex[:16])
        state=ConversationState(conversation_id=cid,merchant_id=candidate["merchant_id"],
            customer_id=candidate["customer_id"],trigger_id=candidate["trigger_id"],send_as=msg.get("send_as","vera"),
            turns=[{"from":"vera","body":msg["body"],"ts":now}],topic=candidate["kind"].replace("_"," "))
        store.conversations.put(state)
        store.mark_sent(msg.get("suppression_key")); store.mark_trigger_used(candidate["trigger_id"])
        actions.append({"conversation_id":cid,"merchant_id":candidate["merchant_id"],"customer_id":candidate["customer_id"] if msg.get("send_as")=="merchant_on_behalf" else None,
            "send_as":msg.get("send_as","vera"),"trigger_id":candidate["trigger_id"],"template_name":msg.get("template_name",""),
            "template_params":msg.get("template_params",[]),"body":msg["body"],"cta":msg.get("cta","none"),
            "suppression_key":msg.get("suppression_key",""),"rationale":msg.get("rationale","")})
    return {"actions":actions}

def match_merchant(text: str, store_obj) -> tuple[str | None, dict | None]:
    low = text.lower().strip()
    merchants = list(store_obj.contexts.items("merchant"))
    # 1. Exact ID
    for m in merchants:
        if m.context_id.lower() == low:
            return m.context_id, m.payload
    # 2. Match owner or business name
    for m in merchants:
        p = m.payload or {}
        owner = str(p.get("identity", {}).get("owner_first_name", "")).lower()
        bname = str(p.get("identity", {}).get("name", "")).lower()
        if owner and (owner == low or owner in low):
            return m.context_id, p
        if bname and (bname in low or low in bname):
            return m.context_id, p
    # 3. Partial keyword matching on common tokens
    tokens = [tok for tok in re.findall(r"\w+", low) if len(tok) >= 3 and tok not in {"the", "and", "restaurant", "clinic", "salon", "vendor", "partner", "shop"}]
    for m in merchants:
        p = m.payload or {}
        owner = str(p.get("identity", {}).get("owner_first_name", "")).lower()
        bname = str(p.get("identity", {}).get("name", "")).lower()
        for tok in tokens:
            if (owner and tok in owner) or (bname and tok in bname):
                return m.context_id, p
    return None, None


def get_vendor_suggestions(p: dict) -> list[str]:
    cat = p.get("category_slug", "")
    offers = [o.get("title") for o in p.get("offers", []) if o.get("status") == "active" and o.get("title")]
    offer_str = offers[0] if offers else "current promotion"
    if cat == "restaurants":
        return [
            "Mid-week dining footfall kaise badhayein?",
            f"Active offer ({offer_str}) push karein",
            "Corporate lunch packages",
            "What about Option 3 or a custom package?",
            "Weekend dining special promo"
        ]
    elif cat == "dentists":
        return [
            "JIDA research study ke baare mein batao",
            "78 lapsed patients recall strategy",
            f"Active offer ({offer_str})",
            "Option B (Aligners vs Braces guide)",
            "What about Option 3 or a custom package?"
        ]
    elif cat == "salons":
        return [
            "Bridal season demand trends (+48% YoY)",
            "220 lapsed clients reactivation",
            f"Active offer ({offer_str})",
            "Option 2 (Bridal Trial @ ₹999)",
            "What about Option 3 or a custom package?"
        ]
    elif cat == "gyms":
        return [
            "Morning HIIT batch demand ka data",
            "Kids yoga summer camp plan",
            f"Active offer ({offer_str})",
            "Member retention strategy",
            "What about Option 3 or a custom package?"
        ]
    elif cat == "pharmacies":
        return [
            "Chronic medication refill schedule",
            "Seasonal hydration ORS essentials",
            f"Active offer ({offer_str})",
            "Option 2 (Family wellness kit)",
            "What about Option 3 or a custom package?"
        ]
    else:
        return [
            f"How to optimize my active offer ({offer_str})?",
            "Reactivating lapsed customers this week",
            "Competitor pricing and demand analysis",
            "What about Option 3 or a custom package?"
        ]


@app.get("/v1/merchants")
async def list_merchants():
    _preload_dataset_if_empty()
    merchants = []
    featured_order = [
        "m_005_pizzajunction_restaurant_delhi",
        "m_001_drmeera_dentist_delhi",
        "m_003_studio11_salon_hyderabad",
        "m_008_zenyoga_gym_chennai",
        "m_009_apollo_pharmacy_jaipur"
    ]
    seen = set()
    for f_id in featured_order:
        item = store.contexts.get("merchant", f_id)
        if item:
            ident = item.get("identity", {})
            offers = [o.get("title") for o in item.get("offers", []) if o.get("status") == "active" and o.get("title")]
            merchants.append({
                "merchant_id": f_id,
                "owner_first_name": ident.get("owner_first_name", ""),
                "name": ident.get("name", ""),
                "category_slug": item.get("category_slug", ""),
                "locality": ident.get("locality") or item.get("location", {}).get("locality", ""),
                "city": ident.get("city") or item.get("location", {}).get("city", ""),
                "active_offers": offers,
                "suggestions": get_vendor_suggestions(item)
            })
            seen.add(f_id)

    for item in store.contexts.items("merchant"):
        if item.context_id in seen:
            continue
        p = item.payload or {}
        ident = p.get("identity", {})
        offers = [o.get("title") for o in p.get("offers", []) if o.get("status") == "active" and o.get("title")]
        merchants.append({
            "merchant_id": item.context_id,
            "owner_first_name": ident.get("owner_first_name", ""),
            "name": ident.get("name", ""),
            "category_slug": p.get("category_slug", ""),
            "locality": ident.get("locality") or p.get("location", {}).get("locality", ""),
            "city": ident.get("city") or p.get("location", {}).get("city", ""),
            "active_offers": offers,
            "suggestions": get_vendor_suggestions(p)
        })
    return {"merchants": merchants}


@app.post("/v1/reply")
async def reply(req: ReplyRequest):
    _preload_dataset_if_empty()
    state = store.conversations.get(req.conversation_id)
    low = req.message.lower().strip()

    # Vendor switch request
    if any(w in low for w in ["switch vendor", "change vendor", "different vendor", "select vendor", "another vendor", "vendor badlo", "dusra vendor", "switch merchant"]):
        if state is None:
            state = ConversationState(conversation_id=req.conversation_id, send_as="vera", conv_state="SELECTING_VENDOR")
            store.conversations.put(state)
        else:
            state.merchant_id = None
            state.trigger_id = None
            state.conv_state = "SELECTING_VENDOR"
            state.turns = []
        return {
            "action": "send",
            "body": "Sure! Which restaurant or vendor would you like to switch to?",
            "conv_state": "SELECTING_VENDOR",
            "rationale": "Initiated conversational vendor selection."
        }

    # State initialization or vendor selection
    if state is None:
        if req.merchant_id:
            m_triggers = [t for t in store.contexts.items("trigger") if t.payload.get("merchant_id") == req.merchant_id]
            tid = m_triggers[0].context_id if m_triggers else None
            state = ConversationState(conversation_id=req.conversation_id, merchant_id=req.merchant_id,
                customer_id=req.customer_id, trigger_id=tid, send_as="vera", topic="business update",
                conv_state="CONVERSING")
            store.conversations.put(state)
        else:
            matched_id, m_payload = match_merchant(req.message, store)
            if matched_id:
                m_triggers = [t for t in store.contexts.items("trigger") if t.payload.get("merchant_id") == matched_id]
                tid = m_triggers[0].context_id if m_triggers else None
                state = ConversationState(conversation_id=req.conversation_id, merchant_id=matched_id,
                    customer_id=req.customer_id, trigger_id=tid, send_as="vera", topic="business update",
                    conv_state="VENDOR_SELECTED")
                store.conversations.put(state)
                owner = m_payload.get("identity", {}).get("owner_first_name", "there")
                bname = m_payload.get("identity", {}).get("name", "your business")
                loc = m_payload.get("identity", {}).get("locality") or m_payload.get("location", {}).get("locality", "")
                city = m_payload.get("identity", {}).get("city") or m_payload.get("location", {}).get("city", "")
                loc_str = f" ({loc}, {city})" if loc else ""
                suggestions = get_vendor_suggestions(m_payload)
                return {
                    "action": "send",
                    "body": f"Great, {owner}! I've loaded the details for {bname}{loc_str}. What would you like help with today?",
                    "conv_state": "VENDOR_SELECTED",
                    "vendor_id": matched_id,
                    "vendor_name": bname,
                    "owner_name": owner,
                    "suggestions": suggestions,
                    "rationale": "Loaded vendor business context and presented tailored suggestions."
                }
            else:
                state = ConversationState(conversation_id=req.conversation_id, send_as="vera", conv_state="SELECTING_VENDOR")
                store.conversations.put(state)
                return {
                    "action": "send",
                    "body": f"I couldn't find a vendor matching '{req.message}'. Please choose an available vendor from below or type the exact business or owner name (e.g. Suresh, Dr. Meera, Lakshmi, Padma, Ramesh):",
                    "conv_state": "SELECTING_VENDOR",
                    "rationale": "Requested clarification for unrecognized vendor name."
                }

    if state.conv_state == "SELECTING_VENDOR" or not state.merchant_id:
        matched_id, m_payload = match_merchant(req.message, store)
        if matched_id:
            state.merchant_id = matched_id
            m_triggers = [t for t in store.contexts.items("trigger") if t.payload.get("merchant_id") == matched_id]
            state.trigger_id = m_triggers[0].context_id if m_triggers else None
            state.conv_state = "VENDOR_SELECTED"
            owner = m_payload.get("identity", {}).get("owner_first_name", "there")
            bname = m_payload.get("identity", {}).get("name", "your business")
            loc = m_payload.get("identity", {}).get("locality") or m_payload.get("location", {}).get("locality", "")
            city = m_payload.get("identity", {}).get("city") or m_payload.get("location", {}).get("city", "")
            loc_str = f" ({loc}, {city})" if loc else ""
            suggestions = get_vendor_suggestions(m_payload)
            return {
                "action": "send",
                "body": f"Great, {owner}! I've loaded the details for {bname}{loc_str}. What would you like help with today?",
                "conv_state": "VENDOR_SELECTED",
                "vendor_id": matched_id,
                "vendor_name": bname,
                "owner_name": owner,
                "suggestions": suggestions,
                "rationale": "Loaded vendor business context and presented tailored suggestions."
            }
        else:
            return {
                "action": "send",
                "body": f"I couldn't find a vendor matching '{req.message}'. Please choose an available vendor from below or type the exact business or owner name (e.g. Suresh, Dr. Meera, Lakshmi, Padma, Ramesh):",
                "conv_state": "SELECTING_VENDOR",
                "rationale": "Requested clarification for unrecognized vendor name."
            }

    if state.status == "ended":
        return {"action": "end", "rationale": "This conversation has ended."}
    if req.from_role not in {"merchant", "customer"}:
        raise HTTPException(400, detail="from_role must be merchant or customer")
    if req.merchant_id and state.merchant_id and req.merchant_id != state.merchant_id:
        raise HTTPException(400, detail="merchant_id does not match conversation")
    if req.customer_id and state.customer_id and req.customer_id != state.customer_id:
        raise HTTPException(400, detail="customer_id does not match conversation")

    state.conv_state = "CONVERSING"
    bundle = build_bundle(store, state.trigger_id, req.received_at) if state.trigger_id else None
    if bundle is None:
        m_payload = store.contexts.get("merchant", state.merchant_id) or {}
        cat_slug = m_payload.get("category_slug")
        c_payload = store.contexts.get("category", cat_slug) or {} if cat_slug else {}
        bundle = {
            "merchant": m_payload,
            "category": c_payload,
            "trigger": store.contexts.get("trigger", state.trigger_id) or {} if state.trigger_id else {},
            "customer": store.contexts.get("customer", state.customer_id) if state.customer_id else None,
            "now": req.received_at or settings.default_now
        }
    from vera.facts import derive_facts
    facts = derive_facts(bundle)
    memory = store.merchant_memory(state.merchant_id)
    result = await respond_async(state, req.message, bundle=bundle, facts=facts, llm=get_llm(), budget_s=settings.reply_budget_s, merchant_memory=memory)
    if result.get("action") == "end": state.status = "ended"
    elif result.get("action") == "wait": state.status = "waiting"
    else: state.status = "active"
    return result

@app.get("/v1/healthz")
async def healthz():
    return {"status":"ok","uptime_seconds":int(time.monotonic()-_STARTED),"contexts_loaded":store.contexts.counts()}

@app.get("/v1/metadata")
async def metadata():
    return {"team_name":settings.team_name,"team_members":settings.team_members,"model":getattr(get_llm(),"model",settings.model),
        "approach":settings.approach,"contact_email":settings.contact_email,"version":settings.version,"submitted_at":settings.submitted_at}

@app.post("/v1/teardown")
async def teardown():
    store.reset()
    llm=get_llm()
    if hasattr(llm,"clear_memo"): llm.clear_memo()
    return {"status":"ok"}

def compose(bundle: dict, merchant: dict | None = None, trigger: dict | None = None,
            customer: dict | None = None, *, prior_bodies: list[str] | None = None):
    """Sync convenience entry point used by local submission tooling."""
    import asyncio
    if merchant is not None and trigger is not None:
        category=bundle or {}
        bundle={"category":category,"merchant":merchant,"trigger":trigger,"customer":customer,"now":settings.default_now}
    return asyncio.run(compose_message(bundle,llm=get_llm(),budget_s=settings.compose_budget_s,prior_bodies=prior_bodies))
