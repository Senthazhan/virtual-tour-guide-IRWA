import json, os, difflib, re
from typing import Optional, Dict, List

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "places.json")
with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
    PLACES: Dict[str, dict] = json.load(f)

def list_places() -> List[str]:
    return sorted(list(PLACES.keys()))

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def _best_match(q: str) -> Optional[str]:
    if not q: return None
    qn = _norm(q)
    # exact / substring match on keys and aliases
    for name, data in PLACES.items():
        keys = [name] + data.get("aliases", [])
        for k in keys:
            kn = _norm(k)
            if qn == kn or qn in kn or kn in qn:
                return name
    # fuzzy
    candidates = difflib.get_close_matches(qn, [_norm(k) for k in PLACES.keys()], n=1, cutoff=0.6)
    if candidates:
        # map back to original casing
        lower_to_orig = {_norm(k): k for k in PLACES.keys()}
        return lower_to_orig.get(candidates[0])
    return None

def lookup_place(place: str) -> Optional[dict]:
    name = _best_match(place)
    if not name:
        return None
    e = PLACES[name]
    facts = e.get("facts", [])
    ticket = e.get("ticket", "N/A")
    return {
        "place": name,
        "facts": facts[:5],  # show a few more facts
        "ticket": ticket
    }

def search(query: str) -> List[dict]:
    """Lightweight search across name, city, highlights."""
    qn = _norm(query)
    results = []
    for name, data in PLACES.items():
        score = 0
        fields = [
            name,
            data.get("city", ""),
            " ".join(data.get("highlights", [])),
            " ".join(data.get("facts", [])),
        ]
        joined = " ".join(fields).lower()
        if qn in joined:
            score += 3
        # token overlap
        tokens = set(qn.split())
        if tokens and any(tok in joined for tok in tokens):
            score += len(tokens)
        if score:
            results.append({
                "name": name,
                "city": data.get("city", ""),
                "best_time": data.get("best_time", ""),
                "score": score
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]
