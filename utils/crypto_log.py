import os, json, datetime
from cryptography.fernet import Fernet

FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY.encode()) if FERNET_KEY else None

def write_event(event: dict, path: str = "logs/audit.log"):
    os.makedirs("logs", exist_ok=True)
    event = {"ts": datetime.datetime.utcnow().isoformat()+"Z", **event}
    line = json.dumps(event, ensure_ascii=False)
    if fernet:
        token = fernet.encrypt(line.encode("utf-8"))
        with open(path, "ab") as f:
            f.write(token + b"\n")
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
