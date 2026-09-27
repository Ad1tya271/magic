# Vera Bot — Build Spec (shared contract for all modules)

Source of truth for the challenge: `C:\abc\magicpin-ai-challenge\` —
`challenge-brief.md` (what to build, rubric), `challenge-testing-brief.md` (HTTP contract),
`examples\api-call-examples.md` (exact request/response shapes), `examples\case-studies.md`
(what "good" looks like — never copy their body text verbatim; the judge runs a plagiarism check),
`judge_simulator.py` (local judge), `dataset\` (categories/*.json, merchants_seed.json,
customers_seed.json, triggers_seed.json, generate_dataset.py).

Project root: `C:\abc\vera-bot\`. Python venv: `C:\abc\vera-bot\.venv\Scripts\python.exe`
(Python 3.14, anthropic 1.8.0, fastapi, uvicorn, pydantic 2, httpx, pytest installed).
Windows: always open files with `encoding="utf-8"`; run Python with `-X utf8` when running
third-party scripts from the challenge folder (they omit encodings and the data contains ₹, —).

## Hard facts that shape the design (verified)

- LLM: Anthropic `claude-opus-4-7` (default; env `VERA_MODEL`). Opus 4.7 **rejects**
  `temperature`/`top_p`/`top_k` (400) and assistant prefill (400). Omitting `thinking` = no
  thinking (fast). `output_config={"effort": "...", "format": {"type": "json_schema", "schema": {...}}}`
  is the structured-output mechanism (schemas need `additionalProperties: false` + `required`).
  Determinism therefore comes from **memoizing** LLM results by a hash of the exact request.
- No `ANTHROPIC_API_KEY` is present in this dev environment. Everything must work with the LLM
  disabled: a deterministic fallback composer is a first-class path, not an afterthought.
- Judge timeouts: testing brief says 30 s; api-call-examples says tick/reply budget 10 s;
  `judge_simulator.py` uses 15 s for tick/reply, 10 s for context, 5 s for healthz. Design for
  **tick ≤ 9 s, reply ≤ 8 s** wall-clock, always.
- `judge_simulator.py` sends `now = datetime.utcnow()` (real clock, e.g. 2026-09-27) while the
  dataset lives around 2026-04-26. Treat `available_triggers` as the judge's truth about what is
  active. Do NOT drop triggers because `expires_at < now` unless `VERA_STRICT_EXPIRY=1`.
  Never print negative/implausible durations computed from a mismatched clock.
- `judge_simulator.py` auto-reply test sends the same canned text 4 times with a **different
  conversation_id each time** (`conv_auto_1..4`) for the same merchant → auto-reply counting
  must be per **merchant**, not only per conversation.
- Simulator intent check: after "Ok lets do it. Whats next?" the body must contain one of
  `done|sending|draft|here|confirm|proceed|next` and must NOT contain
  `would you|do you|can you tell|what if|how about`. Simulator hostile check: `end` passes.
- Simulator never pushes customer contexts; customer-scoped triggers may arrive with no
  CustomerContext stored.
- 75 of 100 generated triggers have placeholder payloads `{"placeholder": true,
  "metric_or_topic": kind}` and 40 generated merchants are sparse (no offers/history/signals,
  `customer_aggregate` only `total_unique_ytd`). Generated customers have
  `preferences.reminder_opt_in` false ~20% of the time and `consent.scope` = ["promotional_offers"].
- URLs in body = hard fail (-3). Same body twice in a conversation = -2. Missing required action
  fields = -2. Fabrication = heavy penalty. Exposing internal jargon (e.g. `ctr_below_peer_median`,
  snake_case ids) = -1.

## Layout and ownership

```
vera-bot/
  bot.py                      [A] FastAPI app (5 endpoints + /v1/teardown) + compose() entrypoint
  conversation_handlers.py    [D] reply classification + policy; respond() / respond_async()
  vera/__init__.py            [A]
  vera/config.py              [A] Settings from env
  vera/store.py               [A] ContextStore, ConversationStore, MerchantMemory
  vera/llm.py                 [A] LLMClient (AsyncAnthropic wrapper, memo cache, deadlines)
  vera/composer.py            [A] compose_message(): facts → LLM (validate/repair) → fallback
  vera/planner.py             [A] tick candidate selection / suppression / prioritisation
  vera/facts.py               [B] resolve_digest_item(), derive_facts() → FactSheet
  vera/language.py            [B] language resolution + per-message detection
  vera/fallback.py            [B] deterministic per-trigger-kind composer
  vera/prompts.py             [C] system prompts, per-kind playbooks, prompt builders, JSON schemas
  vera/validate.py            [C] validators + sanitizer + number-provenance check
  tests/                      each owner writes tests for their modules (test_<module>.py)
  scripts/                    [E] generate_submission.py, run_judge.py, local_harness.py
