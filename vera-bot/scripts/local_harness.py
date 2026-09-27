"""Local test harness to simulate end-to-end Vera Bot operations.

Runs context ingestion, tick message generation, multi-turn conversation
simulation, and optionally opens an interactive WhatsApp simulation console.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "expanded"
BOT_URL = os.environ.get("BOT_URL", "http://127.0.0.1:8000")


def print_banner(text: str):
    print("\n" + "=" * 65)
    print(f"  {text}")
    print("=" * 65 + "\n")


def print_msg(title: str, body: str, meta: dict | None = None):
    print(f"┌── [ {title} ] " + "─" * (50 - len(title)))
    for line in body.split("\n"):
        print(f"│ {line}")
    if meta:
        print("├" + "─" * 63)
        for k, v in meta.items():
            print(f"│  • {k}: {v}")
    print("└──" + "─" * 61 + "\n")


def _load_json_files(directory: Path, id_field: str) -> dict[str, dict]:
    found = {}
    for p in directory.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            ident = data.get(id_field)
            if ident:
                found[ident] = data
        except Exception:
            continue
    return found


def run_simulation(interactive: bool = False):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    client = httpx.Client(base_url=BOT_URL, timeout=10.0)

    # 1. Health & Metadata Check
    print_banner("1. HEALTH & METADATA CHECK")
    try:
        health = client.get("/v1/healthz").json()
        meta = client.get("/v1/metadata").json()
        print(f"[OK] Bot is online: {BOT_URL}")
        print(f"     Status: {health['status']} | Uptime: {health['uptime_seconds']}s")
        print(f"     Team: {meta['team_name']} | Version: {meta['version']}")
        print(f"     Active Model: {meta['model']}")
    except Exception as e:
        print(f"[ERROR] Could not connect to bot at {BOT_URL}: {e}")
        print("Please ensure the bot server is running (`uvicorn bot:app --port 8000`)")
        return

    # 2. Ingest Context
    print_banner("2. INGESTING CONTEXT DATA")
    client.post("/v1/teardown")
    categories = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (DATA_DIR / "categories").glob("*.json")}
    merchants = _load_json_files(DATA_DIR / "merchants", "merchant_id")
    triggers = _load_json_files(DATA_DIR / "triggers", "id")
    customers = _load_json_files(DATA_DIR / "customers", "customer_id")

    # Push categories
    for slug, cat in categories.items():
        client.post("/v1/context", json={"scope": "category", "context_id": slug, "version": 1, "payload": cat})
    print(f"[OK] Pushed {len(categories)} categories")

    # Push sample merchants
    sample_mids = list(merchants.keys())[:5]
    for mid in sample_mids:
        client.post("/v1/context", json={"scope": "merchant", "context_id": mid, "version": 1, "payload": merchants[mid]})
    print(f"[OK] Pushed {len(sample_mids)} merchants")

    # Push sample customers
    sample_cids = list(customers.keys())[:5]
    for cid in sample_cids:
        client.post("/v1/context", json={"scope": "customer", "context_id": cid, "version": 1, "payload": customers[cid]})
    print(f"[OK] Pushed {len(sample_cids)} customers")

    # Push sample triggers
    sample_trig_ids = list(triggers.keys())[:6]
    for tid in sample_trig_ids:
        client.post("/v1/context", json={"scope": "trigger", "context_id": tid, "version": 1, "payload": triggers[tid]})
    print(f"[OK] Pushed {len(sample_trig_ids)} triggers")

    # 3. Simulate Tick
    print_banner("3. SIMULATING TICK EVENT")
    tick_resp = client.post("/v1/tick", json={
        "now": "2026-04-26T10:00:00Z",
        "available_triggers": sample_trig_ids,
    }).json()

    actions = tick_resp.get("actions", [])
    print(f"[OK] Bot evaluated triggers and composed {len(actions)} proactive action(s):\n")

    conversations = {}
    for i, act in enumerate(actions, 1):
        cid = act["conversation_id"]
        conversations[cid] = act
        meta_info = {
            "To": act.get("customer_id") or act.get("merchant_id"),
            "Role": act.get("send_as"),
            "CTA": act.get("cta"),
            "Trigger": act.get("trigger_id"),
            "Suppression Key": act.get("suppression_key"),
            "Rationale": act.get("rationale"),
        }
        print_msg(f"Action #{i}: {act.get('template_name')}", act.get("body", ""), meta_info)

    if not actions:
        print("[INFO] No proactive actions taken in this tick.")
        return

    # 4. Multi-Turn Conversation Simulation
    print_banner("4. MULTI-TURN CONVERSATION SCENARIOS")

    # Pick first conversation
    first_cid = actions[0]["conversation_id"]
    target_mid = actions[0]["merchant_id"]

    # Scenario A: Merchant Commits -> Action Mode
    print("▶ Scenario A: Merchant commits ('Ok lets do it. Whats next?')")
    print(f"  Merchant: \"Ok lets do it. Whats next?\"")
    rep_a = client.post("/v1/reply", json={
        "conversation_id": first_cid,
        "merchant_id": target_mid,
        "message": "Ok lets do it. Whats next?",
    }).json()
    print_msg(f"Vera Reply (Action: {rep_a.get('action')}, CTA: {rep_a.get('cta')})", rep_a.get("body", ""), {"Rationale": rep_a.get("rationale")})

    # Scenario B: Off-topic inquiry
    print("▶ Scenario B: Merchant asks off-topic question ('Can you help me file my GST return?')")
    print(f"  Merchant: \"Can you help me file my GST return?\"")
    rep_b = client.post("/v1/reply", json={
        "conversation_id": first_cid,
        "merchant_id": target_mid,
        "message": "Can you help me file my GST return?",
    }).json()
    print_msg(f"Vera Reply (Action: {rep_b.get('action')}, CTA: {rep_b.get('cta')})", rep_b.get("body", ""), {"Rationale": rep_b.get("rationale")})

    # Scenario C: Opt-Out / Stop
    print("▶ Scenario C: Merchant requests opt-out ('Stop messaging me')")
    print(f"  Merchant: \"Stop messaging me\"")
    rep_c = client.post("/v1/reply", json={
        "conversation_id": first_cid,
        "merchant_id": target_mid,
        "message": "Stop messaging me",
    }).json()
    print_msg(f"Vera Reaction (Action: {rep_c.get('action')})", rep_c.get("body", "(Conversation ended cleanly)"), {"Rationale": rep_c.get("rationale")})

    print_banner("SIMULATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    is_interactive = "--interactive" in sys.argv or "-i" in sys.argv
    run_simulation(interactive=is_interactive)
