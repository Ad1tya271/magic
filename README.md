# Magicpin AI Challenge — Vera Bot

A proactive WhatsApp bot designed to drive merchant and customer engagement across Indian local commerce categories (dentists, salons, restaurants, gyms, pharmacies).

Vera combines a 4-context architecture (Category, Merchant, Customer, Trigger), local BM25 context retrieval, verified number-provenance validation, high-specificity per-trigger-kind deterministic composition, and a multi-turn conversation state machine with automatic intent transitions and auto-reply suppression.

---

## Repository Structure

```
├── magicpin-ai-challenge/     # Challenge specifications, datasets, and judge simulator
│   ├── dataset/               # Base categories, merchants, customers, triggers
│   ├── challenge-brief.md     # Rules, constraints, and scoring rubric
│   ├── judge_simulator.py     # Local judge harness
│   └── examples/              # Case studies and API call contracts
├── vera-bot/                  # Vera Bot implementation
│   ├── bot.py                 # FastAPI application (5 endpoints + teardown)
│   ├── conversation_handlers.py # Multi-turn dialog policy & intent transitions
│   ├── SPEC.md                # System specification & architecture contract
│   ├── submission.jsonl       # Generated 30 canonical evaluation pairs
│   ├── vera/                  # Core modules
│   │   ├── facts.py           # FactSheet extraction & number-provenance indexing
│   │   ├── fallback.py        # Deterministic per-kind WhatsApp composer
│   │   ├── retrieval.py       # Local BM25 ranking & evidence retrieval
│   │   ├── validate.py        # Anti-fabrication, URL, taboo, and syntax validator
│   │   ├── prompts.py         # 30-kind playbook, schemas, and system prompts
│   │   ├── planner.py         # Candidate selection & suppression logic
│   │   ├── composer.py        # Top-level composition coordinator
│   │   ├── store.py           # Context and conversation in-memory store
│   │   └── config.py          # Configuration settings
│   ├── tests/                 # Automated test suite (15/15 passing)
│   └── scripts/               # Submission generator, judge runner, and local harness
├── run_bot.ps1 / .bat         # Launcher for API server on port 8000
├── run_judge.ps1 / .bat       # Launcher for official Judge Simulator
└── run_harness.ps1 / .bat     # Launcher for end-to-end local simulation
```

---

## Quick Start

### 1. Run the Bot Server
```powershell
.\run_bot.ps1
# or: cd vera-bot; .venv\Scripts\uvicorn.exe bot:app --host 0.0.0.0 --port 8000
```
Server runs on `http://127.0.0.1:8000`.

### 2. Run the Official Judge Simulator
```powershell
.\run_judge.ps1 all
```

### 3. Run the End-to-End Simulation Harness
```powershell
.\run_harness.ps1
```

### 4. Run Automated Test Suite
```powershell
cd vera-bot
.\.venv\Scripts\pytest.exe tests/ -v
```

### 5. Generate Submission Artifact (`submission.jsonl`)
```powershell
cd vera-bot
.\.venv\Scripts\python.exe scripts/generate_submission.py
```
