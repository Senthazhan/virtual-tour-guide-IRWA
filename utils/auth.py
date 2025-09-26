import os
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_HASH = generate_password_hash(ADMIN_PASSWORD)

def login(user: str, pwd: str) -> bool:
    if user == ADMIN_USER and check_password_hash(ADMIN_HASH, pwd):
        session["user"] = user
        return True
    return False

def logout():
    session.pop("user", None)

def require_auth() -> bool:
    return bool(session.get("user"))
