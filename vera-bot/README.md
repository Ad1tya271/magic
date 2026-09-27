# Vera Bot

Vera builds each message from category, merchant, trigger, and optional customer context. It resolves a compact evidence sheet, retrieves relevant supplied context with local BM25, and uses a deterministic per-trigger composer when no language model is configured. When Anthropic credentials are available, the model drafts structured JSON and the validator checks provenance, taboo wording, URLs, repetition, and action-mode replies before accepting it.

Run the API with `uvicorn bot:app --host 0.0.0.0 --port 8000`. Generate the canonical 30-pair artifact with `python scripts/generate_submission.py`. The service exposes context, tick, reply, health, metadata, and teardown endpoints.

The main tradeoff is conservative copy: without a model, messages prioritize concrete context and a single low-pressure next step over elaborate personalization. Useful additional context would include up-to-date merchant availability and explicit action permissions, so replies can state exactly what the system can complete.
