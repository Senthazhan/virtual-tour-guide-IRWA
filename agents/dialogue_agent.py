import re
from typing import Tuple, Literal, Dict, Any, Optional

Intent = Literal["facts", "itinerary", "help", "chitchat", "unknown"]

# Accept: "2h", "2 hr", "2 hours", "120m", "120 minutes", "1.5 hours"
TIME_PAT = re.compile(
    r"(?:(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h))|(?:(\d+)\s*(?:minutes?|mins?|m))",
    re.I,
)

CITY_PAT = re.compile(
    r"(?:in|at|around|for)\s+([a-zA-Z][a-zA-Z\s\-']{1,40})\b", re.I
)

FACTS_TRIGGERS = (
    "tell me about", "facts", "history", "info about", "information about",
    "what is", "where is", "ticket", "opening", "close time"
)
PLAN_TRIGGERS = (
    "plan", "route", "itinerary", "tour", "make a plan", "schedule",
    "visit plan", "trip plan", "route plan"
)

CHITCHAT_TRIGGERS = (
    "hi", "hello", "hey", "good morning", "good evening", "good night",
    "how are you", "what's up", "whats up", "good afternoon", "greetings"
)

def parse_minutes(text: str) -> Optional[int]:
    t = (text or "").lower()
    m = TIME_PAT.search(t)
    if not m:
        return None
    if m.group(1):  # hours (possibly float)
        hours = float(m.group(1))
        return max(30, int(round(hours * 60)))
    if m.group(2):  # minutes
        return max(15, int(m.group(2)))
    return None

def _extract_city(text: str) -> Optional[str]:
    t = (text or "").strip()
    m = CITY_PAT.search(t)
    if m:
        return m.group(1).strip(" ?!.").title()
    # fallback: if user wrote a short query like "kandy tour 2h"
    words = [w for w in re.split(r"[^a-zA-Z]+", t) if w]
    if len(words) <= 3:
        return " ".join(words).title() if words else None
    return None

def route_intent(text: str) -> Tuple[Intent, Dict[str, Any]]:
    t = (text or "").lower().strip()

    # Help
    if any(k in t for k in ("help", "how to use", "what can you do")):
        return "help", {}

    # Itinerary first (because “plan about kandy” should be itinerary)
    if any(k in t for k in PLAN_TRIGGERS):
        return "itinerary", {
            "city": _extract_city(text),
            "minutes": parse_minutes(text)
        }

    # Facts
    if any(k in t for k in FACTS_TRIGGERS):
        # try to grab the substring after "about"
        place = None
        if "about" in t:
            place = text.lower().split("about", 1)[1]
        place = (place or text).strip(" ?!.")
        return "facts", {"place": place}

    # Chit-chat / greetings
    if any(k in t for k in CHITCHAT_TRIGGERS):
        return "chitchat", {}

    # One or two words → treat as place facts (e.g., "Sigiriya", "Kandy ticket")
    words = [w for w in re.split(r"\s+", t) if w]
    if 1 <= len(words) <= 3:
        return "facts", {"place": text.strip(" ?!.")}

    return "unknown", {}
