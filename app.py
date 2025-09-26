import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from utils.auth import login as do_login, logout as do_logout, require_auth
from utils.crypto_log import write_event
from utils.llm import polish_text
from agents.safety_agent import check_input, sanitize, check_output
from agents.dialogue_agent import route_intent, parse_minutes
from agents.ir_agent import lookup_place, list_places
from agents.itinerary_agent import plan

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key")

WELCOME = (
    "Hi! I am your Virtual Tour Guide.\n"
    "Try: **Tell me about Sigiriya** or **Plan a 3-hour tour in Kandy**.\n"
    "Places in my dataset: " + ", ".join(list_places()[:12]) + " …"
)

# ---------- helpers: safe, markdown-friendly responses + smart suggestions ----------
def respond(text: str, suggestions=None, status: int = 200):
    """Polish + safety check + JSON envelope with optional suggestions."""
    text = polish_text(text)
    ok_out, reason_out = check_output(text)
    if not ok_out:
        write_event({"agent": "safety", "blocked_output": reason_out})
        text = "⚠️ Output blocked by Safety Agent."
        suggestions = ["Help", "Tell me about Sigiriya", "Plan a 3-hour tour in Kandy"]
    return jsonify({"reply": text, "suggestions": suggestions or []}), status

def clear_slots():
    session["pending"] = None
    session["slots"] = {}

def suggest_for(intent: str, payload: dict | None = None, extra_city: str | None = None):
    """Context-aware quick-reply chips."""
    payload = payload or {}
    city = extra_city or payload.get("city") or payload.get("place")
    if intent in ("help", "unknown"):
        return ["Tell me about Sigiriya", "Plan a 3-hour tour in Kandy"]
    if intent == "facts" and city:
        return [f"Plan a 2-hour tour in {city}", f"Ticket price in {city}", "Another city"]
    if intent == "itinerary" and city:
        return [f"Facts about {city}", "Plan another city", "Help"]
    if intent == "chitchat":
        return ["Tell me about Sigiriya", "Plan a 2-hour tour", "Help"]
    if intent == "await_city":
        return ["Kandy", "Galle", "Ella", "Sigiriya"]
    if intent == "await_minutes" and city:
        return ["1 hour", "2 hours", "3 hours"]
    return []

# ---------- Auth ----------
@app.get("/login")
def login_page():
    return render_template("login.html")

@app.post("/login")
def login_submit():
    user = request.form.get("user", "")
    pwd = request.form.get("pwd", "")
    if do_login(user, pwd):
        write_event({"agent": "auth", "event": "login", "user": user})
        return redirect(url_for("index"))
    return render_template("login.html", error="Invalid credentials.")

@app.get("/logout")
def logout():
    do_logout()
    write_event({"agent": "auth", "event": "logout"})
    return redirect(url_for("login_page"))

# ---------- UI ----------
@app.get("/")
def index():
    if not require_auth():
        return redirect(url_for("login_page"))
    session.setdefault("pending", None)
    session.setdefault("slots", {})
    return render_template("index.html")

# expose lightweight state for UI status strip
@app.get("/state")
def state():
    if not require_auth():
        return jsonify({}), 401
    s = session.get("slots", {})
    return jsonify({"city": s.get("city"), "minutes": s.get("minutes")})