```
Only edit files you own. If you need something from another module that does not exist yet,
code against the interface below; write unit tests with small local stubs.

## Shared data shapes

**Bundle** (plain dict): `{"category": dict, "merchant": dict, "trigger": dict,
"customer": dict | None, "now": str | None}` — the raw context payloads as pushed/loaded.

**CTA enum** (string): `"binary_yes_no" | "binary_confirm_cancel" | "multi_choice_slot" |
"open_ended" | "none"`.

**ComposedMessage** (dict) — returned by composer/fallback:
```
{
  "body": str,                  # WhatsApp text, non-empty, no URLs
  "cta": <CTA enum>,
  "send_as": "vera" | "merchant_on_behalf",
  "suppression_key": str,       # trigger["suppression_key"] if present else f"{kind}:{merchant_id}:{customer_id or '-'}"
  "rationale": str,             # 1–3 sentences: why this message, which facts/levers, what it should achieve
  "template_name": str,         # e.g. "vera_research_digest_v1" / "merchant_recall_due_v1"
  "template_params": [str],     # 2–5 params that, filled into the template, reproduce the body
  "_meta": {"composer": "llm" | "fallback", "route": str, "issues": [...], ...}  # internal only; strip before HTTP/JSONL output
}
```

**FactSheet** (dict) — produced by `vera.facts.derive_facts(bundle)` [B], consumed by prompts [C],
validate [C], fallback [B], composer [A], conversation handlers [D]:
```
{
  "kind": str, "scope": "merchant" | "customer",
  "route": "merchant" | "customer" | "merchant_approval",
      # merchant_approval = customer-scoped trigger but CustomerContext missing, or customer has
      # not consented (reminder_opt_in false / empty consent scope) → message goes to the MERCHANT
      # (send_as "vera") asking approval / flagging, never directly to the customer.
  "route_reason": str | None,
  "send_as": "vera" | "merchant_on_behalf",
  "merchant_id": str, "customer_id": str | None,
  "business_name": str, "owner_first_name": str | None,
  "salutation": str,            # how to address the merchant: "Dr. Meera" (dentists), "Lakshmi", else business name
  "customer_name": str | None,  # clean display name ("Priya"; "Sharma ji"; for "Karthik (parent: Sumitra)" → address parent "Sumitra", child "Karthik")
  "customer_salutation": str | None,
  "locality": str | None, "city": str | None,
  "language": {"mode": "hinglish" | "english" | "hindi" | "regional_mix",
               "regional": "te" | "ta" | "kn" | "mr" | None,
               "label": str},   # human-readable instruction, e.g. "Hindi-English code-mix in Roman script"
  "digest_item": dict | None,   # resolved from category.digest via trigger payload ids, else best match, else None
  "active_offers": [str], "catalog_offers": [str],
  "facts": {id: str},           # verified, human-readable fact fragments, ordered most-relevant-first,
                                # numbers formatted exactly as they may appear in copy ("2.1%", "₹299", "2,100")
  "values": {id: any},          # raw numbers behind the facts (for templates/validation)
  "allowed_numbers": [str],     # normalized numeric tokens that appear in facts/contexts (see validate.normalize_number)
  "placeholder_trigger": bool,  # trigger payload is a generator placeholder → lean on merchant/category data
  "blocked": str | None,        # reason to not message anyone at all (e.g. merchant opted out) — rare
  "suppression_key": str, "template_name": str
}
```

## Module interfaces

### [A] vera/config.py
`settings = Settings.from_env()` with: `model` (VERA_MODEL, "claude-opus-4-7"), `effort`
(VERA_EFFORT, "medium"), `llm_enabled` (true iff ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN set
and VERA_DISABLE_LLM != "1"), `tick_budget_s` (9.0), `reply_budget_s` (8.0), `compose_budget_s`
(25.0), `max_tokens` (1500), `strict_expiry` (False), `default_now` ("2026-04-26T10:00:00Z"),
`max_actions_per_tick` (20), `team_name`, `team_members`, `contact_email`, `version`,
`submitted_at`, `approach`, `prompt_version` ("composer_v1").

### [A] vera/llm.py
```
class LLMClient:
    enabled: bool
    async def complete_json(self, *, system, messages, schema: dict, max_tokens: int,
                            timeout_s: float, cache_key: str | None = None) -> dict | None
