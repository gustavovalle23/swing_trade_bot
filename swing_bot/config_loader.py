import json
import os


def load_config():
    path = os.getenv("SWING_CONFIG_PATH", "config.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["sec_user_agent"] = os.getenv("SEC_USER_AGENT", "").strip()
    if not data["sec_user_agent"]:
        raise ValueError("SEC_USER_AGENT is required")
    return data
