"""Language resolution for merchants/customers and per-message language detection.

Modes (FactSheet["language"]["mode"]):
  "hinglish"     natural Hindi-English code-mix in Roman script
  "hindi"        simple, respectful Hindi in Roman script (customers with language_pref "hi")
  "english"      plain English
  "regional_mix" English body + one warm greeting word in the regional language (Roman script)
"""

from __future__ import annotations

import re
from typing import Any

REGIONAL_GREETINGS: dict[str, str] = {
    "te": "Namaskaram",
    "ta": "Vanakkam",
    "kn": "Namaskara",
    "mr": "Namaskar",
}

_REGIONAL_NAMES: dict[str, str] = {
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "mr": "Marathi",
}

_REGIONAL_ALIASES: dict[str, str] = {
    "te": "te", "telugu": "te",
    "ta": "ta", "tamil": "ta",
    "kn": "kn", "kannada": "kn",
    "mr": "mr", "marathi": "mr",
}

LABELS: dict[str, str] = {
    "hinglish": "Hindi-English code-mix in Roman script (English for numbers, prices and technical terms)",
    "hindi": "Simple, respectful Hindi in Roman script (no Devanagari)",
    "english": "English",
}

# Unambiguous Roman-script Hindi words.
_STRONG_MARKERS = frozenset("""
hai hain nahi nahin nai kya karo karein kariye karna karenge karunga karungi kijiye chahiye chaiye
aap aapka aapke aapki aapko apka apke apki mujhe mujhko ji haan haanji theek thik bhej bhejo bhejiye
bhejna kal abhi acha accha achha achchha chalega chalegi batao bataiye bataye kaise kyun kyon kab
kitna kitne kitni kaun kahan mera meri mere humein hamara hamari tumhara yeh woh bhai arre shukriya
dhanyavad dhanyawad namaste namaskar bilkul zaroor jaldi thoda bahut kuch lekin magar matlab wala
wali raha rahi rahe gaya gayi hoga hogi sakte sakta sakti dijiye lijiye samjha samjhi pehle baad
waise toh bolo boliye suniye dekho dekhiye aur abhi hum sabhi rakho rakhiye ruko rukiye mat band
""".split()) - {"hum", "mat", "band"}

# Words that are Hindi in context but also plausible in English text; they count half.
_WEAK_MARKERS = frozenset("""
main ho ka ki ke se par sab kar hum mat band han
""".split())

_WORD_RE = re.compile(r"[a-z]+")
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def _label_for(mode: str, regional: str | None) -> str:
    if mode == "regional_mix" and regional:
        greeting = REGIONAL_GREETINGS.get(regional, "")
        name = _REGIONAL_NAMES.get(regional, regional)
        return f"English with one warm {name} greeting word ({greeting}) in Roman script"
    return LABELS.get(mode, LABELS["english"])


def _result(mode: str, regional: str | None = None) -> dict:
    return {"mode": mode, "regional": regional if mode == "regional_mix" else None,
            "label": _label_for(mode, regional)}


def _normalize_codes(raw: Any) -> list[str]:
    if isinstance(raw, str):
        raw = re.split(r"[,/;\s]+", raw)
    if not isinstance(raw, (list, tuple)):
        return []
    codes = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            codes.append(item.strip().lower())
    return codes


def resolve_merchant_language(merchant: dict) -> dict:
    """Merchant identity.languages containing "hi" -> hinglish; else regional_mix if a regional
    language is listed; else english."""
    identity = merchant.get("identity") if isinstance(merchant, dict) else None
    codes = _normalize_codes((identity or {}).get("languages") if isinstance(identity, dict) else None)
    if any(c in ("hi", "hindi", "hi-en", "hinglish") for c in codes):
        return _result("hinglish")
    for c in codes:
        if c in _REGIONAL_ALIASES:
            return _result("regional_mix", _REGIONAL_ALIASES[c])
    return _result("english")


def resolve_customer_language(customer: dict) -> dict:
    """Customer identity.language_pref: "hi-en mix" -> hinglish, "hi" -> hindi, "en"/"english" ->
    english, "te-en mix"/"ta-en mix"/"kn-en mix"/"mr-en mix" -> regional_mix. Unknown -> english."""
    identity = customer.get("identity") if isinstance(customer, dict) else None
    pref = (identity or {}).get("language_pref") if isinstance(identity, dict) else None
    if not isinstance(pref, str) or not pref.strip():
        return _result("english")
    tokens = [t for t in re.split(r"[^a-z]+", pref.strip().lower()) if t]
    has_en = any(t in ("en", "english", "mix", "hinglish") for t in tokens)
    if "hinglish" in tokens or (any(t in ("hi", "hindi") for t in tokens) and has_en):
        return _result("hinglish")
    if any(t in ("hi", "hindi") for t in tokens):
        return _result("hindi")
    for t in tokens:
        if t in _REGIONAL_ALIASES:
            return _result("regional_mix", _REGIONAL_ALIASES[t])
    return _result("english")


def hindi_marker_score(text: str) -> float:
    """Strong Roman-Hindi markers count 1, ambiguous ones 0.5."""
    words = _WORD_RE.findall(text.lower()) if isinstance(text, str) else []
    score = 0.0
    for w in words:
        if w in _STRONG_MARKERS:
            score += 1.0
        elif w in _WEAK_MARKERS:
            score += 0.5
    return score


def detect_message_language(text: str) -> str:
    """Classify one message as "hindi" (Devanagari-dominant), "hinglish" (Roman-script Hindi or
    mixed scripts) or "english"."""
    if not isinstance(text, str) or not text.strip():
        return "english"
    deva = len(_DEVANAGARI_RE.findall(text))
    if deva >= 2:
        latin = len(_LATIN_RE.findall(text))
        return "hinglish" if latin > deva else "hindi"
    words = _WORD_RE.findall(text.lower())
    score = hindi_marker_score(text)
    if score >= 1.5 or (score >= 1.0 and len(words) <= 6):
        return "hinglish"
    return "english"