```
Returns parsed JSON dict or None (disabled / timeout / refusal / parse failure / API error).
Never raises. Memoizes successful results in-memory by cache_key (default: sha256 of
model+system+messages+schema). Uses `AsyncAnthropic(max_retries=0)`, `asyncio.wait_for` hard
deadline, `output_config={"effort": settings.effort, "format": {"type":"json_schema","schema":schema}}`,
`cache_control={"type":"ephemeral"}` on the system block. No temperature, no prefill, no thinking.
On a 400 mentioning output_config/format, retry once without `format` and extract the first JSON
object from text. Check `stop_reason` ("refusal"/"max_tokens" → None). `get_llm()` returns a
process singleton; `set_llm(obj)` lets tests inject a fake with the same `complete_json` signature.

### [A] vera/composer.py
```
async def compose_message(bundle: dict, *, llm, budget_s: float,
                          prior_bodies: list[str] | None = None) -> dict   # ComposedMessage or {"skip": True, "reason": str}
```
Flow: `facts = derive_facts(bundle)`; if `facts["blocked"]` → skip. If `llm.enabled` and budget
allows: `system, messages = build_compose_messages(bundle, facts, prior_bodies)` →
`complete_json(schema=COMPOSE_SCHEMA)` → assemble ComposedMessage (code decides `send_as`,
`suppression_key`, `template_name` from facts; LLM decides body/cta/template_params/rationale) →
`sanitize_body` → `validate_message(..., mode="compose")`; on `error` issues and remaining budget,
one repair round (pass issue details as `repair_notes`); if still errors or no LLM →
`compose_fallback(bundle, facts)` then sanitize + validate (fallback must pass validation by
construction). Never raises; always returns within budget.
Also: `precompute(bundle)` hook for background composition when a trigger arrives.

### [A] vera/planner.py
`select_candidates(store, available_trigger_ids, now) -> list[bundle-with-ids]`: skip unknown
triggers/merchants/categories, suppression keys already sent, merchants who opted out, triggers
already turned into a conversation; sort by urgency desc then expires_at asc; at most **one
merchant-facing message per merchant per tick** (customer-facing: one per customer); cap 20.

### [B] vera/facts.py
```
def resolve_digest_item(category: dict, trigger: dict) -> dict | None
def derive_facts(bundle: dict) -> dict   # FactSheet
```
Digest resolution: look in trigger.payload for `top_item_id`, `digest_item_id`, `alert_id`,
`item_id`; also inline `top_item` dict. Fall back to kind mapping (research_digest→research,
regulation_change→compliance, cde_opportunity→cde, supply_alert→alert/recall/compliance,
category_trend_movement→trend) choosing the first matching digest item; else None.
Facts must cover (when data exists): trigger-specific payload facts (formatted), digest item
(title, source, trial_n, segment, summary numbers, deadline, actionable), merchant performance
(views/calls/ctr/leads, 7d deltas as signed %), peer comparison (merchant ctr vs peer avg_ctr,
views/calls vs peer averages), subscription (days remaining/expired), active offers, relevant
catalog offers, customer_aggregate numbers, review themes (theme + count + quote), conversation
history summary (last Vera ask + whether merchant replied; last merchant message), relevant
seasonal beat for the trigger period, relevant trend signal, customer relationship (last visit
date, visits, services, state, preferred slots, language), slots from payload. For placeholder
triggers derive the "why now" from merchant data (e.g. perf_dip → most negative 7d delta).
Durations: prefer payload-provided counts (days_until, days_to_wedding, days_since_expiry…);
compute from dates only if non-negative and plausible; never emit negative durations.
Never invent a number. Percentages from fractions: 0.021 → "2.1%", -0.5 → "-50%" (or "down 50%").

### [B] vera/language.py
```
def resolve_merchant_language(merchant: dict) -> dict   # FactSheet["language"] shape
def resolve_customer_language(customer: dict) -> dict
def detect_message_language(text: str) -> str           # "hinglish" | "hindi" | "english"
```
Merchant languages containing "hi" → "hinglish" (natural Roman-script Hindi-English code-mix,
English for numbers/technical terms). Customer `language_pref`: "hi-en mix"→hinglish, "hi"→hindi
(Roman-script, respectful, simple), "english"/"en"→english, "te-en mix"/"ta-en mix"/"kn-en mix"
→ regional_mix (English body + one warm greeting word in that language, Roman script).

### [B] vera/fallback.py
```
def compose_fallback(bundle: dict, facts: dict) -> dict   # ComposedMessage with _meta.composer="fallback"
```
Deterministic (no randomness, no clock), high quality, per-kind templates for every kind in
triggers_seed.json and generate_dataset.py (research_digest, regulation_change, recall_due,
perf_dip, perf_spike, renewal_due, festival_upcoming, wedding_package_followup, curious_ask_due,
winback_eligible, ipl_match_today, review_theme_emerged, milestone_reached,
active_planning_intent, seasonal_perf_dip, customer_lapsed_hard, customer_lapsed_soft,
trial_followup, supply_alert, chronic_refill_due, category_seasonal, gbp_unverified,
cde_opportunity, competitor_opened, dormant_with_vera, appointment_tomorrow) + the brief's other
named kinds (weather_heatwave, local_news_event, category_trend_movement, scheduled_recurring,
customer_lapsed_soft) + a robust generic template for unknown kinds + a merchant_approval route
template. Must honour language mode, voice/taboos, route, and use only facts. Body ends with the
single CTA sentence. Must pass `validate_message` with zero `error` issues for every trigger in
the dataset (seed + generated).

### [C] vera/prompts.py
```
PROMPT_VERSION: str
COMPOSE_SCHEMA: dict   # {body, cta(enum), template_params[str], rationale, facts_used[str]} all required, additionalProperties false
REPLY_SCHEMA: dict     # {action(enum send|wait|end), body, cta(enum), wait_seconds(int), rationale}
SYSTEM_PROMPT_COMPOSE: str   # stable, no per-request data (cacheable)
SYSTEM_PROMPT_REPLY: str
KIND_PLAYBOOK: dict[str, str]   # per trigger kind: what "why now" + best levers + CTA shape
def build_compose_messages(bundle, facts, prior_bodies=None, repair_notes=None) -> tuple[list, list]
def build_reply_messages(bundle, facts, conversation: list[dict], merchant_message: str,
                         mode: str, notes: list[str] | None = None) -> tuple[list, list]
