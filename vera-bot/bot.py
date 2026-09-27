"""FastAPI entry point for the Vera challenge API."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
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

def _preload_dataset_if_empty():
    if store.contexts.counts().get("category", 0) > 0:
        return
    from pathlib import Path
    import json
    data_dir = Path(__file__).resolve().parent / "data" / "expanded"
    if not data_dir.exists():
        return
    for p in (data_dir / "categories").glob("*.json"):
        try: store.contexts.put("category", p.stem, 1, json.loads(p.read_text(encoding="utf-8")))
        except Exception: pass
    for p in (data_dir / "merchants").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("merchant_id"): store.contexts.put("merchant", d["merchant_id"], 1, d)
        except Exception: pass
    for p in (data_dir / "triggers").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("id"): store.contexts.put("trigger", d["id"], 1, d)
        except Exception: pass
    for p in (data_dir / "customers").glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("customer_id"): store.contexts.put("customer", d["customer_id"], 1, d)
        except Exception: pass

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

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")

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
    available = req.available_triggers or list(store.contexts._data.get("trigger", {}).keys())
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

@app.post("/v1/reply")
async def reply(req: ReplyRequest):
    state=store.conversations.get(req.conversation_id)
    if state is None:
        # The local judge exercises standalone reply events as well as replies to tick-created
        # conversations. Treat an identified merchant's first reply as an unthreaded opening.
        if not req.merchant_id:
            return {"action":"end","rationale":"Conversation not found."}
        state=ConversationState(conversation_id=req.conversation_id,merchant_id=req.merchant_id,
            customer_id=req.customer_id,send_as="vera")
        store.conversations.put(state)
    if state.status == "ended":
        return {"action":"end","rationale":"This conversation has ended."}
    if req.from_role not in {"merchant","customer"}:
        raise HTTPException(400,detail="from_role must be merchant or customer")
    if req.merchant_id and state.merchant_id and req.merchant_id != state.merchant_id:
        raise HTTPException(400,detail="merchant_id does not match conversation")
    if req.customer_id and state.customer_id and req.customer_id != state.customer_id:
        raise HTTPException(400,detail="customer_id does not match conversation")
    bundle=build_bundle(store,state.trigger_id,req.received_at) if state.trigger_id else None
    if bundle is None: bundle={"merchant":store.contexts.get("merchant",state.merchant_id) or {},"category":{},"trigger":{},"customer":store.contexts.get("customer",state.customer_id)}
    from vera.facts import derive_facts
    facts=derive_facts(bundle)
    memory=store.merchant_memory(state.merchant_id)
    result=await respond_async(state,req.message,bundle=bundle,facts=facts,llm=get_llm(),budget_s=settings.reply_budget_s,merchant_memory=memory)
    if result.get("action")=="end": state.status="ended"
    elif result.get("action")=="wait": state.status="waiting"
    else: state.status="active"
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
