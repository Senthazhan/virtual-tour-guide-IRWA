import os
from typing import Optional

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def polish_text(text: str, max_len: int = 600) -> str:
    if not text:
        return text
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            prompt = (
                "Rewrite as a professional, friendly tour guide.\n"
                "Output style:\n"
                "- Start with a one-sentence answer.\n"
                "- Then 3–6 short bullets with the most useful facts/details.\n"
                "- If it is an itinerary, use a numbered list with minute estimates.\n"
                "- Keep it concise, specific, and free of filler or marketing fluff.\n"
                "- Use simple Markdown only (bold, bullets, numbered lists).\n"
                f"Text to rewrite:\n{text}"
            )
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"You are a concise, professional tour guide who writes brief, structured answers."},
                          {"role":"user","content":prompt}],
                max_tokens=260,
                temperature=0.15,
            )
            out = res.choices[0].message.content.strip()
            return out[:max_len]
        except Exception:
            pass
    import re
    # Fallback: compact text and emulate a brief professional tone
    t = re.sub(r"\s+", " ", (text or "").strip())
    # Keep first 1–2 sentences as lead
    sents = re.split(r'(?<=[.!?])\s+', t)
    lead = " ".join(sents[:2])
    rest = " ".join(sents[2:])
    # Try to bulletize obvious list-like fragments
    items = re.split(r";|\s-\s|\n|,\s(?=[A-Z])", rest)
    bullets = [f"- {re.sub(r'\s+', ' ', i).strip()}" for i in items if i and len(i.strip()) > 3][:5]
    compact = (lead + ("\n" + "\n".join(bullets) if bullets else "")).strip()
    return compact[:max_len]