```
`system` is a list of text blocks (`[{"type":"text","text":...,"cache_control":{"type":"ephemeral"}}]`).
User message = compact JSON of relevant context (category: voice, offer_catalog, peer_stats,
resolved digest item + titles of others, seasonal_beats, trend_signals; full merchant; trigger;
customer) + the FactSheet facts + route instructions + prior bodies (avoid repeats) + repair notes.
Keep total prompt well under 100 KB.

### [C] vera/validate.py
```
def sanitize_body(text: str) -> str          # strip URLs, trim, collapse >2 blank lines, normalise spaces
def normalize_number(tok: str) -> str | None # "2,100"→"2100", "₹1,499"→"1499", "38%"→"38", "2.10"→"2.1"
def extract_numbers(text: str) -> list[str]  # normalized numeric tokens in text
def allowed_number_set(bundle: dict, facts: dict) -> set[str]   # from raw contexts + facts (+ x100 for fractions, abs values, date parts, small ints 0–10)
def validate_message(msg: dict, bundle: dict, facts: dict, *, prior_bodies=None,
                     mode: str = "compose") -> list[dict]   # issues: {"code","severity":"error"|"warn","detail"}
```
Checks (error unless noted): empty body; URL; taboo word from category voice.vocab_taboo
(case-insensitive, word-boundary); unverifiable number; cta not in enum; duplicate of a prior
body (normalised); long preamble ("hope you're doing well", "I am reaching out", "I'm writing to");
internal jargon leak (snake_case tokens with `_`, ids like `trg_`, `m_0`, `c_0`, "suppression");
mode "reply_action": contains `would you|do you|can you tell|what if|how about`; customer-facing
body mentioning "Vera"/"magicpin" (warn); hinglish expected but no Hindi markers (warn);
multiple CTAs (warn).

### [D] conversation_handlers.py
```
@dataclass class ConversationState: conversation_id, merchant_id, customer_id, trigger_id,
    send_as, turns: list[dict] ({"from","body","ts"}), status ("active"|"waiting"|"ended"),
    mode ("pitch"|"action"), auto_reply_count, unanswered_nudges, last_language, topic
