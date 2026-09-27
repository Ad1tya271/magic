"""Test all 30 canonical test pairs for submission validity and quality."""
from __future__ import annotations
import json
from pathlib import Path
import pytest

from bot import compose
from vera.validate import has_errors, validate_message, CTA_VALUES

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "expanded"


def _load_contexts(directory: Path, id_field: str) -> dict[str, dict]:
    found = {}
    for path in directory.glob("*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            ident = obj.get(id_field)
            if ident:
                found[ident] = obj
        except (OSError, ValueError):
            continue
    return found


@pytest.fixture(scope="module")
def dataset():
    categories = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (DATA_DIR / "categories").glob("*.json")}
    merchants = _load_contexts(DATA_DIR / "merchants", "merchant_id")
    customers = _load_contexts(DATA_DIR / "customers", "customer_id")
    triggers = _load_contexts(DATA_DIR / "triggers", "id")
    pairs = json.loads((DATA_DIR / "test_pairs.json").read_text(encoding="utf-8"))["pairs"]
    return {
        "categories": categories,
        "merchants": merchants,
        "customers": customers,
        "triggers": triggers,
        "pairs": pairs,
    }


def test_all_30_pairs_generate_cleanly(dataset):
    pairs = dataset["pairs"]
    assert len(pairs) == 30

    bodies_seen = set()
    for pair in pairs:
        test_id = pair["test_id"]
        trigger = dataset["triggers"][pair["trigger_id"]]
        merchant = dataset["merchants"][pair["merchant_id"]]
        customer = dataset["customers"].get(pair.get("customer_id")) if pair.get("customer_id") else None
        category = dataset["categories"][merchant["category_slug"]]

        msg = compose(category, merchant, trigger, customer)
        assert msg is not None, f"compose returned None for {test_id}"
        assert not msg.get("skip"), f"{test_id} was skipped: {msg.get('reason')}"

        body = msg.get("body", "")
        cta = msg.get("cta", "")
        send_as = msg.get("send_as", "")
        suppression_key = msg.get("suppression_key", "")
        rationale = msg.get("rationale", "")

        # 1. Non-empty required fields
        assert body, f"Empty body in {test_id}"
        assert cta in CTA_VALUES, f"Invalid CTA '{cta}' in {test_id}"
        assert send_as in ("vera", "merchant_on_behalf"), f"Invalid send_as '{send_as}' in {test_id}"
        assert suppression_key, f"Empty suppression_key in {test_id}"
        assert rationale, f"Empty rationale in {test_id}"

        # 2. No URLs
        assert "http://" not in body and "https://" not in body and "www." not in body, f"URL in body for {test_id}: {body}"

        # 3. No raw unformatted ISO timestamps like 2026-05-02T19:00:00+05:30
        assert "T19:" not in body and "T00:" not in body and "+05:30" not in body, f"Raw ISO time in body for {test_id}: {body}"

        # 4. No double parentheses
        assert "((" not in body and "))" not in body, f"Double parens in {test_id}: {body}"

        # 5. Route accuracy: if customer is present and consented, send_as should be merchant_on_behalf
        if customer and customer.get("preferences", {}).get("reminder_opt_in") and customer.get("consent", {}).get("scope"):
            assert send_as == "merchant_on_behalf", f"Expected merchant_on_behalf for consented customer in {test_id}"

        # 6. Slot CTA accuracy: if available slots are presented, CTA should be multi_choice_slot
        if "Available slots" in body or "slots available" in body:
            assert cta == "multi_choice_slot", f"Expected multi_choice_slot for slot presentation in {test_id}"

        # 7. Uniqueness: no duplicate bodies across test pairs
        assert body not in bodies_seen, f"Duplicate body in {test_id}: {body}"
        bodies_seen.add(body)

        # 8. Validation passes with zero errors
        bundle = {"category": category, "merchant": merchant, "trigger": trigger, "customer": customer}
        from vera.facts import derive_facts
        facts = derive_facts(bundle)
        issues = validate_message(msg, bundle, facts, mode="compose")
        errors = [i for i in issues if i.get("severity") == "error"]
        assert not errors, f"Validation errors in {test_id}: {errors}"
