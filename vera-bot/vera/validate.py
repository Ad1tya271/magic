"""Deterministic checks on outbound WhatsApp bodies.

The number-provenance check is the anti-fabrication backbone: every numeric token in a body
must be traceable to the raw contexts (bundle), the FactSheet, or a small set of safe
derivations (fraction -> percent, roundings, date/time parts, peer gaps, small counts).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from typing import Any, Iterator

CTA_VALUES: tuple[str, ...] = (
    "binary_yes_no",
    "binary_confirm_cancel",
    "multi_choice_slot",
    "open_ended",
    "none",
)
REPLY_ACTIONS: tuple[str, ...] = ("send", "wait", "end")

# judge_simulator.py matches these as plain substrings of the lower-cased body.
QUALIFYING_PHRASES: tuple[str, ...] = ("would you", "do you", "can you tell", "what if", "how about")
ACTION_MARKERS: tuple[str, ...] = ("done", "sending", "draft", "here", "confirm", "proceed", "next")

ERROR = "error"
WARN = "warn"

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------

_SCHEME_URL = r"(?:https?://|www\.)\S+"
# Bare domains are matched case-sensitively in lower case so that a missing space after a
# full stop ("welcome.In the ...") is not mistaken for a domain.
_BARE_DOMAIN = (
    r"\b[a-z0-9][a-z0-9-]+(?:\.[a-z0-9-]+)*"
    r"\.(?:com|in|org|net|io|co|ai|me|ly|gl|app|info|biz|link|xyz|online|site|store|shop)\b"
    r"(?:/\S*)?"
)
_URL_RE = re.compile(rf"(?i:{_SCHEME_URL})|{_BARE_DOMAIN}")

_NUM_CORE = r"\d{1,3}(?:,\d{2,3})*,\d{3}(?:\.\d+)?|\d+(?:\.\d+)?"
_NUM_RE = re.compile(
    r"(?P<cur>₹|\bRs\.?|\bINR)?\s?"
    rf"(?P<num>{_NUM_CORE})"
    r"(?P<suf>\s?(?:%|[kK]\b|lakhs?\b|lacs?\b|crores?\b|cr\b|L\b))?"
)
_TIME_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})")
_AMPM_RE = re.compile(r"(?<![\d.])(\d{1,2})\s*(am|pm)\b", re.IGNORECASE)

# Effort/latency figures ("2-min abstract", "live in 10 min", "90-sec", "24h") are rhetorical,
# not data claims, as long as they stay small.
_DURATION_UNITS = {
    "sec": 90, "secs": 90, "second": 90, "seconds": 90,
    "min": 90, "mins": 90, "minute": 90, "minutes": 90, "minat": 90,
    "h": 48, "hr": 48, "hrs": 48, "hour": 48, "hours": 48, "ghante": 48, "ghanta": 48,
}
_RHETORICAL_RE = re.compile(
    r"(?<![\d.,])(\d{1,2})(?:\s*(?:-|–|to)\s*(\d{1,2}))?\s*-?\s*("
    + "|".join(sorted(_DURATION_UNITS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)
_ALWAYS_OPEN_RE = re.compile(r"(?<![\d.,])24\s*[x/×]\s*7(?!\d)", re.IGNORECASE)

_SNAKE_RE = re.compile(r"\b[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+\b")
_ID_PREFIX_RE = re.compile(r"\b(?:trg_|m_0|c_0|d_20)\w*", re.IGNORECASE)
_TEMPLATE_SLOT_RE = re.compile(r"\{\{\s*\w*\s*\}\}|\{[a-z_]+\}")
_JARGON_WORD_RE = re.compile(
    r"\b(?:suppression|payload|placeholder|json|null|undefined|metric_or_topic)\b", re.IGNORECASE
)

_PREAMBLE_RES = (
    re.compile(r"\bhope (?:you(?:'re| are)|you have been|you've been) (?:doing )?(?:well|good|fine|great)"),
    re.compile(r"\bhope this (?:message|note|finds)"),
    re.compile(r"\bi(?:'m| am) (?:reaching out|writing to|writing this)"),
    re.compile(r"\b(?:just )?wanted to reach out\b"),
    re.compile(r"\btrust (?:you(?:'re| are)) (?:doing )?well\b"),
    re.compile(r"\bgreetings (?:from|of the day)\b"),
)
_REINTRO_RES = (
    re.compile(r"\b(?:i'm|i am|this is|it's) vera\b"),
    re.compile(r"\bvera (?:here|from magicpin|this side)\b"),
    re.compile(r"\bvera se bol rah[ie]\b"),
)
_HYPE_RE = re.compile(
    r"!{2,}|\b(?:amazing deal|don'?t miss|hurry|limited time|act now|unbelievable|mind-?blowing|best deal)\b",
    re.IGNORECASE,
)
_BRAND_RE = re.compile(r"\b(?:vera|magicpin)\b", re.IGNORECASE)
_CTA_TAIL_RE = re.compile(
    r"\?|\b(?:reply|yes|confirm|haan|batao|bataiye|bolo|boliye|let me know|tell us|tell me|chalega|"
    r"shall i|want me|should i|go ahead)\b",
    re.IGNORECASE,
)
_REPLY_WORD_RE = re.compile(r"\breply\b", re.IGNORECASE)
_KEYWORD_OPTION_RE = re.compile(r"\b(YES|NO|STOP|CONFIRM|CANCEL|MAYBE|LATER)\b")

# Roman-script Hindi words that rarely occur in English copy.
HINDI_MARKERS: frozenset[str] = frozenset({
    "hai", "hain", "aap", "aapka", "aapki", "aapke", "apka", "apki", "apke", "aapko", "apko",
    "kya", "karein", "karen", "kariye", "karo", "karna", "karte", "karke", "kar", "ke", "ki", "ka",
    "mein", "se", "ko", "liye", "abhi", "bas", "chahiye", "haan", "nahi", "nahin", "ji", "sirf",
    "wala", "wali", "wale", "raha", "rahi", "rahe", "hoga", "hogi", "honge", "dekhiye", "dekho",
    "bhej", "bhejein", "bhejna", "bhejun", "bhejdu", "chaliye", "theek", "thik", "accha", "acha",
    "achha", "bilkul", "shukriya", "dhanyavaad", "dhanyawad", "namaste", "namaskar", "jaldi",
    "aaj", "kal", "ghante", "hafte", "mahine", "saal", "wapas", "zaroor", "zarur", "lagta",
    "sakte", "sakti", "sakta", "chalega", "yahan", "yeh", "ye", "woh", "wo", "koi", "kuch",
    "sabhi", "humne", "maine", "tak", "bhi", "toh", "lekin", "aur", "ya", "phir", "fir", "diya",
    "kiya", "gaya", "gayi", "hua", "hui", "wahi", "unka", "unke", "apne", "apna", "apni",
    "banaya", "banayi", "taiyaar", "tayyar", "dijiye", "batayein", "bataiye", "chahenge",
})
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_WORD_RE = re.compile(r"[A-Za-z]+")

# Identifier-valued keys: their digits are never legitimate message content.
_ID_KEYS: frozenset[str] = frozenset({
    "id", "merchant_id", "customer_id", "place_id", "suppression_key", "top_item_id",
    "digest_item_id", "alert_id", "item_id", "trigger_id", "template_name", "conversation_id",
    "phone_redacted", "ack_id",
})
_PERCENT_KEY_HINTS = ("pct", "delta", "yoy", "ctr", "rate", "share", "growth", "uplift", "retention", "churn")

_PEER_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("performance", "ctr", "avg_ctr"),
    ("performance", "views", "avg_views_30d"),
    ("performance", "calls", "avg_calls_30d"),
    ("performance", "directions", "avg_directions_30d"),
    ("customer_aggregate", "retention_6mo_pct", "retention_6mo_pct"),
    ("customer_aggregate", "retention_3mo_pct", "retention_3mo_pct"),
    ("customer_aggregate", "repeat_customer_pct", "repeat_customer_pct"),
    ("customer_aggregate", "monthly_churn_pct", "monthly_churn_pct"),
    ("customer_aggregate", "trial_to_paid_pct", "trial_to_paid_pct"),
    ("customer_aggregate", "delivery_share_pct", "delivery_share_pct"),
)

_SEVERITY_RANK = {ERROR: 0, WARN: 1}


# ---------------------------------------------------------------------------
# Sanitising
# ---------------------------------------------------------------------------

def sanitize_body(text: str) -> str:
    """Strip URLs, normalise whitespace, collapse runs of blank lines, trim."""
    if not text:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[​⁠﻿]", "", s)  # keep ZWJ/ZWNJ: emoji sequences and Indic scripts use them
    s = re.sub(r"[\t  -   　]", " ", s)
    s = _URL_RE.sub("", s)
    s = re.sub(r"\(\s*\)|\[\s*\]|<\s*>", "", s)
    s = re.sub(r"[ ]{2,}", " ", s)
    s = re.sub(r" +([,.;:!?])", r"\1", s)
    s = "\n".join(line.strip() for line in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def _ascii_digits(text: str) -> str:
    if text.isascii():
        return text
    return "".join(str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch for ch in text)


def _fmt(value: Decimal) -> str:
    value = abs(value)
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def _normalize_match(m: re.Match[str]) -> str | None:
    d = _to_decimal(m.group("num").replace(",", ""))
    if d is None:
        return None
    suffix = (m.group("suf") or "").strip().lower()
    if suffix == "k":
        d *= 1000
    elif suffix in ("lakh", "lakhs", "lac", "lacs") or (suffix == "l" and m.group("cur")):
        d *= 100000
    elif suffix in ("crore", "crores", "cr"):
        d *= 10000000
    return _fmt(d)


def normalize_number(tok: str | int | float) -> str | None:
    """Canonical numeric token: "2,100"→"2100", "₹1,499"→"1499", "38%"→"38", "2.10"→"2.1".

    Signs are dropped (hyphens are ambiguous in ranges, dates and batch codes); magnitude
    suffixes k / lakh / crore are applied.
    """
    if isinstance(tok, bool):
        return None
    if isinstance(tok, (int, float, Decimal)):
        d = _to_decimal(tok)
        return None if d is None else _fmt(d)
    m = _NUM_RE.search(_ascii_digits(str(tok)))
    return _normalize_match(m) if m else None


def _iter_numbers(text: str) -> Iterator[tuple[str, int, int]]:
    for m in _NUM_RE.finditer(_ascii_digits(text)):
        n = _normalize_match(m)
        if n is not None:
            yield n, m.start("num"), m.end("num")


def extract_numbers(text: str) -> list[str]:
    """Normalized numeric tokens in order of appearance (duplicates kept)."""
    if not text:
        return []
    return [n for n, _, _ in _iter_numbers(str(text))]


def _roundings(d: Decimal) -> set[str]:
    d = abs(d)
    out = {_fmt(d)}
    for q in (Decimal(1), Decimal("0.1")):
        out.add(_fmt(d.quantize(q, rounding=ROUND_FLOOR)))
        out.add(_fmt(d.quantize(q, rounding=ROUND_CEILING)))
    if d >= 1000:
        # 2 and 3 significant figures ("2.4K views" for 2410).
        digits = len(str(int(d)))
        for sig in (2, 3):
            step = Decimal(10) ** (digits - sig)
            for rounding in (ROUND_FLOOR, ROUND_CEILING):
                out.add(_fmt((d / step).quantize(Decimal(1), rounding=rounding) * step))
    return out


def _numeric_variants(value: Any, key: str = "") -> set[str]:
    d = _to_decimal(value)
    if d is None:
        return set()
    out = _roundings(d)
    key_l = key.lower()
    percent_like = (Decimal(0) < abs(d) < 1) or (
        any(h in key_l for h in _PERCENT_KEY_HINTS) and abs(d) <= 10 and d != d.to_integral_value()
    )
    if percent_like:
        pct = d * 100
        variants = _roundings(pct)
        out |= variants
        if d < 0:
            out |= {"-" + v for v in variants}
    return out


def _string_variants(text: str) -> set[str]:
    out: set[str] = set()
    s = _ascii_digits(text)
    for n, _, _ in _iter_numbers(s):
        out |= _roundings(Decimal(n))
    for m in _TIME_RE.finditer(s):
        hour = int(m.group(1))
        if hour <= 24:
            out.add(str(hour % 12 or 12))
    for m in _AMPM_RE.finditer(s):
        hour = int(m.group(1))
        if m.group(2).lower() == "pm" and hour < 12:
            out.add(str(hour + 12))
    return out


def _walk(obj: Any, allowed: set[str], key: str = "") -> None:
    if key in _ID_KEYS:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            ks = str(k)
            allowed |= _string_variants(ks)
            _walk(v, allowed, ks)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            _walk(v, allowed, key)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float, Decimal)):
        allowed |= _numeric_variants(obj, key)
    else:
        allowed |= _string_variants(str(obj))


def _derived_numbers(bundle: dict) -> set[str]:
    """Conservative arithmetic the composer is likely to state: peer gaps, baseline deltas,
    milestone gaps and price gaps between a trigger payload and the merchant's offers."""
    out: set[str] = set()
    merchant = bundle.get("merchant") or {}
    category = bundle.get("category") or {}
    peer = category.get("peer_stats") or {}
    for section, m_key, p_key in _PEER_PAIRS:
        m_val = _to_decimal((merchant.get(section) or {}).get(m_key))
        p_val = _to_decimal(peer.get(p_key))
        if m_val is None or p_val is None or p_val == 0:
            continue
        diff = abs(m_val - p_val)
        out |= _roundings(diff)
        if abs(p_val) < 1:  # fractions: percentage-point gap
            out |= _roundings(diff * 100)
        out |= _roundings(diff / abs(p_val) * 100)
        out |= _roundings(m_val / p_val)
        out |= _roundings(p_val / m_val) if m_val != 0 else set()

    trigger = bundle.get("trigger") or {}
    payload = trigger.get("payload") or {}
    if isinstance(payload, dict):
        base = _to_decimal(payload.get("vs_baseline"))
        delta = _to_decimal(payload.get("delta_pct"))
        if base is not None and delta is not None:
            out |= _roundings(base * (1 + delta))
            out |= _roundings(base * delta)
        now_v = _to_decimal(payload.get("value_now"))
        goal = _to_decimal(payload.get("milestone_value"))
        if now_v is not None and goal is not None:
            out |= _roundings(goal - now_v)

        payload_prices = _rupee_amounts(payload)
        offer_prices = _rupee_amounts([o.get("title", "") for o in merchant.get("offers") or []
                                       if isinstance(o, dict)])
        for a in payload_prices:
            for b in offer_prices:
                out |= _roundings(a - b)
    return out


