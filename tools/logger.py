import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("/root/tv_bot/alerts_history.log")

def record_alert(raw_data: dict) -> None:
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": raw_data
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