# ---------- Chat ----------
@app.post("/chat")
def chat():
    if not require_auth():
        return jsonify({"reply": "Please login first.", "suggestions": []}), 401

    data = request.get_json(silent=True) or {}
    raw = data.get("message", "")

    ok, reason = check_input(raw)
    if not ok:
        write_event({"agent": "safety", "blocked_input": reason, "text": raw})
        return respond("❌ Safety Agent blocked your input.", ["Help"])

    user_msg = sanitize(raw)

    # Slot filling state
    pending = session.get("pending")
    slots = session.get("slots", {})

    # If we are waiting for city / minutes, capture them first
    if pending == "city":
        slots["city"] = user_msg
        session["pending"] = "minutes"
        session["slots"] = slots
        return respond(
            f"Great. How much time do you have for **{slots['city']}**? (e.g., *2 hours* or *120 min*)",
            suggest_for("await_minutes", extra_city=slots["city"])
        )

    if pending == "minutes":
        mins = parse_minutes(user_msg)
        if not mins:
            return respond(
                "Please tell me the time like **2 hours** or **150 min**.",
                ["1 hour", "2 hours", "3 hours"]
            )
        slots["minutes"] = int(mins)
        # proceed to plan
        res = plan(slots.get("city", ""), slots.get("minutes", 180))
        clear_slots()
        if not res or not res.get("stops"):
            reply = "I couldn't plan that. Try **Plan a 3-hour tour in Kandy**."
            return respond(reply, ["Plan a 3-hour tour in Kandy", "Help"])
        else:
            lines = [f"{i+1}. {s['name']} — ~{s['minutes']} min" for i, s in enumerate(res["stops"])]
            reply = (
                f"**{res['city']} — {res['planned_minutes']}/{res['total_minutes']} min**\n"
                + "\n".join(lines)
                + "\n\nWant **ticket info** or some **quick facts** for this city?"
            )
        write_event({"agent": "dialogue", "intent": "itinerary",
                     "payload": {"city": res.get("city"), "minutes": res.get("total_minutes")}})
        return respond(reply, suggest_for("itinerary", extra_city=res.get("city")))

    # No pending slot → normal intent routing
    intent, payload = route_intent(user_msg)

    if intent in ("help", "unknown"):
        return respond(WELCOME, suggest_for(intent))

    if intent == "chitchat":
        reply = (
            "Hello! I'm glad you're here. I can share quick facts about places or plan a mini tour.\n\n"
            "Try: **Tell me about Sigiriya** or **Plan a 2-hour tour in Kandy**."
        )
        return respond(reply, suggest_for("chitchat"))

    if intent == "facts":
        res = lookup_place(payload.get("place", ""))
        if not res:
            return respond(
                "I couldn't find that place. Try one of these: " + ", ".join(list_places()[:12]) + " …",
                ["Tell me about Sigiriya", "Tell me about Kandy", "Plan a 3-hour tour in Kandy"]
            )
        facts = "\n- " + "\n- ".join(res["facts"]) if res["facts"] else "No facts."
        reply = (
            f"**{res['place']}**{facts}\n\n"
            f"**Ticket:** {res['ticket']}\n\n"
            f"Would you like a 2–3 stop **mini tour** in **{res['place']}**? "
            f"Tell me your time (e.g., *2 hours*)."
        )
        write_event({"agent": "dialogue", "intent": "facts", "payload": {"place": res["place"]}})
        return respond(reply, suggest_for("facts", {"place": res["place"]}))

    if intent == "itinerary":
        city = payload.get("city")
        minutes = payload.get("minutes")
        if not city:
            session["pending"] = "city"
            session["slots"] = {}
            return respond(
                "Which **city** would you like a tour for?",
                suggest_for("await_city")
            )
        if not minutes:
            session["pending"] = "minutes"
            session["slots"] = {"city": city}
            return respond(
                f"How much **time** do you have for **{city}**? (e.g., *2 hours* or *120 min*)",
                suggest_for("await_minutes", extra_city=city)
            )
        # have both -> plan
        res = plan(city, int(minutes))
        if not res or not res.get("stops"):
            reply = "I couldn't plan that. Try **Plan a 3-hour tour in Kandy**."
            return respond(reply, ["Plan a 3-hour tour in Kandy", "Help"])
        else:
            lines = [f"{i+1}. {s['name']} — ~{s['minutes']} min" for i, s in enumerate(res["stops"])]
            reply = (
                f"**{res['city']} — {res['planned_minutes']}/{res['total_minutes']} min**\n"
                + "\n".join(lines)
                + "\n\nWant **ticket info** or **quick facts** as well?"
            )
        write_event({"agent": "dialogue", "intent": "itinerary", "payload": {"city": city, "minutes": minutes}})
        return respond(reply, suggest_for("itinerary", {"city": city}))

    # Fallback
    return respond(WELCOME, suggest_for("help"))

if __name__ == "__main__":
    app.run(debug=True, threaded=True)