def classify_message(text: str, state: ConversationState | None = None,
                     merchant_memory: dict | None = None) -> dict
    # {"label": "auto_reply"|"opt_out"|"hostile"|"commit"|"decline_soft"|"later"|"off_topic"
    #           |"question"|"engaged"|"unclear", "lang": str, "signals": [str]}
def respond(state: ConversationState, merchant_message: str) -> dict   # brief §7.4, sync, rule-based
async def respond_async(state, merchant_message, *, bundle: dict | None, facts: dict | None,
                        llm, budget_s: float, merchant_memory: dict) -> dict
    # returns {"action":"send","body","cta","rationale"} | {"action":"wait","wait_seconds","rationale"}
    #       | {"action":"end","rationale"}; mutates state + merchant_memory; never raises
```
Policy: auto-reply (canned phrases or same text repeated, counted per merchant across
conversations): 1st → one short send flagging it for the owner (single YES-style CTA),
2nd → wait 86400, 3rd+ → end. Explicit opt-out ("stop", "unsubscribe", "not interested",
"don't message", "band karo", "mat bhejo", "nahi chahiye") → end + mark merchant opted out.
Hostile/abusive without explicit opt-out → short apology + one-line opt-out path (cta "none")
and mark conversation closing; a genuine question after that is answered politely.
Commit ("yes", "ok let's do it", "go ahead", "haan", "karo", "confirm", "join") → switch to
action mode: state concretely what is being done now + one CONFIRM-style CTA; never ask a
qualifying question. Later/busy → wait (use stated time if given, else 3600–14400).
Off-topic (GST, tax, loan, legal, personal) → polite one-line decline + redirect to the thread's
topic. Question/engaged → answer from facts (LLM if available within budget, else rule-based).
Never repeat a previous bot body verbatim; after 5 bot turns or 3 unanswered nudges → end.
Reply language follows the merchant's latest message language (detect per turn).

---

## Phase 2 additions (after the base build)

### P2.1 Retrieval layer (RAG) — `vera/retrieval.py`
Why: 75/100 triggers are placeholders, 40/50 merchants are sparse, and the judge injects new
digest items / perf snapshots mid-test and rewards bots that use them. Retrieval decides which
context items are the most relevant evidence for *this* trigger + merchant (+ customer).

- Local, deterministic, dependency-free BM25 (k1=1.5, b=0.75). No embedding APIs (privacy rule
  §11 of the testing brief: no non-LLM external calls with merchant data; also latency).
- Documents built from a bundle: every category digest item, patient_content_library item,
  seasonal beat, trend signal, offer_catalog item, peer_stats (one doc); merchant offers, review
  themes, conversation turns, humanised signals, performance, customer_aggregate; customer
  relationship/preferences. Each doc: `{"id","type","text","source_obj","numbers"}`.
- Query = trigger kind expansion (per-kind keyword map, e.g. perf_dip → calls views dip decline
  ctr post offer visibility; recall_due → recall checkup cleaning visit slot reminder;
  competitor_opened → competitor new nearby price offer; supply_alert → recall batch molecule
  alert compliance …) + string values of trigger.payload + merchant signals (humanised) +
  customer services/state + category slug synonyms.
- Structured boosts (deterministic): digest item explicitly referenced by the trigger (+large);
  seasonal beat whose month_range covers the reference month; **novel items** (digest ids that
  arrived in the latest category version — `bundle["novel_digest_ids"]`) get a boost so injected
  context surfaces; doc type priors per kind.
- Tokeniser: lowercase, split on non-alphanumerics, EN + Hinglish stopwords, light suffix
  stemming (s/es/ing/ed), small synonym map (teeth↔dental, haircut↔hair, gym↔fitness, …).
- API:
  ```
  def build_docs(bundle: dict) -> list[dict]
  def retrieve(bundle: dict, *, k: int = 6, extra_query: str | None = None) -> list[dict]
      # [{"id","type","text","score"}], sorted score desc then id; stable
  def answer_snippets(bundle: dict, question: str, *, k: int = 3) -> list[dict]
  ```
  Index cached by a hash of the bundle's context ids+versions (or canonical JSON).
- Integration: `derive_facts` adds `facts["retrieved"]` (top-k docs, text) and uses retrieval
  as the digest-resolution fallback and for placeholder-trigger "why now" enrichment;
  `build_compose_messages` / `build_reply_messages` add a "RETRIEVED KNOWLEDGE (ranked)" section;
  `compose_fallback` may use top retrieved seasonal beat / trend / digest / review theme when the
  trigger payload is thin; `conversation_handlers` answers questions from `answer_snippets`.

### P2.2 Adaptive context (store)
`ContextStore` keeps, per context, the previous payload when a higher version replaces it.
Bundles gain `"previous_merchant": dict | None` and `"novel_digest_ids": [str]` (digest ids in
the current category version that were not in the previous version). `derive_facts` emits change
facts ("views 2,410 → 2,580 since last snapshot") when previous performance differs.

### P2.3 Pluggable LLM provider — Anthropic or Gemini
`VERA_LLM_PROVIDER` = `auto` (default) | `anthropic` | `gemini`. auto → anthropic if
ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN set, else gemini if GEMINI_API_KEY or GOOGLE_API_KEY set,
else disabled. `VERA_MODEL` overrides; defaults: anthropic `claude-opus-4-7`, gemini
`gemini-flash-latest`. `/v1/metadata.model` reports the active model. Same `complete_json`
interface, memo cache, deadlines, never raises.

**Live benchmark with the user's key (compose-style prompt, responseJsonSchema, temperature 0):**
| model | result | latency |
|---|---|---|
| gemini-flash-latest + thinkingLevel "low" | JSON ok, used all facts | **4.1 s** |
| gemini-flash-latest + thinkingBudget 0 | JSON ok | 4.9 s |
| gemini-flash-latest (default thinking, ~1000 thought tokens) | JSON ok | 6.2 s |
| gemini-3.1-flash-lite | JSON ok, drops facts (less specific) | 2.4 s |
| gemini-3-flash-preview / gemini-3.6-flash | JSON ok | 11–12 s |
| gemini-3.8-flash | JSON ok | 35 s (overloaded) |
| gemini-3.7-flash, gemini-3.5-flash | 503 "high demand" (frequent) | — |
| gemini-3.1-pro-preview | 429 quota exceeded (free tier) | — |
| gemini-2.5-flash | 404 not available to new users | — |
thinkingLevel "minimal" → 400 on gemini-flash-latest. `responseJsonSchema` with
`additionalProperties: false` + enums works. Even urllib sometimes gets
`RemoteDisconnected` → treat connection errors like 503 (retry/next model).
**Gemini client policy:** primary `gemini-flash-latest` with `thinkingConfig.thinkingLevel="low"`;
on 503/429/connection error/timeout move down a fallback chain (env
`VERA_GEMINI_FALLBACK_MODELS`, default `gemini-3.1-flash-lite`) while budget remains; never exceed
the caller's deadline; any failure → None (caller uses the deterministic composer). Free-tier
rate limits are tight: limit concurrent Gemini calls (semaphore, default 4) and memoize.
Judge runs (`scripts/run_judge.py`, provider gemini): use a different model from the bot's
primary when possible to split per-model quota (default judge model `gemini-3-flash-preview`),
and patch the simulator's GeminiProvider at runtime to send `x-goog-api-key`, thinkingLevel
"low", maxOutputTokens 4096 and retry 503/connection errors (its default 1500 tokens can be eaten
by thinking) — config only, never its scoring prompt.
Gemini facts verified in this environment (key is an AI Studio key):
- Endpoint `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  with header `x-goog-api-key: <key>` (or `?key=`). Response text =
  concatenation of `candidates[0].content.parts[*].text` excluding parts with `"thought": true`;
  `finishReason` other than STOP/MAX_TOKENS-with-valid-JSON → treat as failure.
