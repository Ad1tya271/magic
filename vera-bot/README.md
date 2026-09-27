# Vera Bot — Proactive Merchant WhatsApp AI

**Vera** is an intelligent, context-grounded conversational agent built for the magicpin AI Challenge. It serves small & medium retail merchants across 5 core categories (**Dentists, Salons, Restaurants, Gyms, and Pharmacies**) in India.

---

## 🌟 Core Architecture & Capabilities

1. **Chat-First Conversational Onboarding**:
   - The user interface operates entirely within the chat window.
   - Automatically initiates the conversation by asking *"Which restaurant or vendor are you associated with?"*
   - Presents clickable vendor suggestion chips (Suresh at SK Pizza Junction, Dr. Meera, Lakshmi, Padma, Ramesh) alongside manual text input.
   - Validates vendor identities and loads real business metrics, locations, and active offers without exposing internal system prompts or raw configurations.
   - Provides relevant opening suggestions derived from the vendor's actual data.
   - Supports mid-conversation vendor switching (`⇄ Switch Vendor` or typing `"switch vendor"`).

2. **Conversational State Machine**:
   - Manages state progression: `SELECTING_VENDOR` ➔ `VENDOR_SELECTED` ➔ `CONVERSING`.
   - Isolates conversation histories across different vendors to prevent data leakage.
   - Supports session teardown and restart via `↺ Reset Session`.

3. **Multi-Turn Dialog & Safeguards**:
   - Recognizes and answers custom/unknown options (`Option 3`, `Option 4`, `Option C`, custom alternatives) constructively by evaluating category margins and proposing WhatsApp pilot drafts.
   - Strict action-mode intent transitions upon merchant agreement (zero qualifying questions).
   - Multi-tier automated reply detection (turn 1 context, turn 2 pause for 24h, turn 3 clean shutdown).
   - Immediate graceful de-escalation on hostile language.

---

## 🚀 Running Locally

```powershell
# 1. Start the API Server & Interactive UI
.\.venv\Scripts\uvicorn.exe bot:app --host 0.0.0.0 --port 8000

# 2. Run automated test suite
.\.venv\Scripts\pytest.exe tests/ -v

# 3. Run the Challenge Judge Simulator
powershell -ExecutionPolicy Bypass -File ..\run_judge.ps1 all

# 4. Run the Rubric Evaluator
.\.venv\Scripts\python.exe scripts/score_eval.py
```

---

## 📡 REST API Surface

- `GET /` — Interactive web dashboard (Chat-first, Violet & Crème)
- `GET /v1/merchants` — Available merchant profiles and contextual suggestion chips
- `POST /v1/reply` — Conversational turns, vendor selection, and dialogue
- `POST /v1/tick` — Trigger evaluation and proactive message composition
- `POST /v1/context` — Ingest category, merchant, customer, or trigger data
- `POST /v1/teardown` — Clear in-memory conversation state
- `GET /v1/healthz` — Liveness and context counters
- `GET /v1/metadata` — Team and model information
