from typing import Tuple
from better_profanity import profanity
import re

# Load profanity dictionary (already includes strong words)
profanity.load_censor_words()

BANNED_SUBSTRINGS = {
    "kill", "harm", "bomb", "terror", "suicide",
    "hack", "ddos", "phish", "malware", "ransomware",
    "password dump", "credit card", "steal",
    "meth", "cocaine",
    "rm -rf", "drop table", "union select", "exec(", "system(", "xp_cmdshell",
    "<script", "</script"
}

URL_PAT = re.compile(r"https?://[^\s]+", re.I)
EMAIL_PAT = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)

def _contains_banned(text: str) -> str:
    t = (text or "").lower()
    for bad in BANNED_SUBSTRINGS:
        if bad in t:
            return bad
    return ""

def check_input(text: str) -> Tuple[bool, str]:
    t = (text or "")
    if profanity.contains_profanity(t):
        return False, "profanity"
    bad = _contains_banned(t)
    if bad:
        return False, bad
    # crude HTML/script detection
    if "<" in t or ">" in t:
        # allow markdown-like "<3" or escaped html, but block raw tags
        if re.search(r"<\s*\/?\s*[a-z][a-z0-9\-]*\s*[^>]*>", t, re.I):
            return False, "raw_html_tag"
    return True, ""

def sanitize(text: str) -> str:
    # strip angle brackets + collapse whitespace
    clean = (text or "").replace("<", "").replace(">", "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:2000]  # avoid giant payloads

def check_output(text: str) -> Tuple[bool, str]:
    t = (text or "")
    if "<script" in t.lower() or "</script" in t.lower():
        return False, "script"
    # prevent accidental leakage of emails/links if needed (demo policy—allow links if you prefer)
    if URL_PAT.search(t) and "http" in t.lower():
        # allow; flip to False to block links
        return True, ""
    if EMAIL_PAT.search(t):
        # allow; flip to False to block emails
        return True, ""
    return True, ""
