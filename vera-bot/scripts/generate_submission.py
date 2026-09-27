"""Create the challenge's 30-line submission.jsonl from its canonical test pairs."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
CHALLENGE=ROOT.parent/"magicpin-ai-challenge"
sys.path.insert(0,str(ROOT))
from bot import compose

def _load_contexts(directory: Path, id_field: str) -> dict[str,dict]:
    found={}
    for path in directory.glob("*.json"):
        try:
            obj=json.loads(path.read_text(encoding="utf-8"))
            ident=obj.get(id_field)
            if ident: found[ident]=obj
        except (OSError,ValueError):
            continue
    return found

def generate(out: Path=ROOT/"submission.jsonl") -> Path:
    data=ROOT/"data"/"expanded"
    categories={p.stem:json.loads(p.read_text(encoding="utf-8")) for p in (data/"categories").glob("*.json")}
    merchants=_load_contexts(data/"merchants","merchant_id")
    customers=_load_contexts(data/"customers","customer_id")
    triggers=_load_contexts(data/"triggers","id")
    pairs=json.loads((data/"test_pairs.json").read_text(encoding="utf-8"))["pairs"]
    lines=[]
    for pair in pairs:
        trigger=triggers[pair["trigger_id"]]
        merchant=merchants[pair["merchant_id"]]
        customer=customers.get(pair.get("customer_id")) if pair.get("customer_id") else None
        category=categories[merchant["category_slug"]]
        msg=compose(category,merchant,trigger,customer)
        lines.append(json.dumps({"test_id":pair["test_id"],"body":msg["body"],"cta":msg["cta"],
            "send_as":msg["send_as"],"suppression_key":msg["suppression_key"],"rationale":msg["rationale"]},ensure_ascii=False))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return out

if __name__=="__main__":
    print(generate())
