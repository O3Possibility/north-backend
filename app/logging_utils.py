import os
import json
import time
from typing import Any, Dict
from app.config import settings

def ensure_log_dir() -> str:
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    return settings.LOG_DIR

def log_event(event: Dict[str, Any]) -> None:
    if not settings.ENABLE_LOGS:
        return
    ensure_log_dir()
    ts = int(time.time() * 1000)
    date = time.strftime("%Y-%m-%d")
    path = os.path.join(settings.LOG_DIR, f"north_trace_{date}.jsonl")
    event["_ts_ms"] = ts
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
