"""Small deterministic BM25 retrieval over the context already supplied to the bot."""
from __future__ import annotations
import math
import re
from typing import Any

_STOP=set("a an and are as at be by for from has have in is it of on or that the this to was were with your you we i our".split())
_SYN={"teeth":"dental","dentist":"dental","haircut":"hair","gym":"fitness","workout":"fitness","medicine":"pharmacy","drug":"pharmacy","sale":"offer","deal":"offer"}
_EXPAND={"perf_dip":"calls views dip decline ctr post offer visibility", "recall_due":"recall checkup cleaning visit appointment slot reminder", "competitor_opened":"competitor new nearby price offer", "supply_alert":"recall batch medicine supply alert", "research_digest":"research study trial clinical evidence", "renewal_due":"subscription expiry renewal plan", "active_planning_intent":"planning idea draft customer program campaign"}

def _tokens(text: Any) -> list[str]:
    out=[]
    for word in re.findall(r"[a-z0-9]+",str(text or "").lower()):
        if word in _STOP: continue
        if len(word)>5 and word.endswith("ing"): word=word[:-3]
        elif len(word)>4 and word.endswith("ed"): word=word[:-2]
        elif len(word)>3 and word.endswith("s"): word=word[:-1]
        out.append(_SYN.get(word,word))
    return out

def build_docs(bundle: dict) -> list[dict]:
    docs=[]
    def add(ident,typ,text,obj):
        if text: docs.append({"id":str(ident or f"{typ}_{len(docs)}"),"type":typ,"text":str(text),"source_obj":obj,"numbers":re.findall(r"\d+(?:\.\d+)?",str(text))})
    cat=bundle.get("category") or {}; mer=bundle.get("merchant") or {}; trig=bundle.get("trigger") or {}; cus=bundle.get("customer") or {}
    for section,typ in (("digest","digest"),("patient_content_library","patient_content"),("seasonal_beats","seasonal"),("trend_signals","trend"),("offer_catalog","catalog_offer")):
        for i,obj in enumerate(cat.get(section) or []):
            if isinstance(obj,dict): add(obj.get("id"),typ," ".join(f"{k}: {v}" for k,v in obj.items() if k!="id"),obj)
    if cat.get("peer_stats"): add("peer_stats","peer_stats",cat["peer_stats"],cat["peer_stats"])
    for section,typ in (("offers","offer"),("review_themes","review"),("conversation_history","conversation"),("signals","signal"),("performance","performance"),("customer_aggregate","aggregate")):
        for i,obj in enumerate(mer.get(section) or []):
            if isinstance(obj,dict): add(obj.get("id"),typ," ".join(f"{k}: {v}" for k,v in obj.items() if k!="id"),obj)
            elif isinstance(obj,str): add(f"{typ}_{i}",typ,obj,obj)
    if cus:
        add(cus.get("customer_id"),"customer",cus,cus)
    return docs

def retrieve(bundle: dict, *, k: int = 6, extra_query: str | None = None) -> list[dict]:
    docs=build_docs(bundle)
    trig=bundle.get("trigger") or {}; payload=trig.get("payload") or {}
    merchant=bundle.get("merchant") or {}; customer=bundle.get("customer") or {}
    query=" ".join([_EXPAND.get(trig.get("kind"),""),str(payload),str(merchant.get("signals",[])),str(customer.get("relationship",{})),str(extra_query or "")])
    q=_tokens(query); n=len(docs); avg=sum(len(_tokens(d["text"])) for d in docs)/max(1,n)
    df={t:sum(t in set(_tokens(d["text"])) for d in docs) for t in set(q)}
    referenced={payload.get(x) for x in ("top_item_id","digest_item_id","alert_id","item_id") if payload.get(x)}
    novel=set(bundle.get("novel_digest_ids") or [])
    month=str((bundle.get("now") or "")[:7])
    scored=[]
    for doc in docs:
        terms=_tokens(doc["text"]); counts={t:terms.count(t) for t in set(terms)}; score=0.0
        for term in q:
            f=counts.get(term,0)
            if f: score += math.log(1+(n-df.get(term,0)+.5)/(df.get(term,0)+.5))*f*2.5/(f+1.5*(.25+.75*len(terms)/max(1,avg)))
        if doc["id"] in referenced: score += 100
        if doc["id"] in novel: score += 5
        priors={"digest":2,"seasonal":1.5,"trend":1.5,"review":1.4,"performance":1.3,"signal":1.2}
        if score > 0: score+=priors.get(doc["type"],0)
        if score > 0 and month and month[5:7] in doc["text"]: score+=.25
        scored.append((score,doc))
    scored.sort(key=lambda item:(-item[0],item[1]["id"]))
    return [{"id":d["id"],"type":d["type"],"text":d["text"],"score":round(s,6)} for s,d in scored[:max(0,k)] if s>0]

def answer_snippets(bundle: dict, question: str, *, k: int = 3) -> list[dict]:
    return retrieve(bundle,k=k,extra_query=question)
