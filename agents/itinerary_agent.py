import json, os, re
from typing import Optional, Dict, List

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "places.json")
with open(DATA_PATH, "r", encoding="utf-8-sig") as f:
    PLACES: Dict[str, dict] = json.load(f)

def _pick_city(city: str) -> Optional[str]:
    cl = (city or "").lower()
    for k in PLACES:
        kl = k.lower()
        if cl == kl or cl in kl or kl in cl:
            return k
    return None

def _pack_stops(stops: List[dict], minutes: int) -> (List[dict], int):
    """Greedy pack by minutes; keeps original order from dataset (already curated)."""
    chosen: List[dict] = []
    used = 0
    for s in stops:
        dur = int(s.get("minutes", 30))
        if dur <= 0:
            continue
        if used + dur <= minutes:
            chosen.append({"name": s.get("name", "Stop"), "minutes": dur})
            used += dur
    return chosen, used

def plan(city: str, minutes: int = 180) -> Optional[dict]:
    minutes = max(45, int(minutes or 0))  # enforce a sensible lower bound
    target = _pick_city(city)
    if not target:
        return None
    stops = PLACES[target].get("stops", [])
    chosen, used = _pack_stops(stops, minutes)
    if not chosen:
        # fallback: at least the first stop if exists
        if stops:
            first = stops[0]
            used = min(minutes, int(first.get("minutes", 30)))
            chosen = [{"name": first.get("name", "Stop 1"), "minutes": used}]
        else:
            return None
    return {
        "city": target,
        "total_minutes": minutes,
        "planned_minutes": used,
        "stops": chosen,
        "note": "Greedy time packer (demo). Add maps/GPS/opening-hours for production."
    }
