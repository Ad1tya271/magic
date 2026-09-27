"""Evaluate submission.jsonl against the challenge judge rubric and penalty rules."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "expanded"

def evaluate():
    sub_file = ROOT / "submission.jsonl"
    lines = [json.loads(line) for line in sub_file.read_text(encoding="utf-8").strip().split("\n")]
    categories = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (DATA_DIR / "categories").glob("*.json")}
    merchants = {}
    for p in (DATA_DIR / "merchants").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("merchant_id"): merchants[d["merchant_id"]] = d
    triggers = {}
    for p in (DATA_DIR / "triggers").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("id"): triggers[d["id"]] = d
    pairs = json.loads((DATA_DIR / "test_pairs.json").read_text(encoding="utf-8"))["pairs"]
    pair_map = {p["test_id"]: p for p in pairs}

    scores = []
    seen_bodies = set()

    for item in lines:
        tid = item["test_id"]
        pair = pair_map[tid]
        body = item["body"]
        cta = item["cta"]
        send_as = item["send_as"]
        m = merchants[pair["merchant_id"]]
        trg = triggers[pair["trigger_id"]]
        cat = categories[m["category_slug"]]

        penalties = 0
        reasons = []

        # Penalties:
        # URLs: -3
        if re.search(r'https?://|www\.', body):
            penalties += 3
            reasons.append("URL present (-3)")

        # Duplicate body: -2
        if body in seen_bodies:
            penalties += 2
            reasons.append("Duplicate body (-2)")
        seen_bodies.add(body)

        # Taboo words: -2
        taboos = [t.lower() for t in cat.get("voice", {}).get("vocab_taboo", [])]
        for t in taboos:
            if re.search(rf'\b{re.escape(t)}\b', body.lower()):
                penalties += 2
                reasons.append(f"Taboo word '{t}' (-2)")

        # Internal jargon leak: -1
        if re.search(r'\b(trg_\w+|m_\d+|c_\d+|suppression)\b', body):
            penalties += 1
            reasons.append("Internal jargon leak (-1)")

        # Specificity: Numbers, dates, sources, percentages
        num_count = len(re.findall(r'₹?\d+[\d,.]*%?', body))
        has_date_or_time = bool(re.search(r'\b(\d{4}-\d{2}-\d{2}|today|tonight|tomorrow|hafte|din|month)\b', body, re.I))
        has_source = bool("—" in body or "source:" in body.lower() or "dci" in body.lower() or "ida" in body.lower())
        spec = min(10, 6 + (2 if num_count >= 2 else (1 if num_count == 1 else 0)) + (1 if has_date_or_time else 0) + (1 if has_source else 0))

        # Category Fit: Domain vocab, proper salutation
        owner = m.get("identity", {}).get("owner_first_name") or ""
        sal_match = owner.lower() in body.lower() or (cat.get("slug") == "dentists" and "dr." in body.lower())
        cat_fit = 9 if sal_match else 8

        # Merchant Fit: Language mode & active offer / metric tie-in
        has_offer = bool(re.search(r'₹\d+|cleaning|thali|home delivery|trial|post|offer', body, re.I))
        merch_fit = 9 if has_offer else 8

        # Decision Quality / Trigger Relevance: Why now
        why_now = bool(re.search(r'due|confirm|kareeb|down|aaj|match|competitor|renew|update|lapsed|din', body, re.I))
        dq = 9 if why_now else 8

        # Engagement Compulsion: CTA clarity, single ask
        valid_cta = cta in ("binary_yes_no", "binary_confirm_cancel", "multi_choice_slot", "open_ended")
        single_cta = body.count("?") <= 1 or "reply yes" in body.lower() or "reply confirm" in body.lower()
        eng = 10 if (valid_cta and single_cta) else 8

        total = max(0, spec + cat_fit + merch_fit + dq + eng - penalties)
        scores.append({
            "test_id": tid, "kind": trg.get("kind"), "spec": spec,
            "cat_fit": cat_fit, "merch_fit": merch_fit, "dq": dq,
            "eng": eng, "penalties": penalties, "total": total, "reasons": reasons
        })

    avg_spec = sum(s["spec"] for s in scores) / len(scores)
    avg_cat = sum(s["cat_fit"] for s in scores) / len(scores)
    avg_merch = sum(s["merch_fit"] for s in scores) / len(scores)
    avg_dq = sum(s["dq"] for s in scores) / len(scores)
    avg_eng = sum(s["eng"] for s in scores) / len(scores)
    avg_pen = sum(s["penalties"] for s in scores) / len(scores)
    avg_total = sum(s["total"] for s in scores) / len(scores)
    pct = (avg_total / 50.0) * 100.0

    print("=" * 65)
    print("        MAGICPIN AI CHALLENGE — SUBMISSION SCORECARD")
    print("=" * 65)
    print(f"Total Messages Evaluated: {len(scores)}")
    print(f"Total Penalties Detected: {sum(s['penalties'] for s in scores)}\n")
    print(f"  • Specificity:          {avg_spec:.1f} / 10")
    print(f"  • Category Fit:         {avg_cat:.1f} / 10")
    print(f"  • Merchant Fit:         {avg_merch:.1f} / 10")
    print(f"  • Decision Quality:     {avg_dq:.1f} / 10")
    print(f"  • Engagement & CTA:     {avg_eng:.1f} / 10")
    print(f"  • Penalties (Avg):     -{avg_pen:.1f}")
    print("-" * 65)
    print(f"  OVERALL COMPOSITE SCORE: {avg_total:.1f} / 50  ({pct:.1f}%)")
    if pct >= 80:
        print("  RATING: EXCELLENT (Top Tier)")
    elif pct >= 60:
        print("  RATING: GOOD")
    print("=" * 65)

if __name__ == "__main__":
    evaluate()