- **Use stdlib `urllib.request` (via `asyncio.to_thread`) for Gemini — `httpx` connections to
  googleapis fail in this environment ("Server disconnected without sending a response") while
  urllib works.**
- `gemini-2.5-flash` returns 404 for this key ("no longer available to new users"). Listed and
  usable: gemini-3.8-flash (Google's recommended), gemini-3.5-flash, gemini-flash-latest,
  gemini-3.1-pro-preview, gemini-pro-latest.
- generationConfig: `temperature: 0` (supported → determinism, plus the memo cache),
  `responseMimeType: "application/json"`, `responseJsonSchema: <schema>`,
  `maxOutputTokens`, optional `thinkingConfig: {"thinkingLevel": "low"}` (env
  VERA_GEMINI_THINKING, default "low"). These fields are not yet verified live: on an HTTP 400,
  retry once dropping `thinkingConfig`, then once more replacing `responseJsonSchema` with plain
  JSON mime + schema described in the prompt; parse the first JSON object from text.
- System prompt → `systemInstruction: {"parts": [{"text": ...}]}`; user turns →
  `contents: [{"role": "user", "parts": [{"text": ...}]}]` (convert Anthropic-style blocks).
- `judge_simulator.py`'s GeminiProvider defaults to the retired `gemini-1.5-flash` and caps
  `maxOutputTokens` at 1500 → `scripts/run_judge.py` must default LLM_MODEL to gemini-3.8-flash
  for provider gemini.
