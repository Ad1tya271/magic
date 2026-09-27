import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

data = Path("data/expanded")
pairs = json.loads((data / "test_pairs.json").read_text(encoding="utf-8"))["pairs"]
print(f"Total test pairs: {len(pairs)}")
for p in pairs:
    tid = p["trigger_id"]
    mid = p["merchant_id"]
    cid = p.get("customer_id")
    trg = json.loads((data / "triggers" / f"{tid}.json").read_text(encoding="utf-8"))
    m = json.loads((data / "merchants" / f"{mid}.json").read_text(encoding="utf-8"))
    kind = trg.get("kind")
    payload = trg.get("payload", {})
    cat = m.get("category_slug")
    print(f"[{p['test_id']}] kind={kind:<25} cat={cat:<12} mid={mid:<35} cust={cid or '-'}")
    print(f"      payload: {payload}")