def _rupee_amounts(obj: Any) -> list[Decimal]:
    amounts: list[Decimal] = []
    if isinstance(obj, dict):
        for v in obj.values():
            amounts += _rupee_amounts(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            amounts += _rupee_amounts(v)
    elif isinstance(obj, str):
        for m in _NUM_RE.finditer(_ascii_digits(obj)):
            if m.group("cur"):
                n = _normalize_match(m)
                if n is not None:
                    amounts.append(Decimal(n))
    return amounts


def allowed_number_set(bundle: dict, facts: dict) -> set[str]:
    """Every normalized numeric token a message may contain for this bundle."""
    bundle = bundle or {}
    facts = facts or {}
    allowed: set[str] = {str(i) for i in range(11)}
    for tok in facts.get("allowed_numbers") or []:
        n = normalize_number(tok)
        if n is not None:
            allowed.add(n)
            allowed |= _roundings(Decimal(n))
    _walk(facts, allowed)
    for key in ("category", "merchant", "trigger", "customer", "now"):
        _walk(bundle.get(key), allowed, key)
    allowed |= _derived_numbers(bundle)
    return allowed


def _rhetorical_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in _RHETORICAL_RE.finditer(text):
        limit = _DURATION_UNITS[m.group(3).lower()]
        values = [int(g) for g in (m.group(1), m.group(2)) if g]
        if all(v <= limit for v in values):
            spans.append((m.start(), m.end()))
    spans += [(m.start(), m.end()) for m in _ALWAYS_OPEN_RE.finditer(text)]
    return spans


def unverified_numbers(body: str, allowed: set[str]) -> list[tuple[str, int]]:
    """(token, position) for numbers in body that are not in `allowed`, first occurrence only."""
    text = _ascii_digits(body)
    spans = _rhetorical_spans(text)
    seen: set[str] = set()
    out: list[tuple[str, int]] = []
    for n, start, end in _iter_numbers(text):
        if n in allowed or n in seen:
            continue
        if any(s <= start and end <= e for s, e in spans):
            continue
        seen.add(n)
        out.append((n, start))
    return out


# ---------------------------------------------------------------------------
# Message checks
# ---------------------------------------------------------------------------

def _issue(code: str, severity: str, detail: str) -> dict:
    return {"code": code, "severity": severity, "detail": detail}


def _snippet(text: str, pos: int, width: int = 28) -> str:
    start = max(0, pos - width)
    end = min(len(text), pos + width)
    frag = text[start:end].replace("\n", " ")
    return ("…" if start > 0 else "") + frag + ("…" if end < len(text) else "")


def _norm_quotes(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def _norm_for_compare(text: str) -> str:
    s = unicodedata.normalize("NFKC", _norm_quotes(text or "")).lower()
    s = re.sub(r"[^\w]+", " ", s)
    return " ".join(s.split())


def taboo_phrases(category: dict | None) -> list[str]:
    """Taboo phrases from category voice; parenthetical usage notes are dropped."""
    voice = (category or {}).get("voice") or {}
    raw = list(voice.get("vocab_taboo") or []) + list(voice.get("taboos") or [])
    out: list[str] = []
    for item in raw:
        phrase = re.split(r"\s*\(", str(item), maxsplit=1)[0].strip()
        if phrase and phrase.lower() not in (p.lower() for p in out):
            out.append(phrase)
    return out


def _taboo_regex(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", phrase) if p]
    return re.compile(r"(?<!\w)" + r"[\s\-]+".join(parts) + r"(?!\w)", re.IGNORECASE)


def has_hindi_markers(text: str, minimum: int = 2) -> bool:
    if _DEVANAGARI_RE.search(text or ""):
        return True
    words = {w.lower() for w in _WORD_RE.findall(text or "")}
    return len(words & HINDI_MARKERS) >= minimum


def _history_has_vera(bundle: dict) -> bool:
    history = ((bundle.get("merchant") or {}).get("conversation_history")) or []
    return any(isinstance(t, dict) and str(t.get("from", "")).lower() == "vera" for t in history)


def validate_message(msg: dict, bundle: dict, facts: dict, *, prior_bodies: list[str] | None = None,
                     mode: str = "compose") -> list[dict]:
    """Issues found in `msg` ({"body","cta","send_as"[,"action","wait_seconds"]}).

    mode: "compose" | "reply" | "reply_action". Errors sort before warnings; within a severity
    the order is the fixed check order below, then order of appearance in the body.
    """
    msg = msg or {}
    bundle = bundle or {}
    facts = facts or {}
    issues: list[dict] = []
    is_reply = mode.startswith("reply")

    action = msg.get("action")
    if is_reply and action is not None and action not in REPLY_ACTIONS:
        issues.append(_issue("bad_action", ERROR, f"action {action!r} not in {list(REPLY_ACTIONS)}"))
    if action in ("wait", "end"):
        if action == "wait":
            ws = msg.get("wait_seconds")
            if isinstance(ws, bool) or not isinstance(ws, int) or ws <= 0:
                issues.append(_issue("bad_wait_seconds", ERROR, f"wait needs positive integer wait_seconds, got {ws!r}"))
        return _ordered(issues)

    body = str(msg.get("body") or "")
    cta = msg.get("cta")
    if cta not in CTA_VALUES:
        issues.append(_issue("bad_cta", ERROR, f"cta {cta!r} not in {list(CTA_VALUES)}"))
    if not body.strip():
        issues.append(_issue("empty_body", ERROR, "body is empty"))
        return _ordered(issues)

    lower = _norm_quotes(body).lower()
    send_as = msg.get("send_as") or facts.get("send_as")
    customer_facing = send_as == "merchant_on_behalf" or facts.get("route") == "customer"

    for m in _URL_RE.finditer(body):
        issues.append(_issue("url", ERROR, f"URL/domain not allowed: {m.group(0)!r}"))

    for phrase in taboo_phrases(bundle.get("category")):
        m = _taboo_regex(phrase).search(body)
        if m:
            issues.append(_issue("taboo", ERROR, f"category taboo phrase {phrase!r}: {_snippet(body, m.start())!r}"))

    allowed = allowed_number_set(bundle, facts)
    for tok, pos in unverified_numbers(body, allowed):
        issues.append(_issue(
            "unverified_number", ERROR,
            f"number {tok} is not in the contexts or verified facts: {_snippet(body, pos)!r}",
        ))

    norm_body = _norm_for_compare(body)
    for prior in prior_bodies or []:
        norm_prior = _norm_for_compare(prior)
        if not norm_prior:
            continue
        if norm_prior == norm_body:
            issues.append(_issue("duplicate", ERROR, f"identical to a previous message: {prior[:80]!r}"))
            break
        ratio = difflib.SequenceMatcher(None, norm_prior, norm_body, autojunk=False).ratio()
        if ratio >= 0.9:
            issues.append(_issue("near_duplicate", WARN, f"{ratio:.2f} similar to a previous message: {prior[:80]!r}"))
            break

    for rx in _PREAMBLE_RES:
        m = rx.search(lower)
        if m:
            issues.append(_issue("preamble", ERROR, f"filler preamble: {m.group(0)!r}"))

    jargon: list[str] = []
    for rx in (_SNAKE_RE, _ID_PREFIX_RE, _TEMPLATE_SLOT_RE, _JARGON_WORD_RE):
        for m in rx.finditer(body):
            if m.group(0) not in jargon:
                jargon.append(m.group(0))
    for tok in jargon:
        issues.append(_issue("jargon", ERROR, f"internal token exposed: {tok!r}"))

    if mode == "reply_action":
        for phrase in QUALIFYING_PHRASES:
            if phrase in lower:
                issues.append(_issue("qualifying_question", ERROR,
                                     f"action-mode reply contains qualifying phrase {phrase!r}"))
        if not any(marker in lower for marker in ACTION_MARKERS):
            issues.append(_issue("missing_action_marker", WARN,
                                 "action-mode reply has none of: " + ", ".join(ACTION_MARKERS)))

    if customer_facing:
        m = _BRAND_RE.search(body)
        if m:
            issues.append(_issue("brand_mention", WARN, f"customer-facing body mentions {m.group(0)!r}"))

    lang_mode = ((facts.get("language") or {}).get("mode")) if not is_reply else None
    if lang_mode in ("hinglish", "hindi") and not has_hindi_markers(body):
        issues.append(_issue("language_mismatch", WARN, f"expected {lang_mode} but found no Hindi words"))

    reply_count = len(_REPLY_WORD_RE.findall(body))
    options = {m.group(1) for m in _KEYWORD_OPTION_RE.finditer(body)}
    questions = body.count("?")
    if reply_count >= 2 or len(options) >= 3 or questions >= 3:
        issues.append(_issue("multiple_ctas", WARN,
                             f"{reply_count} 'reply' asks, {len(options)} keyword options, {questions} questions"))

    if cta in CTA_VALUES and cta != "none" and not _CTA_TAIL_RE.search(body[-160:]):
        issues.append(_issue("cta_not_last", WARN, "the closing lines do not contain the call to action"))

    if not customer_facing and (prior_bodies or _history_has_vera(bundle)):
        for rx in _REINTRO_RES:
            m = rx.search(lower)
            if m:
                issues.append(_issue("reintroduction", WARN, f"re-introduces Vera: {m.group(0)!r}"))
                break

    for m in _HYPE_RE.finditer(body):
        issues.append(_issue("hype", WARN, f"promotional tone: {m.group(0)!r}"))

    if len(body) > 1200:
        issues.append(_issue("too_long", WARN, f"{len(body)} chars"))
    elif not is_reply and len(body) < 60:
        issues.append(_issue("too_short", WARN, f"{len(body)} chars"))

    return _ordered(issues)


def _ordered(issues: list[dict]) -> list[dict]:
    return sorted(issues, key=lambda i: _SEVERITY_RANK.get(i["severity"], 2))


def has_errors(issues: list[dict]) -> bool:
    return any(i.get("severity") == ERROR for i in issues)
